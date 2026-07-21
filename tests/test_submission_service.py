import json
import os
import unittest
from unittest.mock import patch

from api.submission_service import _grade_pseudocode


PUBLIC_PROBLEM = {
    "statement": {
        "summary": "두 수를 더합니다.",
        "description": "두 정수를 입력받아 합을 출력합니다.",
        "input": "두 정수 A와 B",
        "output": "A+B",
        "constraints": ["정수 범위 안의 입력"],
    }
}

PRIVATE_PROBLEM = {
    "pseudocode_rubric": {
        "pass_score": 70,
        "criteria": [
            {"id": "read", "description": "두 수를 읽는다.", "weight": 40},
            {"id": "add", "description": "두 수를 더한다.", "weight": 40},
            {"id": "print", "description": "합을 출력한다.", "weight": 20},
        ],
    }
}


def provider_result(answer_derivable: bool, has_logical_error: bool) -> dict:
    evaluation = {
        "answer_derivable": answer_derivable,
        "has_logical_error": has_logical_error,
        "score": 65,
        "feedback": "풀이 의도는 확인했습니다.",
        "missing_steps": ["표현을 조금 더 구체화할 수 있습니다."],
    }
    return {"choices": [{"message": {"content": json.dumps(evaluation)}}]}


class PseudocodeGradingTest(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "HF_TOKEN": "test-token",
            "HF_BASE_URL": "https://huggingface.test/v1",
            "HF_MODEL": "test-model",
        },
        clear=False,
    )
    @patch("api.submission_service._request_json")
    def test_passed_is_computed_from_both_model_flags(self, request_mock) -> None:
        cases = [
            (True, False, True),
            (True, True, False),
            (False, False, False),
            (False, True, False),
        ]

        for answer_derivable, has_logical_error, expected_passed in cases:
            with self.subTest(
                answer_derivable=answer_derivable,
                has_logical_error=has_logical_error,
            ):
                request_mock.return_value = provider_result(
                    answer_derivable, has_logical_error
                )

                result = _grade_pseudocode(
                    "두 수를 받아 합친 값을 보여준다.",
                    PUBLIC_PROBLEM,
                    PRIVATE_PROBLEM,
                )

                self.assertIs(result["passed"], expected_passed)
                self.assertEqual(result["kind"], "pseudocode")
                self.assertEqual(result["status"], "evaluated")
                self.assertEqual(result["score"], 65)
                self.assertEqual(
                    set(result),
                    {
                        "kind",
                        "status",
                        "passed",
                        "score",
                        "feedback",
                        "missing_steps",
                    },
                )
                self.assertNotIn("answer_derivable", result)
                self.assertNotIn("has_logical_error", result)

    @patch.dict(
        os.environ,
        {
            "HF_TOKEN": "test-token",
            "HF_BASE_URL": "https://huggingface.test/v1",
            "HF_MODEL": "test-model",
        },
        clear=False,
    )
    @patch("api.submission_service._request_json")
    def test_provider_payload_contains_lenient_policy_and_internal_schema(
        self, request_mock
    ) -> None:
        request_mock.return_value = provider_result(True, False)

        result = _grade_pseudocode(
            "둘을 합해서 답",
            PUBLIC_PROBLEM,
            PRIVATE_PROBLEM,
        )

        self.assertTrue(result["passed"])
        request_mock.assert_called_once()
        call = request_mock.call_args
        self.assertEqual(
            call.args,
            ("POST", "https://huggingface.test/v1/chat/completions"),
        )
        payload = call.kwargs["payload"]
        self.assertEqual(payload["model"], "test-model")

        response_schema = payload["response_format"]["json_schema"]["schema"]
        self.assertEqual(
            set(response_schema["properties"]),
            {
                "answer_derivable",
                "has_logical_error",
                "score",
                "feedback",
                "missing_steps",
            },
        )
        self.assertNotIn("passed", response_schema["properties"])

        policy = payload["messages"][0]["content"]
        for required_policy in (
            "자유로운 형식",
            "부정확한 용어",
            "구현 세부 단계 생략",
            "대안 풀이",
            "비효율만으로는 오답 처리",
            "핵심 논리가 실제로 틀렸을 때만",
        ):
            self.assertIn(required_policy, policy)


if __name__ == "__main__":
    unittest.main()

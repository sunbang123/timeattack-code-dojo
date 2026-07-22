import json
import os
import unittest
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import patch

from api.submission_service import (
    ProviderHTTPError,
    _grade_pseudocode,
    _request_json,
)


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
    @patch("api.submission_service.urlopen")
    def test_http_error_logs_provider_detail_without_query_string(self, urlopen_mock) -> None:
        urlopen_mock.side_effect = HTTPError(
            "https://provider.test/chat/completions?token=secret",
            400,
            "Bad Request",
            {},
            BytesIO(
                json.dumps(
                    {
                        "error": {
                            "message": "response_format is not supported",
                            "type": "invalid_request_error",
                        }
                    }
                ).encode("utf-8")
            ),
        )

        with self.assertLogs("api.submission_service", level="WARNING") as logs:
            with self.assertRaises(ProviderHTTPError) as raised:
                _request_json(
                    "POST",
                    "https://provider.test/chat/completions?token=secret",
                    payload={"answer": "private"},
                )

        self.assertEqual(raised.exception.status_code, 400)
        message = "\n".join(logs.output)
        self.assertIn("response_format is not supported", message)
        self.assertNotIn("token=secret", message)
        self.assertNotIn("private", message)

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
    def test_retries_http_400_with_json_object_format(self, request_mock) -> None:
        request_mock.side_effect = [ProviderHTTPError(400), provider_result(True, False)]

        result = _grade_pseudocode(
            "두 수를 더해 출력한다.",
            PUBLIC_PROBLEM,
            PRIVATE_PROBLEM,
        )

        self.assertTrue(result["passed"])
        self.assertEqual(request_mock.call_count, 2)
        first_payload = request_mock.call_args_list[0].kwargs["payload"]
        retry_payload = request_mock.call_args_list[1].kwargs["payload"]
        self.assertEqual(first_payload["response_format"]["type"], "json_schema")
        self.assertEqual(retry_payload["response_format"], {"type": "json_object"})

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
    def test_does_not_retry_non_400_provider_error(self, request_mock) -> None:
        request_mock.side_effect = ProviderHTTPError(429)

        with self.assertRaises(ProviderHTTPError):
            _grade_pseudocode(
                "두 수를 더해 출력한다.",
                PUBLIC_PROBLEM,
                PRIVATE_PROBLEM,
            )

        request_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()

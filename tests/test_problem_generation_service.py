import unittest
from unittest.mock import patch

from api.problem_generation_service import (
    ProblemGenerationError,
    _reference_tests,
    _store_generated_problem,
    _unique_problem_id,
    _validate_generated_content,
    _validate_reference_solutions,
    create_problem,
    generate_problem,
)
from api.submission_service import ProviderError


def valid_generated_content() -> dict:
    return {
        "id_suggestion": "two-pointer-window",
        "title": "두 포인터 구간",
        "tags": ["two-pointers", "array"],
        "statement": {
            "summary": "조건을 만족하는 가장 짧은 구간을 찾습니다.",
            "description": "양의 정수 배열에서 합이 S 이상인 가장 짧은 연속 구간 길이를 출력합니다.",
            "input": "첫 줄에 N과 S, 둘째 줄에 배열이 주어집니다.",
            "output": "가장 짧은 구간 길이를 출력합니다.",
            "constraints": ["1 <= N <= 100000", "모든 원소는 양의 정수입니다."],
        },
        "examples": [
            {"input": "3 5\n1 2 3\n", "output": "2\n", "explanation": "2+3은 5입니다."},
            {"input": "2 10\n1 2\n", "output": "0\n", "explanation": "조건을 만족하는 구간이 없습니다."},
        ],
        "beginner_prompt": "왼쪽과 오른쪽 포인터의 이동 과정을 작성하세요.",
        "intermediate_skeletons": {
            "python": "# TODO: implement\n",
            "cpp": "int main() { /* TODO */ }\n",
        },
        "expert_templates": {
            "python": "def solve():\n    pass\n",
            "cpp": "int main() { return 0; }\n",
        },
        "pseudocode_rubric": {
            "pass_score": 70,
            "criteria": [
                {"id": "window", "description": "구간을 관리한다.", "weight": 40},
                {"id": "shrink", "description": "조건을 만족하면 줄인다.", "weight": 40},
                {"id": "answer", "description": "최솟값을 기록한다.", "weight": 20},
            ],
        },
        "reference_solutions": {
            "python": "print(0)\n",
            "cpp": "int main() { return 0; }\n",
        },
        "hidden_tests": [
            {"name": "single", "input": "1 1\n1\n", "expected_output": "1\n"},
            {"name": "none", "input": "1 2\n1\n", "expected_output": "0\n"},
            {"name": "full", "input": "2 2\n1 1\n", "expected_output": "2\n"},
        ],
    }


class ProblemGenerationValidationTest(unittest.TestCase):
    def test_accepts_complete_structured_problem(self) -> None:
        value = valid_generated_content()
        self.assertIs(_validate_generated_content(value), value)

    def test_rejects_rubric_weights_that_do_not_sum_to_one_hundred(self) -> None:
        value = valid_generated_content()
        value["pseudocode_rubric"]["criteria"][0]["weight"] = 30
        with self.assertRaises(ProblemGenerationError):
            _validate_generated_content(value)

    def test_rejects_non_numeric_rubric_weight_as_validation_error(self) -> None:
        value = valid_generated_content()
        value["pseudocode_rubric"]["criteria"][0]["weight"] = "40"
        with self.assertRaises(ProblemGenerationError):
            _validate_generated_content(value)

    def test_rejects_non_portable_cpp_headers(self) -> None:
        value = valid_generated_content()
        value["reference_solutions"]["cpp"] = (
            "#include <bits/stdc++.h>\nint main() { return 0; }\n"
        )
        with self.assertRaisesRegex(ProblemGenerationError, "C\\+\\+17"):
            _validate_generated_content(value)

    def test_manual_problem_rejects_incomplete_statement(self) -> None:
        value = valid_generated_content()
        del value["statement"]["output"]
        with self.assertRaisesRegex(ProblemGenerationError, "문제 설명"):
            create_problem(value, "medium")

    def test_duplicate_id_gets_a_stable_suffix(self) -> None:
        self.assertEqual(
            _unique_problem_id("two-pointer-window", {"two-pointer-window"}),
            "two-pointer-window-2",
        )

    @patch("api.problem_generation_service.store_database_problem")
    @patch("api.problem_generation_service.database_enabled", return_value=True)
    def test_database_storage_builds_the_same_public_and_private_documents(
        self, _database_enabled_mock, store_database_problem_mock
    ) -> None:
        store_database_problem_mock.return_value = {
            "bank_version": 6,
            "problem": {
                "id": "two-pointer-window",
                "title": "투 포인터 구간",
                "difficulty": "medium",
            },
        }
        content = valid_generated_content()

        result = _store_generated_problem(content, "medium")

        self.assertEqual(result["bank_version"], 6)
        id_suggestion, difficulty, factory = store_database_problem_mock.call_args.args
        self.assertEqual(id_suggestion, "two-pointer-window")
        self.assertEqual(difficulty, "medium")
        public_problem, private_problem = factory("two-pointer-window-2")
        self.assertEqual(public_problem["id"], "two-pointer-window-2")
        self.assertEqual(public_problem["modes"]["intermediate"]["time_limit_seconds"], 330)
        self.assertEqual(private_problem["problem_id"], "two-pointer-window-2")
        self.assertEqual(private_problem["hidden_tests"], content["hidden_tests"])

    @patch("api.problem_generation_service._grade_code")
    def test_reference_validation_runs_every_case_in_both_languages(
        self, grade_code_mock
    ) -> None:
        value = valid_generated_content()
        grade_code_mock.return_value = {
            "passed": True,
            "status": "accepted",
            "passed_tests": 5,
            "total_tests": 5,
        }

        _validate_reference_solutions(value)

        self.assertEqual(grade_code_mock.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in grade_code_mock.call_args_list],
            ["python", "cpp"],
        )
        expected_tests = _reference_tests(value)
        self.assertEqual(len(expected_tests), 5)
        for language, call in zip(
            ("python", "cpp"), grade_code_mock.call_args_list, strict=True
        ):
            self.assertEqual(call.args[1], value["reference_solutions"][language])
            self.assertEqual(call.args[2], expected_tests)

    @patch("api.problem_generation_service._store_generated_problem")
    @patch("api.problem_generation_service._grade_code")
    @patch("api.problem_generation_service._request_generated_content")
    def test_reference_failure_prevents_problem_from_being_stored(
        self,
        request_content_mock,
        grade_code_mock,
        store_problem_mock,
    ) -> None:
        value = valid_generated_content()
        request_content_mock.return_value = (value, "test-model")
        grade_code_mock.side_effect = [
            {
                "passed": True,
                "status": "accepted",
                "passed_tests": 5,
                "total_tests": 5,
            },
            {
                "passed": False,
                "status": "wrong_answer",
                "passed_tests": 4,
                "total_tests": 5,
            },
        ]

        with self.assertRaisesRegex(ProblemGenerationError, "C\\+\\+"):
            generate_problem("create a window problem", "easy")

        store_problem_mock.assert_not_called()

    @patch(
        "api.problem_generation_service._grade_code",
        side_effect=ProviderError("judge unavailable"),
    )
    def test_reference_validation_preserves_provider_errors(
        self, _grade_code_mock
    ) -> None:
        with self.assertRaisesRegex(ProviderError, "judge unavailable"):
            _validate_reference_solutions(valid_generated_content())

    @patch("api.problem_generation_service._store_generated_problem")
    @patch("api.problem_generation_service._grade_code")
    def test_manual_problem_uses_the_same_validation_and_storage_path(
        self, grade_code_mock, store_problem_mock
    ) -> None:
        grade_code_mock.return_value = {
            "passed": True,
            "status": "accepted",
            "passed_tests": 5,
            "total_tests": 5,
        }
        store_problem_mock.return_value = {
            "bank_version": 8,
            "problem": {
                "id": "two-pointer-window",
                "title": "두 포인터 구간",
                "difficulty": "medium",
            },
        }
        value = valid_generated_content()

        result = create_problem(value, "medium")

        self.assertEqual(result["bank_version"], 8)
        self.assertEqual(grade_code_mock.call_count, 2)
        store_problem_mock.assert_called_once_with(value, "medium")


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from unittest.mock import patch

from api.index import app
from api.solution import app as solution_app
from api.solution_service import (
    SOLUTION_TOKEN_TTL_SECONDS,
    issue_solution_access_token,
)


class SolutionApiTest(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.environment = patch.dict(
            "os.environ",
            {"APP_ENV": "test", "SOLUTION_TOKEN_SECRET": "solution-api-test-secret"},
        )
        self.environment.start()
        self.scope = {
            "problem_id": "sum-two-numbers",
            "version": 2,
            "mode": "intermediate",
            "language": "python",
        }

    def tearDown(self) -> None:
        self.environment.stop()

    @staticmethod
    def wrong_result(mode: str = "intermediate") -> dict:
        if mode == "beginner":
            return {
                "kind": "pseudocode",
                "status": "evaluated",
                "passed": False,
                "score": 40,
                "feedback": "논리를 다시 확인해 주세요.",
                "missing_steps": ["정답 출력"],
            }
        return {
            "kind": "code",
            "status": "wrong_answer",
            "passed": False,
            "score": 40,
            "feedback": "일부 테스트를 통과하지 못했습니다.",
            "passed_tests": 2,
            "total_tests": 5,
        }

    def submit_payload(self, mode: str = "intermediate") -> dict:
        return {
            **self.scope,
            "mode": mode,
            "answer": "틀린 답안",
        }

    def solution_payload(self, token: str, **overrides) -> dict:
        return {
            **self.scope,
            "solution_access_token": token,
            **overrides,
        }

    def test_vercel_solution_entrypoint_exports_the_same_app(self) -> None:
        self.assertIs(solution_app, app)

    def test_each_failed_mode_receives_a_solution_access_token(self) -> None:
        for mode in ("beginner", "intermediate", "expert"):
            with self.subTest(mode=mode), patch(
                "api.index.grade_submission", return_value=self.wrong_result(mode)
            ):
                response = self.client.post(
                    "/api/submit", json=self.submit_payload(mode)
                )

            self.assertEqual(response.status_code, 200)
            token = response.json["result"].get("solution_access_token")
            self.assertIsInstance(token, str)
            self.assertGreater(len(token), 40)

    @patch("api.index.grade_submission")
    def test_successful_submission_does_not_receive_a_token(
        self, grade_submission_mock
    ) -> None:
        grade_submission_mock.return_value = {
            "kind": "code",
            "status": "accepted",
            "passed": True,
            "score": 100,
            "feedback": "통과",
            "passed_tests": 5,
            "total_tests": 5,
        }

        response = self.client.post("/api/submit", json=self.submit_payload())

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("solution_access_token", response.json["result"])

    def test_solution_rejects_missing_or_empty_token(self) -> None:
        without_token = self.client.post("/api/solution", json=self.scope)
        with_empty_token = self.client.post(
            "/api/solution",
            json={**self.scope, "solution_access_token": " "},
        )

        self.assertEqual(without_token.status_code, 400)
        self.assertEqual(with_empty_token.status_code, 400)

    def test_solution_rejects_tampered_token(self) -> None:
        token = issue_solution_access_token(**self.scope)
        replacement = "A" if token[-1] != "A" else "B"
        tampered_token = token[:-1] + replacement

        response = self.client.post(
            "/api/solution", json=self.solution_payload(tampered_token)
        )

        self.assertEqual(response.status_code, 403)

    def test_solution_rejects_expired_token(self) -> None:
        issued_at = 1_000_000
        with patch("api.solution_service._current_time", return_value=issued_at):
            token = issue_solution_access_token(**self.scope)
        with patch(
            "api.solution_service._current_time",
            return_value=issued_at + SOLUTION_TOKEN_TTL_SECONDS,
        ):
            response = self.client.post(
                "/api/solution", json=self.solution_payload(token)
            )

        self.assertEqual(response.status_code, 403)
        self.assertIn("만료", response.json["error"]["message"])

    def test_solution_rejects_a_token_from_another_scope(self) -> None:
        token = issue_solution_access_token(**self.scope)

        response = self.client.post(
            "/api/solution",
            json=self.solution_payload(token, mode="expert"),
        )

        self.assertEqual(response.status_code, 403)

    @patch("api.index.grade_submission")
    def test_valid_grant_returns_the_requested_solution(
        self, grade_submission_mock
    ) -> None:
        grade_submission_mock.return_value = self.wrong_result()
        submission = self.client.post("/api/submit", json=self.submit_payload())
        token = submission.json["result"]["solution_access_token"]

        response = self.client.post(
            "/api/solution", json=self.solution_payload(token)
        )

        self.assertEqual(response.status_code, 200)
        solution = response.json["solution"]
        self.assertEqual(solution["problem_id"], "sum-two-numbers")
        self.assertEqual(solution["version"], 2)
        self.assertEqual(solution["mode"], "intermediate")
        self.assertEqual(solution["language"], "python")
        self.assertEqual(solution["title"], "목표 합 부분 배열 개수")
        self.assertEqual(solution["summary"], "합이 K인 연속 부분 배열의 개수를 구합니다.")
        self.assertEqual(len(solution["steps"]), 4)
        self.assertIn("누적합", solution["steps"][0])
        self.assertIn("from collections import defaultdict", solution["reference_solution"])
        self.assertEqual(
            set(solution),
            {
                "problem_id",
                "version",
                "mode",
                "language",
                "title",
                "summary",
                "steps",
                "reference_solution",
            },
        )

    @patch("api.index.grade_submission")
    def test_problem_and_failed_submission_do_not_reveal_solution_before_request(
        self, grade_submission_mock
    ) -> None:
        grade_submission_mock.return_value = self.wrong_result()
        problem = self.client.get(
            "/api/problem",
            query_string={
                "difficulty": "easy",
                "problem_id": "sum-two-numbers",
                "mode": "intermediate",
                "language": "python",
            },
        )
        submission = self.client.post("/api/submit", json=self.submit_payload())

        self.assertEqual(problem.status_code, 200)
        self.assertEqual(submission.status_code, 200)
        for response in (problem, submission):
            serialized = json.dumps(response.json, ensure_ascii=False)
            self.assertNotIn("reference_solution", serialized)
            self.assertNotIn("reference_solutions", serialized)
            self.assertNotIn("hidden_tests", serialized)
            self.assertNotIn("pseudocode_rubric", serialized)
            self.assertNotIn("prefix = answer = 0", serialized)


if __name__ == "__main__":
    unittest.main()

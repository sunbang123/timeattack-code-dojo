import unittest
from pathlib import Path
from unittest.mock import patch

import api.problem_service as problem_service
from api.index import app
from api.health import app as health_app
from api.create_problem import app as create_problem_app
from api.generate_problem import app as generate_problem_app
from api.problem import app as problem_app
from api.submit import app as submit_app
from api.problem_service import load_manifest
from api.problem_generation_service import ProblemGenerationError
from api.submission_service import ProviderError


class ApiTest(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_health_endpoint(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")
        self.assertEqual(response.json["service"], "timeattack-api")
        self.assertEqual(response.json["runtime"], "python")
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertTrue(response.headers["X-Request-ID"])

    def test_not_found_uses_common_error_shape(self) -> None:
        response = self.client.get("/missing")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"]["code"], 404)
        self.assertTrue(response.json["error"]["request_id"])

    def test_vercel_health_entrypoint_exports_the_same_app(self) -> None:
        self.assertIs(health_app, app)

    def test_vercel_problem_entrypoint_exports_the_same_app(self) -> None:
        self.assertIs(problem_app, app)

    def test_vercel_generate_problem_entrypoint_exports_the_same_app(self) -> None:
        self.assertIs(generate_problem_app, app)

    def test_vercel_create_problem_entrypoint_exports_the_same_app(self) -> None:
        self.assertIs(create_problem_app, app)

    def test_vercel_submit_entrypoint_exports_the_same_app(self) -> None:
        self.assertIs(submit_app, app)


class ProblemGenerationApiTest(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.payload = {
            "prompt": "투 포인터를 연습할 수 있는 문자열 문제를 만들어 주세요.",
            "difficulty": "medium",
        }

    @patch("api.index.generate_problem")
    def test_generation_returns_created_problem(self, generate_mock) -> None:
        generate_mock.return_value = {
            "bank_version": 5,
            "model": "test-model",
            "problem": {
                "id": "two-pointer-string",
                "title": "문자열 구간 찾기",
                "difficulty": "medium",
            },
        }

        response = self.client.post("/api/generate_problem", json=self.payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["problem"]["id"], "two-pointer-string")
        generate_mock.assert_called_once_with(self.payload["prompt"], "medium")

    def test_generation_rejects_unknown_fields(self) -> None:
        response = self.client.post(
            "/api/generate_problem", json={**self.payload, "debug": True}
        )
        self.assertEqual(response.status_code, 400)

    @patch(
        "api.index.generate_problem",
        side_effect=ProblemGenerationError("문제 요청이 너무 짧습니다."),
    )
    def test_generation_maps_validation_error_to_bad_request(self, _generate_mock) -> None:
        response = self.client.post("/api/generate_problem", json=self.payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"]["message"], "문제 요청이 너무 짧습니다.")


    @patch(
        "api.index.generate_problem",
        side_effect=ProviderError("judge unavailable"),
    )
    def test_generation_maps_judge_failure_to_bad_gateway(self, _generate_mock) -> None:
        response = self.client.post("/api/generate_problem", json=self.payload)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json["error"]["message"], "judge unavailable")

    @patch("api.index.generate_problem")
    @patch.dict(
        "os.environ",
        {"APP_ENV": "production", "PROBLEM_AUTHOR_TOKEN": ""},
    )
    def test_generation_requires_server_author_key_configuration(
        self, generate_mock
    ) -> None:
        response = self.client.post("/api/generate_problem", json=self.payload)

        self.assertEqual(response.status_code, 503)
        generate_mock.assert_not_called()

    @patch("api.index.generate_problem")
    @patch.dict(
        "os.environ",
        {"APP_ENV": "production", "PROBLEM_AUTHOR_TOKEN": "test-author-key"},
    )
    def test_generation_rejects_an_invalid_author_key(self, generate_mock) -> None:
        response = self.client.post(
            "/api/generate_problem",
            json=self.payload,
            headers={"Authorization": "Bearer wrong-key"},
        )

        self.assertEqual(response.status_code, 401)
        generate_mock.assert_not_called()

    @patch("api.index.generate_problem")
    @patch.dict(
        "os.environ",
        {"APP_ENV": "production", "PROBLEM_AUTHOR_TOKEN": "test-author-key"},
    )
    def test_generation_accepts_the_configured_author_key(self, generate_mock) -> None:
        generate_mock.return_value = {
            "bank_version": 6,
            "model": "test-model",
            "problem": {
                "id": "authorized-problem",
                "title": "Authorized problem",
                "difficulty": "medium",
            },
        }

        response = self.client.post(
            "/api/generate_problem",
            json=self.payload,
            headers={"Authorization": "Bearer test-author-key"},
        )

        self.assertEqual(response.status_code, 201)
        generate_mock.assert_called_once()


class ProblemCreationApiTest(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.payload = {
            "content": {"id_suggestion": "manual-problem"},
            "difficulty": "easy",
        }

    @patch("api.index.create_problem")
    def test_manual_creation_returns_created_problem(self, create_mock) -> None:
        create_mock.return_value = {
            "bank_version": 6,
            "problem": {
                "id": "manual-problem",
                "title": "직접 만든 문제",
                "difficulty": "easy",
            },
        }

        response = self.client.post("/api/create_problem", json=self.payload)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["problem"]["id"], "manual-problem")
        create_mock.assert_called_once_with(self.payload["content"], "easy")

    def test_manual_creation_rejects_unknown_fields(self) -> None:
        response = self.client.post(
            "/api/create_problem", json={**self.payload, "debug": True}
        )
        self.assertEqual(response.status_code, 400)

    @patch(
        "api.index.create_problem",
        side_effect=ProblemGenerationError("입력한 문제 데이터가 올바르지 않습니다."),
    )
    def test_manual_creation_maps_validation_error_to_bad_request(
        self, _create_mock
    ) -> None:
        response = self.client.post("/api/create_problem", json=self.payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json["error"]["message"],
            "입력한 문제 데이터가 올바르지 않습니다.",
        )


class SubmissionApiTest(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.payload = {
            "problem_id": "sum-two-numbers",
            "version": 2,
            "mode": "intermediate",
            "language": "python",
            "answer": "print(1)",
        }

    @patch("api.index.grade_submission")
    def test_submit_returns_safe_grading_result(self, grade_submission_mock) -> None:
        grade_submission_mock.return_value = {
            "kind": "code",
            "status": "accepted",
            "passed": True,
            "score": 100,
            "feedback": "통과",
            "passed_tests": 5,
            "total_tests": 5,
        }

        response = self.client.post("/api/submit", json=self.payload)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["result"]["passed"])
        grade_submission_mock.assert_called_once_with(
            "sum-two-numbers", 2, "intermediate", "python", "print(1)"
        )

    def test_submit_rejects_empty_and_unknown_fields(self) -> None:
        empty = self.client.post("/api/submit", json={**self.payload, "answer": " "})
        unknown = self.client.post(
            "/api/submit", json={**self.payload, "debug": True}
        )

        self.assertEqual(empty.status_code, 400)
        self.assertEqual(unknown.status_code, 400)

    @patch("api.index.grade_submission", side_effect=ProviderError("provider down"))
    def test_submit_maps_provider_failure_to_bad_gateway(self, _grade_submission_mock) -> None:
        response = self.client.post("/api/submit", json=self.payload)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json["error"]["message"], "provider down")


class ProblemApiTest(unittest.TestCase):
    def setUp(self) -> None:
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def get_problem(self, **parameters: str):
        defaults = {
            "mode": "beginner",
            "language": "python",
        }
        return self.client.get("/api/problem", query_string={**defaults, **parameters})

    def test_all_modes_and_languages_return_mode_specific_payloads(self) -> None:
        for mode in ("beginner", "intermediate", "expert"):
            for language in ("python", "cpp"):
                with self.subTest(mode=mode, language=language):
                    response = self.get_problem(mode=mode, language=language)

                    self.assertEqual(response.status_code, 200)
                    problem = response.json["problem"]
                    self.assertEqual(problem["mode"], mode)
                    self.assertEqual(problem["language"], language)
                    self.assertEqual(
                        response.json["bank_version"], load_manifest()["bank_version"]
                    )
                    if mode == "beginner":
                        self.assertEqual(problem["answer_format"], "pseudocode")
                        self.assertIn("prompt", problem)
                        self.assertNotIn("starter_code", problem)
                    else:
                        self.assertEqual(problem["answer_format"], "code")
                        self.assertIn("starter_code", problem)
                        self.assertNotIn("prompt", problem)

    def test_all_difficulties_return_a_problem(self) -> None:
        expected_ids = {
            "easy": "add-two-integers",
            "medium": "valid-bracket-string",
            "hard": "shortest-path-basic",
        }
        for difficulty, expected_id in expected_ids.items():
            with self.subTest(difficulty=difficulty):
                response = self.get_problem(difficulty=difficulty)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["problem"]["id"], expected_id)

    def test_bundled_problem_bank_works_without_source_json_files(self) -> None:
        caches = (
            problem_service.load_manifest,
            problem_service.load_public_problem,
            problem_service.load_private_problem,
            problem_service.load_problem_bank_bundle,
        )
        try:
            with patch.object(
                problem_service,
                "PROBLEM_BANK_ROOT",
                Path("__missing_problem_bank__"),
            ):
                for cached_function in caches:
                    cached_function.cache_clear()
                response = self.get_problem(mode="intermediate", language="cpp")

                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.json["available_problems"]), 13)
                problem_id = response.json["problem"]["id"]
                self.assertEqual(
                    problem_service.load_private_problem(problem_id)["problem_id"],
                    problem_id,
                )
        finally:
            for cached_function in caches:
                cached_function.cache_clear()

    def test_every_seed_problem_supports_every_mode_and_language(self) -> None:
        for entry in load_manifest()["problems"]:
            for mode in ("beginner", "intermediate", "expert"):
                for language in ("python", "cpp"):
                    with self.subTest(
                        problem_id=entry["id"], mode=mode, language=language
                    ):
                        response = self.get_problem(
                            difficulty=entry["difficulty"],
                            problem_id=entry["id"],
                            mode=mode,
                            language=language,
                        )

                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.json["problem"]["id"], entry["id"])

    def test_problem_id_selects_from_the_complete_problem_list(self) -> None:
        response = self.get_problem(problem_id="count-vowels")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["problem"]["id"], "count-vowels")
        self.assertEqual(
            [item["id"] for item in response.json["available_problems"]],
            [entry["id"] for entry in load_manifest()["problems"]],
        )

    def test_difficulty_is_optional_and_only_filters_when_requested(self) -> None:
        complete = self.get_problem()
        easy_only = self.get_problem(difficulty="easy")

        self.assertEqual(complete.status_code, 200)
        expected_total = len(load_manifest()["problems"])
        expected_easy = sum(
            entry["difficulty"] == "easy" for entry in load_manifest()["problems"]
        )
        self.assertEqual(len(complete.json["available_problems"]), expected_total)
        self.assertEqual(len(easy_only.json["available_problems"]), expected_easy)
        self.assertTrue(
            all(
                problem["difficulty"] == "easy"
                for problem in easy_only.json["available_problems"]
            )
        )

    def test_response_never_contains_private_or_unrequested_mode_fields(self) -> None:
        forbidden_keys = {
            "hidden_tests",
            "reference_solutions",
            "pseudocode_rubric",
            "modes",
            "skeletons",
            "starter_templates",
        }
        for mode in ("beginner", "intermediate", "expert"):
            response = self.get_problem(mode=mode, language="cpp")
            keys = self.collect_keys(response.json)

            self.assertTrue(forbidden_keys.isdisjoint(keys))

    def test_missing_parameter_uses_common_error_shape(self) -> None:
        response = self.client.get(
            "/api/problem", query_string={"difficulty": "easy", "mode": "beginner"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"]["code"], 400)
        self.assertIn("language", response.json["error"]["message"])
        self.assertTrue(response.json["error"]["request_id"])

    def test_invalid_parameter_values_are_rejected(self) -> None:
        invalid_cases = {
            "difficulty": "impossible",
            "mode": "speedrun",
            "language": "javascript",
        }
        for name, value in invalid_cases.items():
            with self.subTest(parameter=name):
                response = self.get_problem(**{name: value})

                self.assertEqual(response.status_code, 400)
                self.assertIn(name, response.json["error"]["message"])

    def test_unknown_and_duplicate_parameters_are_rejected(self) -> None:
        unknown = self.client.get(
            "/api/problem?difficulty=easy&mode=beginner&language=python&debug=true"
        )
        duplicate = self.client.get(
            "/api/problem?difficulty=easy&difficulty=hard&mode=beginner&language=python"
        )

        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(duplicate.status_code, 400)

    def test_unknown_or_mismatched_problem_id_returns_not_found(self) -> None:
        unknown = self.get_problem(problem_id="does-not-exist")
        mismatched = self.get_problem(
            difficulty="hard", problem_id="sum-two-numbers"
        )

        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(mismatched.status_code, 404)

    @classmethod
    def collect_keys(cls, value):
        if isinstance(value, dict):
            return set(value) | set().union(
                *(cls.collect_keys(item) for item in value.values())
            )
        if isinstance(value, list):
            return set().union(*(cls.collect_keys(item) for item in value))
        return set()


if __name__ == "__main__":
    unittest.main()

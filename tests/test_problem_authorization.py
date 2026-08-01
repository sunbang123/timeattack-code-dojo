import json
import unittest
from urllib.error import HTTPError
from unittest.mock import MagicMock, patch

from api.problem_authorization import (
    ProblemAuthorConfigurationError,
    ProblemAuthorForbiddenError,
    ProblemAuthorUnauthorizedError,
    verify_problem_authorization,
)
from api.problem_repository import ProblemRepositoryError


class ProblemAuthorizationTest(unittest.TestCase):
    settings = {
        "SUPABASE_URL": "https://project.supabase.co",
        "SUPABASE_PUBLISHABLE_KEY": "sb_publishable_test",
    }

    def verified_response(self):
        response = MagicMock()
        response.read.return_value = json.dumps(
            {
                "id": "3a8a10fb-2f57-4707-bd90-e24566cd449c",
                "email": "Admin@Example.com",
                "email_confirmed_at": "2026-08-01T00:00:00Z",
            }
        ).encode("utf-8")
        response.__enter__.return_value = response
        return response

    @patch.dict("os.environ", settings, clear=True)
    @patch("api.problem_authorization.claim_or_verify_problem_admin", return_value=True)
    @patch("api.problem_authorization.urlopen")
    def test_verified_allowlisted_user_is_returned(
        self, urlopen_mock, claim_admin_mock
    ) -> None:
        urlopen_mock.return_value = self.verified_response()

        author = verify_problem_authorization("Bearer session-token")

        self.assertEqual(author.email, "admin@example.com")
        self.assertEqual(author.user_id, "3a8a10fb-2f57-4707-bd90-e24566cd449c")
        claim_admin_mock.assert_called_once_with(author.user_id, author.email)
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, "https://project.supabase.co/auth/v1/user")
        self.assertEqual(request.get_header("Authorization"), "Bearer session-token")

    @patch.dict("os.environ", settings, clear=True)
    @patch("api.problem_authorization.urlopen")
    def test_expired_supabase_session_is_unauthorized(self, urlopen_mock) -> None:
        urlopen_mock.side_effect = HTTPError(
            "https://project.supabase.co/auth/v1/user", 401, "Unauthorized", None, None
        )

        with self.assertRaises(ProblemAuthorUnauthorizedError):
            verify_problem_authorization("Bearer expired-token")

    @patch.dict("os.environ", settings, clear=True)
    @patch("api.problem_authorization.claim_or_verify_problem_admin", return_value=False)
    @patch("api.problem_authorization.urlopen")
    def test_verified_non_admin_user_is_forbidden(
        self, urlopen_mock, _claim_admin_mock
    ) -> None:
        urlopen_mock.return_value = self.verified_response()

        with self.assertRaises(ProblemAuthorForbiddenError):
            verify_problem_authorization("Bearer member-token")

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_server_settings_fail_closed(self) -> None:
        with self.assertRaises(ProblemAuthorConfigurationError):
            verify_problem_authorization("Bearer session-token")

    def test_missing_bearer_token_is_unauthorized(self) -> None:
        with self.assertRaises(ProblemAuthorUnauthorizedError):
            verify_problem_authorization(None)

    @patch.dict("os.environ", settings, clear=True)
    @patch(
        "api.problem_authorization.claim_or_verify_problem_admin",
        side_effect=ProblemRepositoryError("database unavailable"),
    )
    @patch("api.problem_authorization.urlopen")
    def test_repository_failure_is_a_configuration_error(
        self, urlopen_mock, _claim_admin_mock
    ) -> None:
        urlopen_mock.return_value = self.verified_response()

        with self.assertRaises(ProblemAuthorConfigurationError):
            verify_problem_authorization("Bearer session-token")


if __name__ == "__main__":
    unittest.main()

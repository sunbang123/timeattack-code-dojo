"""Server-side authorization for problem authoring endpoints."""

from __future__ import annotations

import hmac
import os


class ProblemAuthorConfigurationError(RuntimeError):
    """Production authoring protection is not configured."""


class ProblemAuthorUnauthorizedError(RuntimeError):
    """A problem authoring request has invalid credentials."""


def verify_problem_authorization(authorization_header: str | None) -> None:
    expected_token = os.getenv("PROBLEM_AUTHOR_TOKEN", "").strip()
    is_deployed = (
        os.getenv("VERCEL", "").strip() == "1"
        or os.getenv("APP_ENV", "development").strip().lower()
        in {"production", "staging"}
    )
    if not expected_token:
        if is_deployed:
            raise ProblemAuthorConfigurationError(
                "문제 생성용 관리자 키가 서버에 설정되지 않았습니다."
            )
        return

    scheme, separator, supplied_token = (authorization_header or "").partition(" ")
    if (
        separator != " "
        or scheme.lower() != "bearer"
        or not supplied_token
        or not hmac.compare_digest(supplied_token, expected_token)
    ):
        raise ProblemAuthorUnauthorizedError("관리자 키가 올바르지 않습니다.")

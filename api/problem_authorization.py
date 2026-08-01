"""Supabase-backed authorization for problem authoring endpoints."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from api.problem_repository import (
    ProblemRepositoryError,
    claim_or_verify_problem_admin,
)


class ProblemAuthorConfigurationError(RuntimeError):
    """Problem authoring authentication is not configured or unavailable."""


class ProblemAuthorUnauthorizedError(RuntimeError):
    """A problem authoring request has no valid Supabase session."""


class ProblemAuthorForbiddenError(RuntimeError):
    """The signed-in account is not allowed to author problems."""


@dataclass(frozen=True)
class ProblemAuthor:
    user_id: str
    email: str


def _supabase_settings() -> tuple[str, str]:
    url = (
        os.getenv("SUPABASE_URL", "").strip()
        or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").strip()
    )
    publishable_key = (
        os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
        or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "").strip()
        or os.getenv("SUPABASE_ANON_KEY", "").strip()
        or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "").strip()
    )
    if not url or not publishable_key:
        raise ProblemAuthorConfigurationError(
            "Supabase 관리자 로그인이 서버에 설정되지 않았습니다."
        )
    return url.rstrip("/"), publishable_key


def _bearer_token(authorization_header: str | None) -> str:
    scheme, separator, token = (authorization_header or "").partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise ProblemAuthorUnauthorizedError("관리자 로그인이 필요합니다.")
    return token.strip()


def _get_verified_supabase_user(access_token: str) -> ProblemAuthor:
    url, publishable_key = _supabase_settings()
    request = Request(
        f"{url}/auth/v1/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "apikey": publishable_key,
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code in {401, 403}:
            raise ProblemAuthorUnauthorizedError(
                "관리자 로그인 세션이 만료되었거나 올바르지 않습니다."
            ) from error
        raise ProblemAuthorConfigurationError(
            "Supabase 인증 서버가 요청을 처리하지 못했습니다."
        ) from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ProblemAuthorConfigurationError(
            "Supabase 인증 서버에 연결하지 못했습니다."
        ) from error

    if not isinstance(payload, dict):
        raise ProblemAuthorUnauthorizedError("관리자 로그인 세션이 올바르지 않습니다.")
    user_id = payload.get("id")
    email = payload.get("email")
    email_confirmed_at = payload.get("email_confirmed_at")
    if (
        not isinstance(user_id, str)
        or not isinstance(email, str)
        or not isinstance(email_confirmed_at, str)
    ):
        raise ProblemAuthorUnauthorizedError("이메일이 확인된 로그인이 필요합니다.")
    return ProblemAuthor(user_id=user_id, email=email.strip().lower())


def verify_problem_authorization(
    authorization_header: str | None,
) -> ProblemAuthor:
    author = _get_verified_supabase_user(_bearer_token(authorization_header))
    try:
        is_admin = claim_or_verify_problem_admin(author.user_id, author.email)
    except ProblemRepositoryError as error:
        raise ProblemAuthorConfigurationError(
            "관리자 권한 저장소를 확인하지 못했습니다."
        ) from error
    if not is_admin:
        raise ProblemAuthorForbiddenError("문제 등록 권한이 없는 계정입니다.")
    return author

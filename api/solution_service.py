"""Issue short-lived solution grants and serialize private solution material."""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
from time import time as _current_time
from typing import Any

from api.problem_service import (
    LANGUAGES,
    MODES,
    PROBLEM_BANK_ROOT,
    ProblemBankError,
    load_public_problem,
)


SOLUTION_TOKEN_TTL_SECONDS = 10 * 60
_DEVELOPMENT_SECRET = "timeattack-code-dojo-development-solution-token-secret"
_TOKEN_PART_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_PROBLEM_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_CLAIM_KEYS = {"problem_id", "version", "mode", "language", "issued_at", "expires_at"}


class SolutionAccessError(RuntimeError):
    """A solution access token is absent, invalid, expired, or out of scope."""


class SolutionConfigurationError(RuntimeError):
    """The server cannot securely issue or verify solution access tokens."""


class SolutionDataError(RuntimeError):
    """Private solution data is missing or inconsistent with public data."""


def _token_secret() -> bytes:
    configured = os.getenv("SOLUTION_TOKEN_SECRET", "").strip()
    if configured:
        return configured.encode("utf-8")

    environment = os.getenv("APP_ENV", "development").strip().lower()
    if environment in {"development", "test"}:
        return _DEVELOPMENT_SECRET.encode("utf-8")
    raise SolutionConfigurationError(
        "SOLUTION_TOKEN_SECRET must be configured outside development."
    )


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    if not value or not _TOKEN_PART_PATTERN.fullmatch(value):
        raise ValueError("invalid base64url value")
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _signature(encoded_claims: str) -> str:
    digest = hmac.new(
        _token_secret(), encoded_claims.encode("ascii"), hashlib.sha256
    ).digest()
    return _base64url_encode(digest)


def issue_solution_access_token(
    problem_id: str,
    version: int,
    mode: str,
    language: str,
) -> str:
    """Return an HMAC-signed grant scoped to one failed submission context."""
    issued_at = int(_current_time())
    claims = {
        "problem_id": problem_id,
        "version": version,
        "mode": mode,
        "language": language,
        "issued_at": issued_at,
        "expires_at": issued_at + SOLUTION_TOKEN_TTL_SECONDS,
    }
    encoded_claims = _base64url_encode(
        json.dumps(
            claims, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    )
    return f"{encoded_claims}.{_signature(encoded_claims)}"


def _validate_claims(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _CLAIM_KEYS:
        raise SolutionAccessError("정답 보기 권한이 올바르지 않습니다.")
    if not isinstance(value["problem_id"], str) or not _PROBLEM_ID_PATTERN.fullmatch(
        value["problem_id"]
    ):
        raise SolutionAccessError("정답 보기 권한이 올바르지 않습니다.")
    if (
        not isinstance(value["version"], int)
        or isinstance(value["version"], bool)
        or value["version"] < 1
    ):
        raise SolutionAccessError("정답 보기 권한이 올바르지 않습니다.")
    if value["mode"] not in MODES or value["language"] not in LANGUAGES:
        raise SolutionAccessError("정답 보기 권한이 올바르지 않습니다.")
    for name in ("issued_at", "expires_at"):
        if not isinstance(value[name], int) or isinstance(value[name], bool):
            raise SolutionAccessError("정답 보기 권한이 올바르지 않습니다.")
    if value["expires_at"] <= value["issued_at"]:
        raise SolutionAccessError("정답 보기 권한이 올바르지 않습니다.")
    return value


def verify_solution_access_token(
    token: str,
    *,
    problem_id: str,
    version: int,
    mode: str,
    language: str,
) -> dict[str, Any]:
    """Verify signature, expiry, and the exact problem submission scope."""
    try:
        if not isinstance(token, str) or len(token) > 4096:
            raise ValueError("invalid token")
        encoded_claims, supplied_signature = token.split(".")
        if not _TOKEN_PART_PATTERN.fullmatch(
            encoded_claims
        ) or not _TOKEN_PART_PATTERN.fullmatch(supplied_signature):
            raise ValueError("invalid signature")
        expected_signature = _signature(encoded_claims)
        if not hmac.compare_digest(supplied_signature, expected_signature):
            raise ValueError("signature mismatch")
        claims = _validate_claims(
            json.loads(_base64url_decode(encoded_claims).decode("utf-8"))
        )
    except (binascii.Error, UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise SolutionAccessError("정답 보기 권한이 올바르지 않습니다.") from exc

    now = int(_current_time())
    if claims["expires_at"] <= now:
        raise SolutionAccessError("정답 보기 권한이 만료되었습니다.")
    if claims["issued_at"] > now + 30:
        raise SolutionAccessError("정답 보기 권한이 올바르지 않습니다.")

    expected_scope = {
        "problem_id": problem_id,
        "version": version,
        "mode": mode,
        "language": language,
    }
    if any(claims[name] != expected for name, expected in expected_scope.items()):
        raise SolutionAccessError("이 제출에 대한 정답 보기 권한이 아닙니다.")
    return claims


def _read_private_problem(problem_id: str) -> dict[str, Any]:
    path: Path = PROBLEM_BANK_ROOT / "private" / f"{problem_id}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SolutionDataError("Solution data could not be loaded") from exc
    if not isinstance(value, dict) or value.get("problem_id") != problem_id:
        raise SolutionDataError("Solution data is invalid")
    return value


def get_solution_payload(
    problem_id: str,
    version: int,
    mode: str,
    language: str,
) -> dict[str, Any]:
    """Return only the solution fields intended for an explicitly unlocked view."""
    try:
        public_problem = load_public_problem(problem_id)
    except ProblemBankError as exc:
        raise SolutionDataError("Solution problem could not be loaded") from exc
    private_problem = _read_private_problem(problem_id)

    if (
        public_problem.get("version") != version
        or private_problem.get("version") != version
    ):
        raise SolutionDataError("Solution version does not match the problem")
    if mode not in public_problem.get("modes", {}) or language not in public_problem.get(
        "supported_languages", []
    ):
        raise SolutionDataError("Solution scope is not supported")

    rubric = private_problem.get("pseudocode_rubric")
    criteria = rubric.get("criteria") if isinstance(rubric, dict) else None
    reference_solutions = private_problem.get("reference_solutions")
    reference_solution = (
        reference_solutions.get(language)
        if isinstance(reference_solutions, dict)
        else None
    )
    if not isinstance(criteria, list) or not all(
        isinstance(item, dict)
        and isinstance(item.get("description"), str)
        and item["description"].strip()
        for item in criteria
    ):
        raise SolutionDataError("Solution steps are invalid")
    if not isinstance(reference_solution, str) or not reference_solution.strip():
        raise SolutionDataError("Reference solution is invalid")

    statement = public_problem.get("statement")
    if not isinstance(statement, dict) or not isinstance(statement.get("summary"), str):
        raise SolutionDataError("Solution summary is invalid")

    return {
        "problem_id": problem_id,
        "version": version,
        "mode": mode,
        "language": language,
        "title": public_problem["title"],
        "summary": statement["summary"],
        "steps": [item["description"].strip() for item in criteria],
        "reference_solution": reference_solution,
    }

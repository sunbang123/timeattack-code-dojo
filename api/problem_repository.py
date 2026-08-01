"""PostgreSQL persistence for the problem bank.

The application keeps the JSON problem bank as a development and test fallback.
When DATABASE_URL (or POSTGRES_URL) is configured, every runtime read and write
uses PostgreSQL instead.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - exercised only before dependencies install.
    psycopg = None
    dict_row = None
    Jsonb = None


class ProblemRepositoryError(RuntimeError):
    """The configured persistent problem repository is unavailable."""


_DEFAULT_READ_CACHE_SECONDS = 10.0
_problem_bank_cache_lock = threading.Lock()
_problem_bank_cache: tuple[float, dict[str, Any]] | None = None


def database_url() -> str | None:
    for name in ("DATABASE_URL", "POSTGRES_URL"):
        value = os.getenv(name, "").strip()
        if value:
            parts = urlsplit(value)
            query = [
                (key, query_value)
                for key, query_value in parse_qsl(
                    parts.query, keep_blank_values=True
                )
                if key != "supa"
            ]
            return urlunsplit(
                (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
            )
    return None


def database_enabled() -> bool:
    return database_url() is not None


def _connect():
    url = database_url()
    if url is None:
        raise ProblemRepositoryError("Database persistence is not configured")
    if psycopg is None:
        raise ProblemRepositoryError("PostgreSQL driver is not installed")
    try:
        return psycopg.connect(
            url,
            connect_timeout=8,
            prepare_threshold=None,
            row_factory=dict_row,
        )
    except psycopg.Error as exc:
        raise ProblemRepositoryError("PostgreSQL connection failed") from exc


def _read_cache_seconds() -> float:
    raw_value = os.getenv("PROBLEM_READ_CACHE_SECONDS", "").strip()
    if not raw_value:
        return _DEFAULT_READ_CACHE_SECONDS
    try:
        return max(0.0, min(float(raw_value), 60.0))
    except ValueError:
        return _DEFAULT_READ_CACHE_SECONDS


def clear_database_problem_cache() -> None:
    global _problem_bank_cache
    with _problem_bank_cache_lock:
        _problem_bank_cache = None


def claim_or_verify_problem_admin(user_id: str, email: str) -> bool:
    """Bind an allowlisted email to its first verified Supabase Auth user."""
    normalized_email = email.strip().lower()
    try:
        with _connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE dojo.problem_admins
                SET
                    user_id = coalesce(user_id, %s),
                    activated_at = coalesce(activated_at, now())
                WHERE email = %s
                  AND (user_id is null OR user_id = %s)
                RETURNING email
                """,
                (user_id, normalized_email, user_id),
            )
            row = cursor.fetchone()
    except ProblemRepositoryError:
        raise
    except psycopg.Error as exc:
        raise ProblemRepositoryError("Problem admin query failed") from exc
    return row is not None


def _query_database_problem_bank_bundle() -> dict[str, Any]:
    """Load the public problem bank with one connection and one round trip."""
    try:
        with _connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    state.bank_version,
                    problem.id,
                    problem.version,
                    problem.difficulty,
                    problem.title,
                    problem.public_data
                FROM dojo.problem_bank_state AS state
                LEFT JOIN dojo.problems AS problem ON true
                WHERE state.singleton = true
                ORDER BY problem.sort_order NULLS LAST, problem.id
                """
            )
            rows = cursor.fetchall()
    except ProblemRepositoryError:
        raise
    except psycopg.Error as exc:
        raise ProblemRepositoryError("Problem bank bundle query failed") from exc
    if not rows:
        raise ProblemRepositoryError("Problem bank state is missing")

    entries: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    public_problems: dict[str, dict[str, Any]] = {}
    for row in rows:
        problem_id = row["id"]
        if problem_id is None:
            continue
        public_problem = row["public_data"]
        if not isinstance(public_problem, dict):
            raise ProblemRepositoryError("Public problem document is invalid")
        entries.append(
            {
                "id": problem_id,
                "difficulty": row["difficulty"],
                "version": int(row["version"]),
            }
        )
        summaries.append(
            {
                "id": problem_id,
                "title": row["title"],
                "difficulty": row["difficulty"],
            }
        )
        public_problems[problem_id] = public_problem

    return {
        "manifest": {
            "schema_version": "1.0.0",
            "bank_version": int(rows[0]["bank_version"]),
            "problems": entries,
        },
        "summaries": summaries,
        "public": public_problems,
    }


def load_database_problem_bank_bundle() -> dict[str, Any]:
    global _problem_bank_cache
    now = time.monotonic()
    cache_seconds = _read_cache_seconds()
    with _problem_bank_cache_lock:
        if (
            cache_seconds > 0
            and _problem_bank_cache is not None
            and now - _problem_bank_cache[0] < cache_seconds
        ):
            return _problem_bank_cache[1]
        bundle = _query_database_problem_bank_bundle()
        if cache_seconds > 0:
            _problem_bank_cache = (time.monotonic(), bundle)
        else:
            _problem_bank_cache = None
        return bundle


def load_database_manifest() -> dict[str, Any]:
    return load_database_problem_bank_bundle()["manifest"]


def list_database_problem_summaries(
    difficulty: str | None = None,
) -> list[dict[str, Any]]:
    summaries = load_database_problem_bank_bundle()["summaries"]
    if difficulty is None:
        return list(summaries)
    return [summary for summary in summaries if summary["difficulty"] == difficulty]


def _load_problem_document(problem_id: str, column: str) -> dict[str, Any]:
    if column not in {"public_data", "private_data"}:
        raise ValueError("Unsupported problem document column")
    try:
        with _connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {column} AS document FROM dojo.problems WHERE id = %s",
                (problem_id,),
            )
            row = cursor.fetchone()
    except ProblemRepositoryError:
        raise
    except psycopg.Error as exc:
        raise ProblemRepositoryError("Problem document query failed") from exc
    if row is None or not isinstance(row["document"], dict):
        raise ProblemRepositoryError("Problem document is missing")
    return row["document"]


def load_database_public_problem(problem_id: str) -> dict[str, Any]:
    problem = load_database_problem_bank_bundle()["public"].get(problem_id)
    if not isinstance(problem, dict):
        raise ProblemRepositoryError("Public problem document is missing")
    return problem


def load_database_private_problem(problem_id: str) -> dict[str, Any]:
    return _load_problem_document(problem_id, "private_data")


ProblemDocumentsFactory = Callable[
    [str], tuple[dict[str, Any], dict[str, Any]]
]


def store_database_problem(
    id_suggestion: str,
    difficulty: str,
    documents_factory: ProblemDocumentsFactory,
) -> dict[str, Any]:
    """Insert one problem and increment the bank version atomically."""
    try:
        with _connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT bank_version
                FROM dojo.problem_bank_state
                WHERE singleton = true
                FOR UPDATE
                """
            )
            if cursor.fetchone() is None:
                raise ProblemRepositoryError("Problem bank state is missing")

            base = id_suggestion[:64].rstrip("-") or "generated-problem"
            problem_id = base
            suffix = 2
            while True:
                cursor.execute("SELECT 1 FROM dojo.problems WHERE id = %s", (problem_id,))
                if cursor.fetchone() is None:
                    break
                problem_id = f"{base[:58].rstrip('-')}-{suffix}"
                suffix += 1

            public_problem, private_problem = documents_factory(problem_id)
            cursor.execute(
                """
                INSERT INTO dojo.problems (
                    id, version, difficulty, title, public_data, private_data
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    problem_id,
                    public_problem["version"],
                    difficulty,
                    public_problem["title"],
                    Jsonb(public_problem),
                    Jsonb(private_problem),
                ),
            )
            cursor.execute(
                """
                UPDATE dojo.problem_bank_state
                SET bank_version = bank_version + 1, updated_at = now()
                WHERE singleton = true
                RETURNING bank_version
                """
            )
            state = cursor.fetchone()
    except ProblemRepositoryError:
        raise
    except psycopg.Error as exc:
        raise ProblemRepositoryError("Problem insert failed") from exc
    if state is None:
        raise ProblemRepositoryError("Problem bank version update failed")
    clear_database_problem_cache()
    return {
        "bank_version": int(state["bank_version"]),
        "problem": {
            "id": problem_id,
            "title": public_problem["title"],
            "difficulty": difficulty,
        },
    }

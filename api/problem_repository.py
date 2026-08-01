"""PostgreSQL persistence for the problem bank.

The application keeps the JSON problem bank as a development and test fallback.
When DATABASE_URL (or POSTGRES_URL) is configured, every runtime read and write
uses PostgreSQL instead.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

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


def database_url() -> str | None:
    for name in ("DATABASE_URL", "POSTGRES_URL"):
        value = os.getenv(name, "").strip()
        if value:
            return value
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


def load_database_manifest() -> dict[str, Any]:
    try:
        with _connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT bank_version FROM dojo.problem_bank_state WHERE singleton = true"
            )
            state = cursor.fetchone()
            cursor.execute(
                """
                SELECT id, difficulty, version
                FROM dojo.problems
                ORDER BY sort_order, id
                """
            )
            problems = cursor.fetchall()
    except ProblemRepositoryError:
        raise
    except psycopg.Error as exc:
        raise ProblemRepositoryError("Problem manifest query failed") from exc
    if state is None:
        raise ProblemRepositoryError("Problem bank state is missing")
    return {
        "schema_version": "1.0.0",
        "bank_version": int(state["bank_version"]),
        "problems": [dict(problem) for problem in problems],
    }


def list_database_problem_summaries(
    difficulty: str | None = None,
) -> list[dict[str, Any]]:
    try:
        with _connect() as connection, connection.cursor() as cursor:
            where_clause = "" if difficulty is None else "WHERE difficulty = %s"
            parameters = () if difficulty is None else (difficulty,)
            cursor.execute(
                f"""
                SELECT id, title, difficulty
                FROM dojo.problems
                {where_clause}
                ORDER BY sort_order, id
                """,
                parameters,
            )
            rows = cursor.fetchall()
    except ProblemRepositoryError:
        raise
    except psycopg.Error as exc:
        raise ProblemRepositoryError("Problem summary query failed") from exc
    return [dict(row) for row in rows]


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
    return _load_problem_document(problem_id, "public_data")


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
    return {
        "bank_version": int(state["bank_version"]),
        "problem": {
            "id": problem_id,
            "title": public_problem["title"],
            "difficulty": difficulty,
        },
    }

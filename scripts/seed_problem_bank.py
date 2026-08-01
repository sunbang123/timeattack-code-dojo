"""Seed the checked-in JSON problem bank into the configured PostgreSQL DB."""

from __future__ import annotations

import json
import os
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBLEM_BANK_ROOT = PROJECT_ROOT / "problem_bank"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    database_url = (
        os.getenv("DATABASE_URL", "").strip()
        or os.getenv("POSTGRES_URL", "").strip()
    )
    if not database_url:
        raise SystemExit("DATABASE_URL or POSTGRES_URL is required")

    manifest = _read_json(PROBLEM_BANK_ROOT / "manifest.json")
    with psycopg.connect(
        database_url,
        connect_timeout=8,
        prepare_threshold=None,
    ) as connection, connection.cursor() as cursor:
        for sort_order, entry in enumerate(manifest["problems"], start=1):
            problem_id = entry["id"]
            public_data = _read_json(
                PROBLEM_BANK_ROOT / "public" / f"{problem_id}.json"
            )
            private_data = _read_json(
                PROBLEM_BANK_ROOT / "private" / f"{problem_id}.json"
            )
            cursor.execute(
                """
                INSERT INTO dojo.problems (
                    id, version, difficulty, title,
                    public_data, private_data, sort_order
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    problem_id,
                    entry["version"],
                    entry["difficulty"],
                    public_data["title"],
                    Jsonb(public_data),
                    Jsonb(private_data),
                    sort_order,
                ),
            )
        cursor.execute(
            """
            UPDATE dojo.problem_bank_state
            SET bank_version = greatest(bank_version, %s), updated_at = now()
            WHERE singleton = true
            """,
            (manifest["bank_version"],),
        )
        cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('dojo.problems', 'sort_order'),
                coalesce(max(sort_order), 0) + 1,
                false
            )
            FROM dojo.problems
            """
        )

    print(f"Seeded {len(manifest['problems'])} problems (bank version {manifest['bank_version']}).")


if __name__ == "__main__":
    main()

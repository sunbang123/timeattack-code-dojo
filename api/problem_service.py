"""Read and serialize public problem-bank data for the problem API."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBLEM_BANK_ROOT = PROJECT_ROOT / "problem_bank"

DIFFICULTIES = ("easy", "medium", "hard")
MODES = ("beginner", "intermediate", "expert")
LANGUAGES = ("python", "cpp")


class ProblemBankError(RuntimeError):
    """The server-side problem bank is missing or internally inconsistent."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProblemBankError("Problem bank data could not be loaded") from exc
    if not isinstance(value, dict):
        raise ProblemBankError("Problem bank data must be a JSON object")
    return value


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    manifest = _read_json(PROBLEM_BANK_ROOT / "manifest.json")
    if manifest.get("schema_version") != "1.0.0" or not isinstance(
        manifest.get("problems"), list
    ):
        raise ProblemBankError("Problem bank manifest is invalid")
    return manifest


@lru_cache(maxsize=16)
def load_public_problem(problem_id: str) -> dict[str, Any]:
    problem = _read_json(PROBLEM_BANK_ROOT / "public" / f"{problem_id}.json")
    if problem.get("id") != problem_id:
        raise ProblemBankError("Public problem id does not match its manifest entry")
    return problem


def find_problem_entry(
    difficulty: str, problem_id: str | None = None
) -> dict[str, Any] | None:
    entries = load_manifest()["problems"]
    for entry in entries:
        if entry.get("difficulty") != difficulty:
            continue
        if problem_id is not None and entry.get("id") != problem_id:
            continue
        return entry
    return None


def serialize_problem(
    entry: dict[str, Any], mode: str, language: str
) -> dict[str, Any]:
    """Return only the fields required by one requested learning mode."""
    problem_id = entry["id"]
    public = load_public_problem(problem_id)
    if public.get("difficulty") != entry.get("difficulty") or public.get(
        "version"
    ) != entry.get("version"):
        raise ProblemBankError("Public problem metadata does not match the manifest")
    if language not in public.get("supported_languages", []):
        raise ProblemBankError("Requested language is missing from the public problem")

    modes = public.get("modes", {})
    mode_data = modes.get(mode)
    if not isinstance(mode_data, dict):
        raise ProblemBankError("Requested mode is missing from the public problem")

    payload = {
        "id": public["id"],
        "version": public["version"],
        "title": public["title"],
        "difficulty": public["difficulty"],
        "tags": public["tags"],
        "statement": public["statement"],
        "examples": public["examples"],
        "mode": mode,
        "language": language,
        "time_limit_seconds": mode_data["time_limit_seconds"],
        "answer_format": mode_data["answer_format"],
    }

    if mode == "beginner":
        payload["prompt"] = mode_data["prompt"]
    elif mode == "intermediate":
        payload["starter_code"] = mode_data["skeletons"][language]
    else:
        payload["starter_code"] = mode_data["starter_templates"][language]
    return payload


def get_problem_response(
    difficulty: str, mode: str, language: str, problem_id: str | None = None
) -> dict[str, Any] | None:
    entry = find_problem_entry(difficulty, problem_id)
    if entry is None:
        return None
    manifest = load_manifest()
    return {
        "bank_version": manifest["bank_version"],
        "problem": serialize_problem(entry, mode, language),
    }

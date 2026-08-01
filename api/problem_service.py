"""Read and serialize public problem-bank data for the problem API."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from api.problem_repository import (
    ProblemRepositoryError,
    database_enabled,
    list_database_problem_summaries,
    load_database_manifest,
    load_database_private_problem,
    load_database_public_problem,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBLEM_BANK_ROOT = PROJECT_ROOT / "problem_bank"
PROBLEM_BANK_BUNDLE_PATH = PROJECT_ROOT / "problem_bank" / "bundle.json"

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
def load_problem_bank_bundle() -> dict[str, Any]:
    bundle = _read_json(PROBLEM_BANK_BUNDLE_PATH)
    if not all(
        isinstance(bundle.get(section), dict)
        for section in ("manifest", "public", "private")
    ):
        raise ProblemBankError("Problem bank bundle is invalid")
    return bundle


@lru_cache(maxsize=1)
def _load_local_manifest() -> dict[str, Any]:
    path = PROBLEM_BANK_ROOT / "manifest.json"
    manifest = (
        _read_json(path)
        if path.is_file()
        else load_problem_bank_bundle()["manifest"]
    )
    if manifest.get("schema_version") != "1.0.0" or not isinstance(
        manifest.get("problems"), list
    ):
        raise ProblemBankError("Problem bank manifest is invalid")
    return manifest


@lru_cache(maxsize=16)
def _load_local_public_problem(problem_id: str) -> dict[str, Any]:
    path = PROBLEM_BANK_ROOT / "public" / f"{problem_id}.json"
    if path.is_file():
        problem = _read_json(path)
    else:
        problem = load_problem_bank_bundle()["public"].get(problem_id)
        if not isinstance(problem, dict):
            raise ProblemBankError(
                "Public problem is missing from the problem bank bundle"
            )
    if problem.get("id") != problem_id:
        raise ProblemBankError("Public problem id does not match its manifest entry")
    return problem


@lru_cache(maxsize=16)
def _load_local_private_problem(problem_id: str) -> dict[str, Any]:
    path = PROBLEM_BANK_ROOT / "private" / f"{problem_id}.json"
    if path.is_file():
        problem = _read_json(path)
    else:
        problem = load_problem_bank_bundle()["private"].get(problem_id)
        if not isinstance(problem, dict):
            raise ProblemBankError(
                "Private problem is missing from the problem bank bundle"
            )
    if problem.get("problem_id") != problem_id:
        raise ProblemBankError("Private problem id does not match its manifest entry")
    return problem


def load_manifest() -> dict[str, Any]:
    if not database_enabled():
        return _load_local_manifest()
    try:
        return load_database_manifest()
    except ProblemRepositoryError as exc:
        raise ProblemBankError("Persistent problem bank could not be loaded") from exc


def load_public_problem(problem_id: str) -> dict[str, Any]:
    if not database_enabled():
        return _load_local_public_problem(problem_id)
    try:
        problem = load_database_public_problem(problem_id)
    except ProblemRepositoryError as exc:
        raise ProblemBankError("Persistent public problem could not be loaded") from exc
    if problem.get("id") != problem_id:
        raise ProblemBankError("Public problem id does not match its manifest entry")
    return problem


def load_private_problem(problem_id: str) -> dict[str, Any]:
    if not database_enabled():
        return _load_local_private_problem(problem_id)
    try:
        problem = load_database_private_problem(problem_id)
    except ProblemRepositoryError as exc:
        raise ProblemBankError("Persistent private problem could not be loaded") from exc
    if problem.get("problem_id") != problem_id:
        raise ProblemBankError("Private problem id does not match its manifest entry")
    return problem


def clear_local_problem_cache() -> None:
    """Clear only JSON fallback caches; database reads intentionally stay uncached."""
    load_problem_bank_bundle.cache_clear()
    _load_local_manifest.cache_clear()
    _load_local_public_problem.cache_clear()
    _load_local_private_problem.cache_clear()


# Preserve the cache-clearing hooks used by validation code while keeping
# database reads uncached across serverless instances.
load_manifest.cache_clear = _load_local_manifest.cache_clear  # type: ignore[attr-defined]
load_public_problem.cache_clear = _load_local_public_problem.cache_clear  # type: ignore[attr-defined]
load_private_problem.cache_clear = _load_local_private_problem.cache_clear  # type: ignore[attr-defined]


def find_problem_entry(
    difficulty: str | None = None, problem_id: str | None = None
) -> dict[str, Any] | None:
    entries = load_manifest()["problems"]
    for entry in entries:
        if difficulty is not None and entry.get("difficulty") != difficulty:
            continue
        if problem_id is not None and entry.get("id") != problem_id:
            continue
        return entry
    return None


def list_problem_summaries(difficulty: str | None = None) -> list[dict[str, Any]]:
    if database_enabled():
        try:
            return list_database_problem_summaries(difficulty)
        except ProblemRepositoryError as exc:
            raise ProblemBankError(
                "Persistent problem summaries could not be loaded"
            ) from exc
    summaries = []
    for entry in load_manifest()["problems"]:
        if difficulty is not None and entry.get("difficulty") != difficulty:
            continue
        public = load_public_problem(entry["id"])
        summaries.append(
            {
                "id": public["id"],
                "title": public["title"],
                "difficulty": public["difficulty"],
            }
        )
    return summaries


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
    difficulty: str | None,
    mode: str,
    language: str,
    problem_id: str | None = None,
) -> dict[str, Any] | None:
    manifest = load_manifest()
    entry = next(
        (
            item
            for item in manifest["problems"]
            if (difficulty is None or item.get("difficulty") == difficulty)
            and (problem_id is None or item.get("id") == problem_id)
        ),
        None,
    )
    if entry is None:
        return None
    return {
        "available_problems": list_problem_summaries(difficulty),
        "bank_version": manifest["bank_version"],
        "problem": serialize_problem(entry, mode, language),
    }

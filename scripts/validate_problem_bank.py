"""Validate the Step 2 problem bank and optionally run C++ cases on Judge0."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc.step0_probe import (
    ProbeError,
    _judge0_headers,
    _request_json,
    load_env_file,
    select_judge0_language,
)


BANK = ROOT / "problem_bank"
DIFFICULTIES = {"easy", "medium", "hard"}
LANGUAGES = ["python", "cpp"]
MODES = {"beginner", "intermediate", "expert"}


class ValidationError(RuntimeError):
    """The problem bank or a reference solution is invalid."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Cannot read valid JSON from {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"Expected a JSON object in {path.relative_to(ROOT)}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_public(problem: dict[str, Any], expected: dict[str, Any]) -> None:
    problem_id = expected["id"]
    require(problem.get("schema_version") == "1.0.0", f"{problem_id}: invalid public schema_version")
    require(problem.get("id") == problem_id, f"{problem_id}: public id mismatch")
    require(problem.get("version") == expected["version"], f"{problem_id}: public version mismatch")
    require(problem.get("difficulty") == expected["difficulty"], f"{problem_id}: difficulty mismatch")
    require(problem.get("supported_languages") == LANGUAGES, f"{problem_id}: Python/C++ support required")
    require(set(problem.get("modes", {})) == MODES, f"{problem_id}: all three modes are required")
    require(len(problem.get("examples", [])) >= 2, f"{problem_id}: at least two examples are required")
    require(bool(problem.get("tags")), f"{problem_id}: at least one tag is required")
    require(bool(problem.get("title")), f"{problem_id}: title is required")
    statement = problem.get("statement", {})
    require(
        all(statement.get(key) for key in ("summary", "description", "input", "output", "constraints")),
        f"{problem_id}: incomplete statement",
    )
    modes = problem["modes"]
    require(modes["beginner"].get("answer_format") == "pseudocode", f"{problem_id}: beginner format")
    require(modes["intermediate"].get("answer_format") == "code", f"{problem_id}: intermediate format")
    require(modes["expert"].get("answer_format") == "code", f"{problem_id}: expert format")
    require(set(modes["intermediate"].get("skeletons", {})) == set(LANGUAGES), f"{problem_id}: skeleton languages")
    require(set(modes["expert"].get("starter_templates", {})) == set(LANGUAGES), f"{problem_id}: starter languages")
    for source in modes["intermediate"]["skeletons"].values():
        require("TODO" in source, f"{problem_id}: intermediate skeleton must include TODO")
    forbidden = {"hidden_tests", "reference_solutions", "pseudocode_rubric"}
    require(not (forbidden & set(problem)), f"{problem_id}: private fields leaked into public definition")


def validate_private(problem: dict[str, Any], expected: dict[str, Any]) -> None:
    problem_id = expected["id"]
    require(problem.get("schema_version") == "1.0.0", f"{problem_id}: invalid private schema_version")
    require(problem.get("problem_id") == problem_id, f"{problem_id}: private id mismatch")
    require(problem.get("version") == expected["version"], f"{problem_id}: private version mismatch")
    require(set(problem.get("reference_solutions", {})) == set(LANGUAGES), f"{problem_id}: reference languages")
    require(all(problem["reference_solutions"].values()), f"{problem_id}: empty reference solution")
    require(len(problem.get("hidden_tests", [])) >= 3, f"{problem_id}: at least three hidden tests required")
    rubric = problem.get("pseudocode_rubric", {})
    require(1 <= rubric.get("pass_score", 0) <= 100, f"{problem_id}: invalid rubric pass score")
    criteria = rubric.get("criteria", [])
    require(len(criteria) >= 3, f"{problem_id}: at least three rubric criteria required")
    require(sum(item.get("weight", 0) for item in criteria) == 100, f"{problem_id}: rubric weights must sum to 100")


def load_and_validate_bank() -> list[dict[str, Any]]:
    manifest = read_json(BANK / "manifest.json")
    entries = manifest.get("problems", [])
    require(manifest.get("schema_version") == "1.0.0", "Invalid manifest schema_version")
    bank_version = manifest.get("bank_version")
    require(isinstance(bank_version, int) and bank_version >= 4, "Invalid bank_version")
    require(len(entries) >= 12, "The problem bank must contain at least twelve problems")
    ids = [entry.get("id") for entry in entries]
    require(len(set(ids)) == len(ids), "Problem ids must be unique")
    difficulty_counts = Counter(entry.get("difficulty") for entry in entries)
    require(all(difficulty_counts[level] >= 4 for level in DIFFICULTIES), "Expected at least four problems per difficulty")

    loaded: list[dict[str, Any]] = []
    for entry in entries:
        problem_id = entry["id"]
        public = read_json(BANK / "public" / f"{problem_id}.json")
        private = read_json(BANK / "private" / f"{problem_id}.json")
        validate_public(public, entry)
        validate_private(private, entry)
        loaded.append({"manifest": entry, "public": public, "private": private})
    return loaded


def normalize_output(value: str | None) -> str:
    return "\n".join(line.rstrip() for line in (value or "").strip().splitlines())


def all_cases(item: dict[str, Any]) -> list[dict[str, str]]:
    examples = [
        {"name": f"example_{index}", "input": case["input"], "expected_output": case["output"]}
        for index, case in enumerate(item["public"]["examples"], start=1)
    ]
    return examples + item["private"]["hidden_tests"]


def run_python_reference_cases(items: list[dict[str, Any]]) -> dict[str, Any]:
    results = []
    for item in items:
        problem_id = item["manifest"]["id"]
        source = item["private"]["reference_solutions"]["python"]
        for case in all_cases(item):
            started = time.perf_counter()
            completed = subprocess.run(
                [sys.executable, "-c", source],
                input=case["input"],
                text=True,
                capture_output=True,
                timeout=3,
                cwd=ROOT,
                check=False,
            )
            accepted = completed.returncode == 0 and normalize_output(completed.stdout) == normalize_output(case["expected_output"])
            result = {
                "problem_id": problem_id,
                "case": case["name"],
                "accepted": accepted,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            }
            results.append(result)
            if not accepted:
                raise ValidationError(
                    f"Python rejected {problem_id}/{case['name']}: exit={completed.returncode}, "
                    f"stdout={completed.stdout!r}, stderr={completed.stderr!r}"
                )
    return {"runtime": sys.version.split()[0], "passed": len(results), "total": len(results), "cases": results}


def msvc_environment() -> tuple[str, dict[str, str], str] | None:
    if os.name != "nt":
        return None
    roots = [
        Path("C:/Program Files/Microsoft Visual Studio/2022"),
        Path("C:/Program Files (x86)/Microsoft Visual Studio/2022"),
    ]
    candidates = [path for root in roots if root.exists() for path in root.glob("*/VC/Auxiliary/Build/vcvars64.bat")]
    if not candidates:
        return None
    vcvars = max(candidates, key=lambda path: path.stat().st_mtime)
    initialized = subprocess.run(
        f'cmd.exe /d /c call "{vcvars}" >nul && set',
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if initialized.returncode != 0:
        raise ValidationError(f"Failed to initialize MSVC: {initialized.stderr}")
    environment = os.environ.copy()
    for line in initialized.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator:
            environment[key] = value
            if key.lower() == "path":
                environment["PATH"] = value
    compiler = shutil.which("cl.exe", path=environment.get("PATH"))
    if not compiler:
        return None
    return compiler, environment, "MSVC"


def local_cpp_compiler() -> tuple[str, dict[str, str], str]:
    for executable, name in (("g++", "G++"), ("clang++", "Clang++"), ("c++", "C++")):
        compiler = shutil.which(executable)
        if compiler:
            return compiler, os.environ.copy(), name
    msvc = msvc_environment()
    if msvc:
        return msvc
    raise ValidationError("No local C++17 compiler found; install G++, Clang++, or Visual Studio C++ tools")


def run_local_cpp_cases(items: list[dict[str, Any]]) -> dict[str, Any]:
    compiler, environment, family = local_cpp_compiler()
    version = subprocess.run(
        [compiler, "--version"] if family != "MSVC" else [compiler],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env=environment,
        timeout=10,
        check=False,
    )
    version_text = (version.stdout or version.stderr).splitlines()
    runtime = version_text[0].strip() if version_text else family
    results = []
    artifact_directory = ROOT / "artifacts"
    artifact_directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="timeattack-step2-", dir=artifact_directory) as temp_directory:
        temp = Path(temp_directory)
        for item in items:
            problem_id = item["manifest"]["id"]
            source_path = temp / f"{problem_id}.cpp"
            executable_path = temp / f"{problem_id}.exe"
            source_path.write_text(item["private"]["reference_solutions"]["cpp"], encoding="utf-8")
            if family == "MSVC":
                command = [compiler, "/nologo", "/std:c++17", "/EHsc", "/O2", str(source_path), f"/Fe:{executable_path}"]
            else:
                command = [compiler, "-std=c++17", "-O2", str(source_path), "-o", str(executable_path)]
            compiled = subprocess.run(
                command,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                env=environment,
                timeout=30,
                cwd=temp,
                check=False,
            )
            if compiled.returncode != 0:
                raise ValidationError(f"C++ compile failed for {problem_id}: {compiled.stdout}\n{compiled.stderr}")
            for case in all_cases(item):
                started = time.perf_counter()
                completed = subprocess.run(
                    [str(executable_path)],
                    input=case["input"],
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    env=environment,
                    timeout=3,
                    cwd=temp,
                    check=False,
                )
                accepted = completed.returncode == 0 and normalize_output(completed.stdout) == normalize_output(case["expected_output"])
                result = {
                    "problem_id": problem_id,
                    "case": case["name"],
                    "accepted": accepted,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                }
                results.append(result)
                if not accepted:
                    raise ValidationError(
                        f"C++ rejected {problem_id}/{case['name']}: exit={completed.returncode}, "
                        f"stdout={completed.stdout!r}, stderr={completed.stderr!r}"
                    )
    return {"provider": "local", "runtime": runtime, "passed": len(results), "total": len(results), "cases": results}


def chunks(values: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def run_judge0_cpp_cases(items: list[dict[str, Any]]) -> dict[str, Any]:
    base_url = os.getenv("JUDGE0_BASE_URL", "https://ce.judge0.com").rstrip("/")
    headers = _judge0_headers()
    languages = _request_json("GET", f"{base_url}/languages/", headers=headers)
    runtime = select_judge0_language(languages, "cpp")
    submissions = []
    metadata = []
    for item in items:
        problem_id = item["manifest"]["id"]
        source = item["private"]["reference_solutions"]["cpp"]
        for case in all_cases(item):
            submissions.append(
                {
                    "source_code": source,
                    "language_id": runtime["id"],
                    "stdin": case["input"],
                    "expected_output": case["expected_output"],
                    "cpu_time_limit": 2,
                    "wall_time_limit": 5,
                    "memory_limit": 128000,
                }
            )
            metadata.append({"problem_id": problem_id, "case": case["name"]})

    tokens: list[str] = []
    for batch in chunks(submissions, 20):
        created = _request_json(
            "POST",
            f"{base_url}/submissions/batch?base64_encoded=false",
            headers=headers,
            payload={"submissions": batch},
            timeout=30,
        )
        batch_tokens = [entry.get("token") for entry in created]
        if not all(batch_tokens):
            raise ProbeError(f"Judge0 batch creation failed: {created}")
        tokens.extend(batch_tokens)

    deadline = time.monotonic() + 90
    pending = set(tokens)
    results_by_token: dict[str, dict[str, Any]] = {}
    fields = "token,stdout,stderr,compile_output,message,time,memory,status"
    while pending and time.monotonic() < deadline:
        for token_batch in chunks([{"token": token} for token in pending], 20):
            token_csv = ",".join(entry["token"] for entry in token_batch)
            response = _request_json(
                "GET",
                f"{base_url}/submissions/batch?tokens={token_csv}&base64_encoded=false&fields={fields}",
                headers=headers,
                timeout=20,
            )
            for result in response.get("submissions", []):
                token = result.get("token")
                if token and result.get("status", {}).get("id") not in (1, 2):
                    results_by_token[token] = result
                    pending.discard(token)
        if pending:
            time.sleep(0.5)
    if pending:
        raise ProbeError(f"Judge0 did not finish {len(pending)} C++ cases within 90 seconds")

    case_results = []
    for token, meta in zip(tokens, metadata, strict=True):
        raw = results_by_token[token]
        accepted = raw.get("status", {}).get("id") == 3
        result = {
            **meta,
            "accepted": accepted,
            "status": raw.get("status", {}).get("description"),
            "provider_time_seconds": raw.get("time"),
            "provider_memory_kb": raw.get("memory"),
        }
        case_results.append(result)
        if not accepted:
            raise ValidationError(
                f"C++ rejected {meta['problem_id']}/{meta['case']}: "
                f"status={result['status']}, compile_output={raw.get('compile_output')!r}, stderr={raw.get('stderr')!r}"
            )
    return {
        "provider": "judge0",
        "base_url": base_url,
        "runtime": runtime["name"],
        "passed": len(case_results),
        "total": len(case_results),
        "cases": case_results,
    }


def bank_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(BANK.rglob("*.json")):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpp-local", action="store_true", help="Compile once per problem and run every C++ case locally")
    parser.add_argument("--judge0", action="store_true", help="Run every C++ example and hidden test on Judge0")
    parser.add_argument("--output", type=Path, help="Write a JSON evidence artifact")
    args = parser.parse_args()

    try:
        items = load_and_validate_bank()
        python_result = run_python_reference_cases(items)
        summary: dict[str, Any] = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "bank_version": read_json(BANK / "manifest.json")["bank_version"],
            "bank_sha256": bank_digest(),
            "problem_count": len(items),
            "difficulty_counts": dict(Counter(item["manifest"]["difficulty"] for item in items)),
            "modes": sorted(MODES),
            "languages": LANGUAGES,
            "python": python_result,
        }
        if args.cpp_local:
            summary["cpp"] = run_local_cpp_cases(items)
        if args.judge0:
            require(not args.cpp_local, "Choose only one C++ validation provider")
            load_env_file(ROOT / ".env")
            summary["cpp"] = run_judge0_cpp_cases(items)
        if args.output:
            output = args.output if args.output.is_absolute() else ROOT / args.output
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            f"Problem bank valid: {len(items)} problems, "
            f"Python {python_result['passed']}/{python_result['total']} passed"
            + (f", C++ {summary['cpp']['passed']}/{summary['cpp']['total']} passed" if "cpp" in summary else "")
        )
        return 0
    except (ValidationError, ProbeError, subprocess.TimeoutExpired) as exc:
        print(f"Problem bank validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Live provider probes for Step 0 of the Time Attack Code Dojo MVP.

This module intentionally uses only the Python standard library so the probe
can run before the application dependencies are selected.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 20


class ProbeError(RuntimeError):
    """A provider probe failed in an actionable way."""


def load_env_file(path: Path = Path(".env")) -> None:
    """Load simple KEY=VALUE entries without adding a dependency.

    Existing process environment variables win over values from the file.
    """
    if not path.exists():
        return
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ProbeError(f"Invalid .env entry on line {line_number}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'\"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "timeattack-code-dojo-step0/0.1",
        **(headers or {}),
    }
    if body is not None:
        request_headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=request_headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")[:800]
        raise ProbeError(f"HTTP {exc.code} from {url}: {raw}") from exc
    except (URLError, TimeoutError) as exc:
        raise ProbeError(f"Network error from {url}: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProbeError(f"Non-JSON response from {url}: {raw[:800]}") from exc


def _version_tuple(name: str) -> tuple[int, ...]:
    matches = re.findall(r"\d+(?:\.\d+)+", name)
    if not matches:
        return (0,)
    return tuple(int(part) for part in matches[-1].split("."))


def select_judge0_language(languages: list[dict[str, Any]], language: str) -> dict[str, Any]:
    if language == "python":
        candidates = [item for item in languages if "python (3" in item.get("name", "").lower()]
    elif language == "cpp":
        candidates = [item for item in languages if "c++ (gcc" in item.get("name", "").lower()]
    else:
        raise ValueError(f"Unsupported language: {language}")

    if not candidates:
        raise ProbeError(f"Judge0 did not report a usable {language} runtime")
    return max(candidates, key=lambda item: (_version_tuple(item.get("name", "")), item.get("id", 0)))


def _judge0_headers() -> dict[str, str]:
    token = os.getenv("JUDGE0_AUTH_TOKEN", "").strip()
    return {"X-Auth-Token": token} if token else {}


def _poll_judge0(base_url: str, token: str, headers: dict[str, str]) -> dict[str, Any]:
    deadline = time.monotonic() + DEFAULT_TIMEOUT_SECONDS
    fields = "stdout,stderr,compile_output,message,time,memory,status"
    while time.monotonic() < deadline:
        result = _request_json(
            "GET",
            f"{base_url}/submissions/{token}?base64_encoded=false&fields={fields}",
            headers=headers,
            timeout=10,
        )
        status_id = result.get("status", {}).get("id")
        if status_id not in (1, 2):
            return result
        time.sleep(0.35)
    raise ProbeError("Judge0 submission did not finish within the probe deadline")


def probe_judge0(repetitions: int) -> dict[str, Any]:
    base_url = os.getenv("JUDGE0_BASE_URL", "https://ce.judge0.com").rstrip("/")
    headers = _judge0_headers()
    languages = _request_json("GET", f"{base_url}/languages/", headers=headers)
    selected = {
        "python": select_judge0_language(languages, "python"),
        "cpp": select_judge0_language(languages, "cpp"),
    }
    samples = {
        "python": "a, b = map(int, input().split())\nprint(a + b)\n",
        "cpp": (
            "#include <iostream>\n"
            "int main() { long long a, b; std::cin >> a >> b; std::cout << a + b << '\\n'; }\n"
        ),
    }

    runs: list[dict[str, Any]] = []
    for language, runtime in selected.items():
        for attempt in range(1, repetitions + 1):
            started = time.perf_counter()
            created = _request_json(
                "POST",
                f"{base_url}/submissions/?base64_encoded=false&wait=false",
                headers=headers,
                payload={
                    "source_code": samples[language],
                    "language_id": runtime["id"],
                    "stdin": "20 22\n",
                    "expected_output": "42\n",
                    "cpu_time_limit": 2,
                    "wall_time_limit": 5,
                    "memory_limit": 128000,
                },
            )
            token = created.get("token")
            if not token:
                raise ProbeError(f"Judge0 did not return a submission token: {created}")
            result = _poll_judge0(base_url, token, headers)
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            accepted = result.get("status", {}).get("id") == 3 and result.get("stdout", "").strip() == "42"
            runs.append(
                {
                    "language": language,
                    "attempt": attempt,
                    "accepted": accepted,
                    "latency_ms": elapsed_ms,
                    "provider_time_seconds": result.get("time"),
                    "provider_memory_kb": result.get("memory"),
                    "status": result.get("status", {}).get("description"),
                    "stdout": result.get("stdout"),
                }
            )
            if not accepted:
                raise ProbeError(f"Judge0 rejected the {language} sample: {result}")

    return {
        "provider": "judge0",
        "status": "passed",
        "base_url": base_url,
        "authenticated": bool(headers),
        "runtimes": {key: value["name"] for key, value in selected.items()},
        "runs": runs,
    }


def _piston_headers() -> dict[str, str]:
    token = os.getenv("PISTON_TOKEN", "").strip()
    if not token:
        return {}
    name = os.getenv("PISTON_AUTH_HEADER", "Authorization").strip()
    scheme = os.getenv("PISTON_AUTH_SCHEME", "Bearer").strip()
    value = f"{scheme} {token}".strip()
    return {name: value}


def _select_piston_runtime(runtimes: list[dict[str, Any]], language: str) -> dict[str, Any]:
    names = {"python": {"python", "python3", "py"}, "cpp": {"c++", "cpp", "gcc"}}[language]
    candidates = []
    for item in runtimes:
        identifiers = {str(item.get("language", "")).lower()}
        identifiers.update(str(alias).lower() for alias in item.get("aliases", []))
        if identifiers & names:
            candidates.append(item)
    if not candidates:
        raise ProbeError(f"Piston did not report a usable {language} runtime")
    return max(candidates, key=lambda item: _version_tuple(str(item.get("version", ""))))


def probe_piston(repetitions: int) -> dict[str, Any]:
    base_url = os.getenv("PISTON_BASE_URL", "https://emkc.org/api/v2/piston").rstrip("/")
    headers = _piston_headers()
    if base_url == "https://emkc.org/api/v2/piston" and not headers:
        return {
            "provider": "piston",
            "status": "skipped",
            "reason": "The public Piston API requires an authorization token as of 2026-02-15.",
        }

    runtimes = _request_json("GET", f"{base_url}/runtimes", headers=headers)
    selected = {
        "python": _select_piston_runtime(runtimes, "python"),
        "cpp": _select_piston_runtime(runtimes, "cpp"),
    }
    samples = {
        "python": ("main.py", "a, b = map(int, input().split())\nprint(a + b)\n"),
        "cpp": (
            "main.cpp",
            "#include <iostream>\nint main(){ long long a,b; std::cin>>a>>b; std::cout<<a+b<<'\\n'; }\n",
        ),
    }
    runs: list[dict[str, Any]] = []
    for language, runtime in selected.items():
        for attempt in range(1, repetitions + 1):
            filename, source = samples[language]
            started = time.perf_counter()
            result = _request_json(
                "POST",
                f"{base_url}/execute",
                headers=headers,
                payload={
                    "language": runtime["language"],
                    "version": runtime["version"],
                    "files": [{"name": filename, "content": source}],
                    "stdin": "20 22\n",
                    "compile_timeout": 10000,
                    "run_timeout": 5000,
                    "compile_memory_limit": 128000000,
                    "run_memory_limit": 128000000,
                },
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000)
            run = result.get("run", {})
            accepted = run.get("code") == 0 and str(run.get("stdout", "")).strip() == "42"
            runs.append(
                {
                    "language": language,
                    "attempt": attempt,
                    "accepted": accepted,
                    "latency_ms": elapsed_ms,
                    "exit_code": run.get("code"),
                    "signal": run.get("signal"),
                }
            )
            if not accepted:
                raise ProbeError(f"Piston rejected the {language} sample: {result}")

    return {
        "provider": "piston",
        "status": "passed",
        "base_url": base_url,
        "authenticated": bool(headers),
        "runtimes": {key: value["version"] for key, value in selected.items()},
        "runs": runs,
    }


def validate_pseudocode_evaluation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProbeError("Hugging Face response content is not a JSON object")
    required = {"passed", "score", "feedback", "missing_steps"}
    if set(value) != required:
        raise ProbeError(f"Unexpected Hugging Face response keys: {sorted(value)}")
    if not isinstance(value["passed"], bool):
        raise ProbeError("'passed' must be a boolean")
    if not isinstance(value["score"], int) or isinstance(value["score"], bool) or not 0 <= value["score"] <= 100:
        raise ProbeError("'score' must be an integer from 0 through 100")
    if not isinstance(value["feedback"], str) or not value["feedback"].strip():
        raise ProbeError("'feedback' must be a non-empty string")
    if not isinstance(value["missing_steps"], list) or not all(
        isinstance(item, str) for item in value["missing_steps"]
    ):
        raise ProbeError("'missing_steps' must be an array of strings")
    return value


def probe_huggingface(repetitions: int) -> dict[str, Any]:
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        return {
            "provider": "huggingface",
            "status": "skipped",
            "reason": "HF_TOKEN with Inference Providers permission is not configured.",
        }

    base_url = os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1").rstrip("/")
    model = os.getenv("HF_MODEL", "openai/gpt-oss-120b:groq")
    schema = {
        "name": "pseudocode_evaluation",
        "description": "Evaluation of a novice learner's pseudocode.",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "passed": {"type": "boolean"},
                "score": {"type": "integer", "minimum": 0, "maximum": 100},
                "feedback": {"type": "string"},
                "missing_steps": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["passed", "score", "feedback", "missing_steps"],
        },
    }
    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict but helpful programming tutor. Evaluate whether the pseudocode "
                "solves the stated problem. Focus on input, loop bounds, condition, update, and output."
            ),
        },
        {
            "role": "user",
            "content": (
                "Problem: Read N integers and print their sum.\n"
                "Pseudocode: Read N. Set total to 0. Repeat N times: read x and add x to total. "
                "After the loop, print total."
            ),
        },
    ]

    runs: list[dict[str, Any]] = []
    for attempt in range(1, repetitions + 1):
        started = time.perf_counter()
        result = _request_json(
            "POST",
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {token}"},
            payload={
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_schema", "json_schema": schema},
                "temperature": 0,
                "max_tokens": 300,
            },
            timeout=30,
        )
        try:
            content = result["choices"][0]["message"]["content"]
            parsed = json.loads(content) if isinstance(content, str) else content
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ProbeError(f"Unexpected Hugging Face response: {result}") from exc
        validated = validate_pseudocode_evaluation(parsed)
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        runs.append(
            {
                "attempt": attempt,
                "schema_valid": True,
                "passed": validated["passed"],
                "score": validated["score"],
                "latency_ms": elapsed_ms,
                "evaluation": validated,
            }
        )

    return {
        "provider": "huggingface",
        "status": "passed",
        "base_url": base_url,
        "model": model,
        "runs": runs,
    }


def run_probe(name: str, repetitions: int) -> dict[str, Any]:
    probe = {
        "judge0": probe_judge0,
        "piston": probe_piston,
        "huggingface": probe_huggingface,
    }[name]
    started = time.perf_counter()
    try:
        result = probe(repetitions)
    except ProbeError as exc:
        result = {"provider": name, "status": "failed", "error": str(exc)}
    result["probe_elapsed_ms"] = round((time.perf_counter() - started) * 1000)
    return result


def main() -> int:
    load_env_file()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--providers",
        nargs="+",
        choices=("judge0", "piston", "huggingface"),
        default=("judge0", "piston", "huggingface"),
    )
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("artifacts/step0-results.json"))
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "repetitions": args.repetitions,
        "results": [run_probe(name, args.repetitions) for name in args.providers],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if any(item["status"] == "failed" for item in summary["results"]) else 0


if __name__ == "__main__":
    sys.exit(main())

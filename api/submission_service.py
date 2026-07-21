"""Grade pseudocode and source-code submissions without exposing private tests."""

from __future__ import annotations

import json
import os
import re
import time
from functools import lru_cache
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from api.problem_service import PROBLEM_BANK_ROOT, ProblemBankError, load_public_problem


PROVIDER_TIMEOUT_SECONDS = 15
POLL_INTERVAL_SECONDS = 0.35


class SubmissionError(RuntimeError):
    """A submission cannot be graded safely."""


class ProviderError(RuntimeError):
    """An external grading provider is unavailable or returned invalid data."""


def _read_private_problem(problem_id: str) -> dict[str, Any]:
    path = PROBLEM_BANK_ROOT / "private" / f"{problem_id}.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SubmissionError("채점 데이터를 불러오지 못했습니다.") from exc
    if not isinstance(value, dict) or value.get("problem_id") != problem_id:
        raise SubmissionError("채점 데이터가 올바르지 않습니다.")
    return value


def _request_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = PROVIDER_TIMEOUT_SECONDS,
) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "timeattack-code-dojo/0.1",
        **(headers or {}),
    }
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    provider_request = Request(url, data=body, headers=request_headers, method=method)
    try:
        with urlopen(provider_request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raise ProviderError(f"채점 서비스가 HTTP {exc.code} 오류를 반환했습니다.") from exc
    except (URLError, TimeoutError) as exc:
        raise ProviderError("채점 서비스에 연결하지 못했습니다.") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProviderError("채점 서비스 응답을 해석하지 못했습니다.") from exc


def _judge0_headers() -> dict[str, str]:
    token = os.getenv("JUDGE0_AUTH_TOKEN", "").strip()
    return {"X-Auth-Token": token} if token else {}


def _version_tuple(name: str) -> tuple[int, ...]:
    matches = re.findall(r"\d+(?:\.\d+)+", name)
    return tuple(int(part) for part in matches[-1].split(".")) if matches else (0,)


@lru_cache(maxsize=2)
def _judge0_language_id(language: str) -> int:
    base_url = os.getenv("JUDGE0_BASE_URL", "https://ce.judge0.com").rstrip("/")
    runtimes = _request_json("GET", f"{base_url}/languages/", headers=_judge0_headers())
    if not isinstance(runtimes, list):
        raise ProviderError("채점 서비스의 언어 목록이 올바르지 않습니다.")
    marker = "python (3" if language == "python" else "c++ (gcc"
    candidates = [
        runtime
        for runtime in runtimes
        if marker in str(runtime.get("name", "")).lower()
        and isinstance(runtime.get("id"), int)
    ]
    if not candidates:
        raise ProviderError("요청한 언어의 실행 환경을 찾지 못했습니다.")
    selected = max(
        candidates,
        key=lambda runtime: (_version_tuple(str(runtime.get("name", ""))), runtime["id"]),
    )
    return selected["id"]


def _normalized_output(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "\n".join(line.rstrip() for line in value.strip().splitlines())


def _safe_detail(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()[:1200]


def _grade_code(language: str, answer: str, tests: list[dict[str, str]]) -> dict[str, Any]:
    base_url = os.getenv("JUDGE0_BASE_URL", "https://ce.judge0.com").rstrip("/")
    headers = _judge0_headers()
    submissions = [
        {
            "source_code": answer,
            "language_id": _judge0_language_id(language),
            "stdin": test["input"],
            "cpu_time_limit": 3,
            "wall_time_limit": 6,
            "memory_limit": 256000,
        }
        for test in tests
    ]
    created = _request_json(
        "POST",
        f"{base_url}/submissions/batch?base64_encoded=false",
        headers=headers,
        payload={"submissions": submissions},
    )
    if not isinstance(created, list) or len(created) != len(tests):
        raise ProviderError("채점 서비스가 실행 토큰을 반환하지 않았습니다.")
    tokens = [item.get("token") for item in created if isinstance(item, dict)]
    if len(tokens) != len(tests) or not all(isinstance(token, str) for token in tokens):
        raise ProviderError("채점 서비스가 실행 토큰을 반환하지 않았습니다.")

    fields = "stdout,stderr,compile_output,message,status"
    deadline = time.monotonic() + PROVIDER_TIMEOUT_SECONDS
    results: list[dict[str, Any]] | None = None
    while time.monotonic() < deadline:
        query = urlencode(
            {
                "tokens": ",".join(tokens),
                "base64_encoded": "false",
                "fields": fields,
            }
        )
        polled = _request_json(
            "GET",
            f"{base_url}/submissions/batch?{query}",
            headers=headers,
            timeout=10,
        )
        current = polled.get("submissions") if isinstance(polled, dict) else None
        if not isinstance(current, list) or len(current) != len(tests):
            raise ProviderError("채점 서비스의 실행 결과가 올바르지 않습니다.")
        if all(item.get("status", {}).get("id") not in (1, 2) for item in current):
            results = current
            break
        time.sleep(POLL_INTERVAL_SECONDS)
    if results is None:
        raise ProviderError("제한 시간 안에 채점이 끝나지 않았습니다.")

    first_failure: dict[str, Any] | None = None
    passed_tests = 0
    for test, result in zip(tests, results, strict=True):
        status_id = result.get("status", {}).get("id")
        if status_id == 3 and _normalized_output(result.get("stdout")) == _normalized_output(
            test["expected_output"]
        ):
            passed_tests += 1
        elif first_failure is None:
            first_failure = result

    total_tests = len(tests)
    if passed_tests == total_tests:
        return {
            "kind": "code",
            "status": "accepted",
            "passed": True,
            "score": 100,
            "feedback": "모든 공개·비공개 테스트를 통과했습니다.",
            "passed_tests": passed_tests,
            "total_tests": total_tests,
        }

    assert first_failure is not None
    status_id = first_failure.get("status", {}).get("id")
    if status_id == 6:
        status = "compile_error"
        feedback = "컴파일 오류가 발생했습니다. 오류 내용을 확인해 주세요."
        detail = _safe_detail(first_failure.get("compile_output"))
    elif status_id != 3:
        status = "runtime_error"
        feedback = "실행 중 오류가 발생했습니다. 입력 범위와 예외 처리를 확인해 주세요."
        detail = _safe_detail(first_failure.get("stderr") or first_failure.get("message"))
    else:
        status = "wrong_answer"
        feedback = "일부 테스트를 통과하지 못했습니다. 경계값과 알고리즘 복잡도를 점검해 보세요."
        detail = None
    response: dict[str, Any] = {
        "kind": "code",
        "status": status,
        "passed": False,
        "score": round(passed_tests * 100 / total_tests),
        "feedback": feedback,
        "passed_tests": passed_tests,
        "total_tests": total_tests,
    }
    if detail:
        response["detail"] = detail
    return response


def _grade_pseudocode(
    answer: str,
    public_problem: dict[str, Any],
    private_problem: dict[str, Any],
) -> dict[str, Any]:
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise ProviderError("의사코드 채점에는 로컬 환경의 HF_TOKEN 설정이 필요합니다.")
    base_url = os.getenv("HF_BASE_URL", "https://router.huggingface.co/v1").rstrip("/")
    model = os.getenv("HF_MODEL", "openai/gpt-oss-120b:groq")
    rubric = private_problem["pseudocode_rubric"]
    schema = {
        "name": "pseudocode_evaluation",
        "description": "문제별 루브릭에 따른 의사코드 평가",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "answer_derivable": {
                    "type": "boolean",
                    "description": "제출한 절차에서 요구 결과를 산출하는 흐름을 따라갈 수 있는지 여부",
                },
                "has_logical_error": {
                    "type": "boolean",
                    "description": "실제로 잘못된 결과를 만드는 핵심 논리 오류가 있는지 여부",
                },
                "score": {"type": "integer", "minimum": 0, "maximum": 100},
                "feedback": {"type": "string"},
                "missing_steps": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "answer_derivable",
                "has_logical_error",
                "score",
                "feedback",
                "missing_steps",
            ],
        },
    }
    messages = [
        {
            "role": "system",
            "content": (
                "당신은 초보 학습자의 의사코드를 관대하게 평가하는 알고리즘 튜터입니다. "
                "최종 통과 여부는 서버가 계산하므로 다음 두 사실을 서로 독립적으로 판단하세요.\n"
                "- answer_derivable: 제출한 절차와 의도에서 문제의 요구 결과를 어떻게 산출하는지 "
                "충분히 따라갈 수 있으면 true입니다. 계산의 옳고 그름은 이 필드가 아니라 "
                "has_logical_error로 판단하세요.\n"
                "- has_logical_error: 답안의 조건, 계산, 갱신 또는 추론에 실제로 잘못된 결과를 "
                "만드는 핵심 논리 오류가 있으면 true입니다. 단순한 설명 생략은 논리 오류가 아닙니다.\n"
                "판정 정책:\n"
                "- 자연어, 자유로운 형식, 부정확한 용어, 거친 기호와 코드 문법 오류를 허용하세요.\n"
                "- 의도가 분명하면 입출력 문구, 초기화, 경계 처리 등 구현 세부 단계 생략을 허용하세요.\n"
                "- 평가 기준의 모범 알고리즘과 다른 대안 풀이도 올바르면 인정하세요.\n"
                "- 시간·공간 비효율만으로는 오답 처리하거나 논리 오류로 판단하지 마세요.\n"
                "- 평가 기준은 점수와 개선 피드백을 위한 참고 자료일 뿐, 항목 누락 자체를 통과 "
                "실패 사유로 삼지 마세요.\n"
                "- answer_derivable=false는 내용이 너무 없거나 모호하여 요구 결과를 산출하는 "
                "흐름을 판단할 수 없을 때만, "
                "has_logical_error=true는 핵심 논리가 실제로 틀렸을 때만 사용하세요.\n"
                "score와 missing_steps는 학습용 피드백이며 위 두 사실을 바꾸지 않습니다. "
                "답변은 한국어로 짧고 구체적으로 작성하세요."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "problem": public_problem["statement"],
                    "rubric": rubric,
                    "pseudocode": answer,
                },
                ensure_ascii=False,
            ),
        },
    ]
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
    )
    try:
        content = result["choices"][0]["message"]["content"]
        evaluation = json.loads(content) if isinstance(content, str) else content
        if not isinstance(evaluation, dict) or set(evaluation) != {
            "answer_derivable",
            "has_logical_error",
            "score",
            "feedback",
            "missing_steps",
        }:
            raise ValueError
        if not isinstance(evaluation["answer_derivable"], bool):
            raise ValueError
        if not isinstance(evaluation["has_logical_error"], bool):
            raise ValueError
        if (
            not isinstance(evaluation["score"], int)
            or isinstance(evaluation["score"], bool)
            or not 0 <= evaluation["score"] <= 100
        ):
            raise ValueError
        if not isinstance(evaluation["feedback"], str) or not evaluation["feedback"].strip():
            raise ValueError
        if not isinstance(evaluation["missing_steps"], list) or not all(
            isinstance(item, str) for item in evaluation["missing_steps"]
        ):
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ProviderError("의사코드 채점 결과를 해석하지 못했습니다.") from exc
    passed = evaluation["answer_derivable"] and not evaluation["has_logical_error"]
    return {
        "kind": "pseudocode",
        "status": "evaluated",
        "passed": passed,
        "score": evaluation["score"],
        "feedback": evaluation["feedback"],
        "missing_steps": evaluation["missing_steps"],
    }


def grade_submission(
    problem_id: str,
    version: int,
    mode: str,
    language: str,
    answer: str,
) -> dict[str, Any]:
    try:
        public_problem = load_public_problem(problem_id)
    except ProblemBankError as exc:
        raise SubmissionError("요청한 문제를 찾을 수 없습니다.") from exc
    private_problem = _read_private_problem(problem_id)
    if public_problem.get("version") != version or private_problem.get("version") != version:
        raise SubmissionError("문제 버전이 변경되었습니다. 새로고침 후 다시 제출해 주세요.")
    if mode not in public_problem.get("modes", {}):
        raise SubmissionError("지원하지 않는 학습 모드입니다.")
    if language not in public_problem.get("supported_languages", []):
        raise SubmissionError("지원하지 않는 언어입니다.")
    if mode == "beginner":
        if len(answer) > 8_000:
            raise SubmissionError("의사코드 답안은 8,000자 이하여야 합니다.")
        return _grade_pseudocode(answer, public_problem, private_problem)

    tests = [
        {"input": example["input"], "expected_output": example["output"]}
        for example in public_problem["examples"]
    ]
    tests.extend(private_problem["hidden_tests"])
    return _grade_code(language, answer, tests)

from __future__ import annotations

import os
import re
import uuid
from typing import Any

from flask import Flask, Response, abort, jsonify, request
from werkzeug.exceptions import HTTPException

from api.problem_service import (
    DIFFICULTIES,
    LANGUAGES,
    MODES,
    get_problem_response,
)
from api.solution_service import (
    SolutionAccessError,
    get_solution_payload,
    issue_solution_access_token,
    verify_solution_access_token,
)
from api.submission_service import ProviderError, SubmissionError, grade_submission


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


@app.after_request
def add_response_headers(response: Response) -> Response:
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Request-ID"] = request.environ["request_id"]
    return response


@app.before_request
def assign_request_id() -> None:
    request.environ["request_id"] = request.headers.get(
        "X-Request-ID", str(uuid.uuid4())
    )


@app.get("/")
@app.get("/api")
def index() -> tuple[Response, int]:
    return jsonify(service="timeattack-api", status="ok"), 200


@app.get("/health")
@app.get("/api/health")
def health() -> tuple[Response, int]:
    return (
        jsonify(
            environment=os.getenv("APP_ENV", "development"),
            runtime="python",
            service="timeattack-api",
            status="ok",
            version="0.1.0",
        ),
        200,
    )


def required_query_value(name: str, allowed: tuple[str, ...]) -> str:
    values = request.args.getlist(name)
    if not values or not values[0]:
        abort(400, description=f"Missing required query parameter: {name}")
    if len(values) != 1:
        abort(400, description=f"Query parameter must appear once: {name}")
    value = values[0]
    if value not in allowed:
        choices = ", ".join(allowed)
        abort(400, description=f"Invalid {name}; expected one of: {choices}")
    return value


@app.get("/problem")
@app.get("/api/problem")
def problem() -> tuple[Response, int]:
    allowed_parameters = {"difficulty", "mode", "language", "problem_id"}
    unknown_parameters = sorted(set(request.args) - allowed_parameters)
    if unknown_parameters:
        abort(
            400,
            description=f"Unknown query parameter: {unknown_parameters[0]}",
        )

    difficulty_values = request.args.getlist("difficulty")
    difficulty = (
        required_query_value("difficulty", DIFFICULTIES)
        if difficulty_values
        else None
    )
    mode = required_query_value("mode", MODES)
    language = required_query_value("language", LANGUAGES)
    problem_ids = request.args.getlist("problem_id")
    if len(problem_ids) > 1:
        abort(400, description="Query parameter must appear once: problem_id")
    problem_id = problem_ids[0].strip() if problem_ids else None
    if problem_id == "":
        abort(400, description="problem_id must not be empty")

    payload = get_problem_response(difficulty, mode, language, problem_id)
    if payload is None:
        abort(404, description="Problem not found for the requested selection")
    return jsonify(payload), 200


@app.post("/submit")
@app.post("/api/submit")
def submit() -> tuple[Response, int]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400, description="Request body must be a JSON object")
    allowed_fields = {"problem_id", "version", "mode", "language", "answer"}
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        abort(400, description=f"Unknown request field: {unknown_fields[0]}")
    if set(payload) != allowed_fields:
        missing = sorted(allowed_fields - set(payload))
        abort(400, description=f"Missing request field: {missing[0]}")
    if not isinstance(payload["problem_id"], str) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", payload["problem_id"]
    ):
        abort(400, description="problem_id is invalid")
    if (
        not isinstance(payload["version"], int)
        or isinstance(payload["version"], bool)
        or payload["version"] < 1
    ):
        abort(400, description="version must be a positive integer")
    if payload["mode"] not in MODES:
        abort(400, description="Invalid mode")
    if payload["language"] not in LANGUAGES:
        abort(400, description="Invalid language")
    if not isinstance(payload["answer"], str) or not payload["answer"].strip():
        abort(400, description="answer must be a non-empty string")
    try:
        result = grade_submission(
            payload["problem_id"],
            payload["version"],
            payload["mode"],
            payload["language"],
            payload["answer"],
        )
    except SubmissionError as error:
        abort(400, description=str(error))
    except ProviderError as error:
        abort(502, description=str(error))
    if result.get("passed") is False:
        result = {
            **result,
            "solution_access_token": issue_solution_access_token(
                payload["problem_id"],
                payload["version"],
                payload["mode"],
                payload["language"],
            ),
        }
    return jsonify({"result": result}), 200


@app.post("/solution")
@app.post("/api/solution")
def solution() -> tuple[Response, int]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        abort(400, description="Request body must be a JSON object")
    allowed_fields = {
        "problem_id",
        "version",
        "mode",
        "language",
        "solution_access_token",
    }
    unknown_fields = sorted(set(payload) - allowed_fields)
    if unknown_fields:
        abort(400, description=f"Unknown request field: {unknown_fields[0]}")
    if set(payload) != allowed_fields:
        missing = sorted(allowed_fields - set(payload))
        abort(400, description=f"Missing request field: {missing[0]}")
    if not isinstance(payload["problem_id"], str) or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", payload["problem_id"]
    ):
        abort(400, description="problem_id is invalid")
    if (
        not isinstance(payload["version"], int)
        or isinstance(payload["version"], bool)
        or payload["version"] < 1
    ):
        abort(400, description="version must be a positive integer")
    if payload["mode"] not in MODES:
        abort(400, description="Invalid mode")
    if payload["language"] not in LANGUAGES:
        abort(400, description="Invalid language")
    token = payload["solution_access_token"]
    if not isinstance(token, str) or not token.strip():
        abort(400, description="solution_access_token must be a non-empty string")

    try:
        verify_solution_access_token(
            token,
            problem_id=payload["problem_id"],
            version=payload["version"],
            mode=payload["mode"],
            language=payload["language"],
        )
    except SolutionAccessError as error:
        abort(403, description=str(error))

    solution_payload = get_solution_payload(
        payload["problem_id"],
        payload["version"],
        payload["mode"],
        payload["language"],
    )
    return jsonify({"solution": solution_payload}), 200


@app.errorhandler(Exception)
def handle_error(error: Exception) -> tuple[Response, int]:
    status_code = error.code if isinstance(error, HTTPException) else 500
    message = error.description if isinstance(error, HTTPException) else "Internal server error"
    payload: dict[str, Any] = {
        "error": {
            "code": status_code,
            "message": message,
            "request_id": request.environ.get("request_id"),
        }
    }
    return jsonify(payload), status_code


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("API_PORT", "5328")),
        debug=os.getenv("APP_ENV", "development") == "development",
    )

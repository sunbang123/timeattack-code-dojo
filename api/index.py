from __future__ import annotations

import os
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

    difficulty = required_query_value("difficulty", DIFFICULTIES)
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
        abort(404, description="Problem not found for the requested difficulty")
    return jsonify(payload), 200


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

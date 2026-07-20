from __future__ import annotations

import os
import uuid
from typing import Any

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException


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


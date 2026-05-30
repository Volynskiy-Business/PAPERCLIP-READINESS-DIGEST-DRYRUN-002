from __future__ import annotations

import json
import os
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from backend.internal_operator_auth import verify_internal_operator_jwt
from backend.readiness_digest import DigestSourceError, build_digest


class ReadinessDigestHandler(BaseHTTPRequestHandler):
    server_version = "ReadinessDigestHTTP/0.1"

    def do_GET(self) -> None:
        if self.path != "/api/v1/ops/readiness-digest":
            self._write_json(
                HTTPStatus.NOT_FOUND,
                {"error": {"code": "not_found", "message": "Route not found.", "requestId": self._request_id()}},
            )
            return

        if not self._authorized():
            self._write_json(
                HTTPStatus.UNAUTHORIZED,
                {
                    "error": {
                        "code": "unauthorized",
                        "message": "Authentication is required.",
                        "requestId": self._request_id(),
                    }
                },
            )
            return

        request_id = self._request_id()
        try:
            body = build_digest(request_id=request_id)
        except DigestSourceError as exc:
            self._write_json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {
                    "error": {
                        "code": exc.code.lower(),
                        "message": exc.message,
                        "requestId": request_id,
                    }
                },
            )
            return

        self._write_json(HTTPStatus.OK, body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _authorized(self) -> bool:
        header = self.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme != "Bearer" or not token:
            return False
        return verify_internal_operator_jwt(token) is not None

    def _request_id(self) -> str:
        return str(uuid.uuid4())

    def _write_json(self, status: HTTPStatus, body: dict) -> None:
        raw = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def run(host: str = "127.0.0.1", port: int = 4180) -> None:
    server = ThreadingHTTPServer((host, port), ReadinessDigestHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run()

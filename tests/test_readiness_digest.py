from __future__ import annotations

import io
import json
import logging
import os
import socketserver
import time
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

from backend.internal_operator_auth import load_internal_operator_auth_config, verify_internal_operator_jwt
from backend.readiness_digest import WORKSPACE_ROOT, build_digest
from backend.readiness_digest_server import ReadinessDigestHandler


class ReadinessDigestTests(unittest.TestCase):
    def test_build_digest_has_required_shape(self) -> None:
        digest = build_digest(generated_at="2026-05-30T22:00:00Z", request_id="req-shape")
        self.assertEqual(digest["sliceId"], "SECOND-SLICE-RD-001")
        self.assertEqual(digest["scope"]["programIssue"], "VOL-132")
        self.assertIn("summary", digest)
        self.assertIn("workstreams", digest)
        self.assertIn("warnings", digest)
        self.assertEqual(digest["generatedAt"], "2026-05-30T22:00:00Z")

    def test_build_digest_emits_degraded_warning_when_doc_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs/second-slice-readiness-digest-architecture.md").write_text("ok")
            logger = logging.getLogger("readiness_digest")
            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            old_level = logger.level
            logger.setLevel(logging.WARNING)
            logger.addHandler(handler)
            try:
                digest = build_digest(workspace_root=root, generated_at="2026-05-30T22:05:00Z", request_id="req-doc-missing")
            finally:
                logger.removeHandler(handler)
                logger.setLevel(old_level)

            codes = {warning["code"] for warning in digest["warnings"]}
            self.assertIn("DEGRADED_SOURCE_DOCUMENTS", codes)
            self.assertIn("readiness_digest_generation_failed", stream.getvalue())

    def test_build_digest_reflects_security_blocker_state(self) -> None:
        digest = build_digest(generated_at="2026-05-30T22:15:00Z", request_id="req-current-state")
        workstreams = {stream["key"]: stream for stream in digest["workstreams"]}

        self.assertEqual(workstreams["qa"]["status"], "done")
        self.assertEqual(workstreams["qa"]["blockers"], [])
        self.assertEqual(workstreams["staging"]["status"], "done")
        self.assertEqual(workstreams["staging"]["blockers"], [])
        self.assertEqual(workstreams["security"]["status"], "in_review")
        self.assertEqual(workstreams["security"]["blockers"], [])
        self.assertEqual(digest["summary"], {"completedWorkstreams": 2, "blockedWorkstreams": 0, "inProgressWorkstreams": 3})
        self.assertEqual(digest["blockers"], [])
        self.assertEqual(digest["warnings"], [])

    def test_sample_response_fixture_matches_live_digest_shape(self) -> None:
        fixture = json.loads((WORKSPACE_ROOT / "docs/second-slice-readiness-digest-sample-response.json").read_text())
        digest = build_digest(generated_at=fixture["generatedAt"], request_id="req-fixture-match")
        self.assertEqual(digest, fixture)

    def test_sample_response_fixture_records_qa_and_staging_evidence_links(self) -> None:
        fixture = json.loads((WORKSPACE_ROOT / "docs/second-slice-readiness-digest-sample-response.json").read_text())
        evidence_paths = {item["path"] for item in fixture["evidenceLinks"]}
        self.assertIn("docs/second-slice-qa-regression-evidence.md", evidence_paths)
        self.assertIn("docs/second-slice-staging-rollback-evidence.md", evidence_paths)

    def test_frontend_reads_authenticated_api_route_not_static_fixture(self) -> None:
        script = (WORKSPACE_ROOT / "ops/readiness-digest/app.js").read_text()
        self.assertIn('const DIGEST_URL = "/api/v1/ops/readiness-digest";', script)
        self.assertNotIn("index.json", script)

    def test_frontend_exposes_auth_required_ui_state(self) -> None:
        html = (WORKSPACE_ROOT / "ops/readiness-digest/index.html").read_text()
        script = (WORKSPACE_ROOT / "ops/readiness-digest/app.js").read_text()
        self.assertIn('id="auth-status"', html)
        self.assertIn('role="alert"', html)
        self.assertIn("Authentication required", script)
        self.assertIn("route-like static digest fixture has been removed", script)

    def test_jwt_verifier_accepts_valid_internal_operator_token(self) -> None:
        with auth_env() as config:
            token = mint_internal_operator_jwt(config=config)
            claims = verify_internal_operator_jwt(token, config=load_internal_operator_auth_config())
        self.assertIsNotNone(claims)
        self.assertEqual(claims["sub"], "operator:readiness-review")

    def test_jwt_verifier_rejects_wrong_role(self) -> None:
        with auth_env() as config:
            token = mint_internal_operator_jwt(config=config, role="viewer")
            claims = verify_internal_operator_jwt(token, config=load_internal_operator_auth_config())
        self.assertIsNone(claims)

    def test_http_401_without_token(self) -> None:
        with running_server(configured=True) as base_url:
            req = urllib.request.Request(f"{base_url}/api/v1/ops/readiness-digest")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=3)
            self.assertEqual(ctx.exception.code, 401)
            body = json.loads(ctx.exception.read().decode("utf-8"))
            self.assertEqual(body["error"]["code"], "unauthorized")

    def test_http_200_with_valid_internal_operator_jwt(self) -> None:
        with running_server(configured=True) as base_url:
            req = urllib.request.Request(f"{base_url}/api/v1/ops/readiness-digest")
            req.add_header("Authorization", f"Bearer {mint_internal_operator_jwt()}")
            with urllib.request.urlopen(req, timeout=3) as response:
                self.assertEqual(response.status, 200)
                body = json.loads(response.read().decode("utf-8"))
            self.assertEqual(body["sliceId"], "SECOND-SLICE-RD-001")
            self.assertEqual(body["scope"]["architectureIssue"], "VOL-136")
            self.assertIn("warnings", body)

    def test_http_401_when_jwt_expired(self) -> None:
        with running_server(configured=True) as base_url:
            req = urllib.request.Request(f"{base_url}/api/v1/ops/readiness-digest")
            req.add_header("Authorization", f"Bearer {mint_internal_operator_jwt(expires_in=-60)}")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=3)
            self.assertEqual(ctx.exception.code, 401)
            body = json.loads(ctx.exception.read().decode("utf-8"))
            self.assertEqual(body["error"]["code"], "unauthorized")

    def test_http_401_when_auth_config_missing_even_if_structurally_valid_jwt_is_sent(self) -> None:
        with running_server(configured=False) as base_url:
            req = urllib.request.Request(f"{base_url}/api/v1/ops/readiness-digest")
            req.add_header("Authorization", f"Bearer {mint_internal_operator_jwt(config=DEFAULT_AUTH_CONFIG)}")
            with self.assertRaises(urllib.error.HTTPError) as ctx:
                urllib.request.urlopen(req, timeout=3)
            self.assertEqual(ctx.exception.code, 401)
            body = json.loads(ctx.exception.read().decode("utf-8"))
            self.assertEqual(body["error"]["code"], "unauthorized")


@contextmanager
def running_server(*, configured: bool):
    with auth_env(enabled=configured):
        server = socketserver.TCPServer(("127.0.0.1", 0), ReadinessDigestHandler, bind_and_activate=False)
        server.allow_reuse_address = True
        server.server_bind()
        server.server_activate()
        host, port = server.server_address
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://{host}:{port}"
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1)


DEFAULT_AUTH_CONFIG = {
    "secret": "paperclip-internal-operator-hs256-secret",
    "issuer": "paperclip.internal.auth",
    "audience": "readiness-digest",
    "required_role": "internal-operator",
    "role_claim": "role",
}


@contextmanager
def auth_env(enabled: bool = True):
    env_names = {
        "INTERNAL_OPERATOR_JWT_SECRET": DEFAULT_AUTH_CONFIG["secret"],
        "INTERNAL_OPERATOR_JWT_ISSUER": DEFAULT_AUTH_CONFIG["issuer"],
        "INTERNAL_OPERATOR_JWT_AUDIENCE": DEFAULT_AUTH_CONFIG["audience"],
        "INTERNAL_OPERATOR_JWT_REQUIRED_ROLE": DEFAULT_AUTH_CONFIG["required_role"],
        "INTERNAL_OPERATOR_JWT_ROLE_CLAIM": DEFAULT_AUTH_CONFIG["role_claim"],
    }
    previous = {name: os.environ.get(name) for name in env_names}
    if enabled:
        for name, value in env_names.items():
            os.environ[name] = value
    else:
        for name in env_names:
            os.environ.pop(name, None)
    try:
        yield DEFAULT_AUTH_CONFIG
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def mint_internal_operator_jwt(*, config: dict[str, str] | None = None, role: str | None = None, expires_in: int = 300) -> str:
    resolved = config or DEFAULT_AUTH_CONFIG
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": resolved["issuer"],
        "aud": resolved["audience"],
        "sub": "operator:readiness-review",
        resolved["role_claim"]: role or resolved["required_role"],
        "iat": now,
        "nbf": now,
        "exp": now + expires_in,
    }
    return encode_hs256_jwt(header=header, payload=payload, secret=resolved["secret"])


def encode_hs256_jwt(*, header: dict[str, str], payload: dict[str, object], secret: str) -> str:
    header_segment = _urlsafe_b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signed_value = f"{header_segment}.{payload_segment}".encode("ascii")
    signature_segment = _urlsafe_b64encode(hmac_digest(secret=secret, value=signed_value))
    return f"{header_segment}.{payload_segment}.{signature_segment}"


def hmac_digest(*, secret: str, value: bytes) -> bytes:
    import hashlib
    import hmac

    return hmac.new(secret.encode("utf-8"), value, hashlib.sha256).digest()


def _urlsafe_b64encode(value: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

assert_eq() {
  local actual="$1"
  local expected="$2"
  local message="$3"
  if [[ "$actual" != "$expected" ]]; then
    printf 'assertion failed: %s\nexpected: %s\nactual: %s\n' "$message" "$expected" "$actual" >&2
    exit 1
  fi
}

backend_pid=""
static_pid=""
cleanup() {
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" 2>/dev/null; then
    kill "$backend_pid"
    wait "$backend_pid" || true
  fi
  if [[ -n "$static_pid" ]] && kill -0 "$static_pid" 2>/dev/null; then
    kill "$static_pid"
    wait "$static_pid" || true
  fi
}
trap cleanup EXIT

python3 -m unittest tests/test_readiness_digest.py

READINESS_DIGEST_TOKEN=paperclip-internal-operator-token \
  python3 -m backend.readiness_digest_server > /tmp/readiness-digest-backend.log 2>&1 &
backend_pid=$!
sleep 1

unauthorized_code="$(curl -sS -o /tmp/readiness-digest-401.json -w '%{http_code}' \
  http://127.0.0.1:4180/api/v1/ops/readiness-digest)"
assert_eq "$unauthorized_code" "401" "digest route must require authentication"

authorized_code="$(curl -sS -H 'Authorization: Bearer paperclip-internal-operator-token' \
  -o /tmp/readiness-digest-200.json -w '%{http_code}' \
  http://127.0.0.1:4180/api/v1/ops/readiness-digest)"
assert_eq "$authorized_code" "200" "digest route must succeed with the bounded operator token"

python3 - <<'PY'
import json
from pathlib import Path

body = json.loads(Path("/tmp/readiness-digest-200.json").read_text())
assert body["sliceId"] == "SECOND-SLICE-RD-001"
assert body["summary"] == {
    "completedWorkstreams": 2,
    "blockedWorkstreams": 1,
    "inProgressWorkstreams": 3,
}
assert body["warnings"] == [
    {
        "code": "DEGRADED_SOURCE_AUTHZ",
        "message": "Security re-review remains blocked pending operator-auth remediation and removal of the published route-like digest fixture.",
    }
]
assert any(
    link["path"] == "docs/second-slice-staging-rollback-evidence.md"
    for link in body["evidenceLinks"]
)
print(body["overallVerdict"])
PY

python3 -m http.server 4173 > /tmp/readiness-digest-static.log 2>&1 &
static_pid=$!
sleep 1

page_code="$(curl -sS -o /tmp/readiness-digest-page.html -w '%{http_code}' \
  http://127.0.0.1:4173/ops/readiness-digest/)"
assert_eq "$page_code" "200" "static operator review page must be reachable"

fixture_code="$(curl -sS -o /tmp/readiness-digest-missing.json -w '%{http_code}' \
  http://127.0.0.1:4173/api/v1/ops/readiness-digest/index.json)"
assert_eq "$fixture_code" "404" "static route-like digest fixture must stay unavailable"

printf 'bounded readiness digest smoke passed\n'

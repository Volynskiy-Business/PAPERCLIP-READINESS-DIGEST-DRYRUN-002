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

wait_for_route() {
  local url="$1"
  local code=""
  local attempts=0
  while ((attempts < 20)); do
    code="$(curl -sS -o /tmp/readiness-digest-check.json -w '%{http_code}' "$url" || true)"
    if [[ "$code" != "000" ]]; then
      return 0
    fi
    attempts=$((attempts + 1))
    sleep 0.5
  done
  printf 'assertion failed: route did not become reachable (%s)\n' "$url" >&2
  exit 1
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
wait_for_route "http://127.0.0.1:4180/api/v1/ops/readiness-digest"

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

expected = json.loads(Path("docs/second-slice-readiness-digest-sample-response.json").read_text())
body = json.loads(Path("/tmp/readiness-digest-200.json").read_text())
assert body == expected
assert any(
    link["path"] == "docs/second-slice-staging-rollback-evidence.md"
    for link in expected["evidenceLinks"]
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

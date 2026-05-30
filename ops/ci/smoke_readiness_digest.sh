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

static_pid=""
cleanup() {
  if [[ -n "$static_pid" ]] && kill -0 "$static_pid" 2>/dev/null; then
    kill "$static_pid"
    wait "$static_pid" || true
  fi
}
trap cleanup EXIT

python3 -m unittest tests/test_readiness_digest.py

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

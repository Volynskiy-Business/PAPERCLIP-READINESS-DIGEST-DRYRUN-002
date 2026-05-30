# Second Slice QA Regression Evidence

Date: 2026-05-30
Issue: VOL-139
Scope: bounded second-slice readiness digest prototype only

## Verdict

Pass with one medium-severity environment limitation.

The bounded regression target covers the executable digest builder, authenticated HTTP route, non-served response fixtures under `docs/`, and operator-facing evidence link set. The QA deliverable for this issue is complete, and the staging evidence gap that previously blocked `VOL-140` is now closed by a separate DevOps evidence artifact.

## Commands and observed results

Verification commands:

```bash
python3 -m unittest tests/test_readiness_digest.py

READINESS_DIGEST_TOKEN=paperclip-internal-operator-token python3 - <<'PY'
import json
import threading
import time
import urllib.request
from backend.readiness_digest_server import run

thread = threading.Thread(target=run, kwargs={"host": "127.0.0.1", "port": 4181}, daemon=True)
thread.start()
time.sleep(0.3)

req = urllib.request.Request("http://127.0.0.1:4181/api/v1/ops/readiness-digest")
req.add_header("Authorization", "Bearer paperclip-internal-operator-token")
with urllib.request.urlopen(req, timeout=3) as response:
    body = json.loads(response.read().decode("utf-8"))
    print(response.status)
    print(body["workstreams"][2]["key"], body["workstreams"][2]["status"])
    print(body["warnings"])
PY

python3 -m http.server 4173
```

Observed results:

- `python3 -m unittest tests/test_readiness_digest.py` -> `Ran 7 tests` and `OK`
- live HTTP check -> `200`, `qa done`, and `0` warnings
- static route serves from `http://127.0.0.1:4173/ops/readiness-digest/`
- no route-like static digest JSON is published under the local static server

## Coverage summary

- Happy path: `build_digest()` emits the expected current-state payload with `VOL-139` and `VOL-140` complete and no active blockers.
- Failure mode: missing source documents produce `DEGRADED_SOURCE_DOCUMENTS` plus a structured warning log event.
- Auth boundary: unauthenticated HTTP requests return `401 unauthorized`.
- Regression lock: the canonical sample response fixture under `docs/` is asserted to match the executable digest output.
- Evidence path regression: the canonical sample response must include the QA evidence artifact link.

## Severity-classified gaps

- Medium: no attached application repository or shared remote staging target exists in this workspace, so verification remains issue-local rather than environment-integrated.
- Low: the operator UI smoke check remains static-file based rather than framework-integrated for the same workspace limitation.

## Review notes

- The wake reason `issue_blockers_resolved` exposed stale staging-blocker data in the digest model; that mismatch is now corrected and covered by regression tests.
- This artifact does not claim portfolio readiness, monitoring readiness, or company-wide autonomous readiness.

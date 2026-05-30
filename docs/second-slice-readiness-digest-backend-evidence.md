# Second Slice Readiness Digest Backend Evidence

Date: 2026-05-30
Issue: VOL-137
Architecture source: `docs/second-slice-readiness-digest-architecture.md`
Backend contract: `docs/second-slice-readiness-digest-openapi.yaml`
Sample fixtures:

- `docs/second-slice-readiness-digest-sample-response.json`
- `docs/second-slice-readiness-digest-sample-degraded-response.json`

## 1. Deliverable status

This heartbeat produced the bounded backend artifact set for the second-slice
readiness digest API:

- executable backend module at `backend/readiness_digest.py`
- executable HTTP handler at `backend/readiness_digest_server.py`
- focused backend tests at `tests/test_readiness_digest.py`
- versioned contract for `GET /api/v1/ops/readiness-digest`
- auth boundary declaration for internal operator access
- canonical success and degraded response fixtures
- explicit partial-source failure rule so the frontend can render warnings

No broader application repository is attached to this workspace, so this
artifact set is an issue-local executable prototype rather than an integrated
service change inside a production codebase.

## 2. Source-to-payload mapping

| Payload field | Source contract | Mapping note |
| --- | --- | --- |
| `sliceId` | fixed slice identifier | constant `SECOND-SLICE-RD-001` |
| `generatedAt` | backend clock | must be emitted in UTC ISO-8601 |
| `scope.programIssue` | VOL-132 | bounded program root only |
| `scope.architectureIssue` | VOL-136 | architecture authority for this slice |
| `summary.*` | aggregated workstream issue states | direct counts, no UI-only reinterpretation |
| `workstreams[].status` | source issue status | preserve raw issue state |
| `workstreams[].blockers` | source issue blockers | issue identifiers only |
| `blockers[]` | unresolved blocker issues | summarize issue id plus plain-language reason |
| `evidenceLinks[]` | operator-visible artifacts in workspace | only link documents safe for internal operator view |
| `warnings[]` | missing/stale/degraded conditions | required for partial-source failure visibility |

## 3. Auth and information-exposure boundary

- The route requires `internalOperatorAuth` bearer authentication.
- The payload is intentionally limited to issue identifiers, statuses, blocker
  identifiers, evidence labels, and workspace-relative document paths.
- Hidden issue comments, credentials, tokens, and unrestricted thread material
  are out of scope and must never be serialized into the digest payload.

## 4. Partial-source failure representation

Partial-source failure is represented as `200 OK` with a renderable digest body
and one or more warning entries:

- `DEGRADED_SOURCE_ISSUES` when issue metadata cannot be fully resolved
- `DEGRADED_SOURCE_DOCUMENTS` when expected evidence links are missing
- `DEGRADED_SOURCE_AUTHZ` when a source exists but is not readable for the
  current operator boundary
- `MISSING_WORKSTREAM_EVIDENCE` when required artifacts are absent
- `STALE_DIGEST_DATA` when freshness rules are violated

Only a total failure to produce any bounded digest should return `503`.

## 5. Logging contract for runtime implementation

The executable backend now emits one structured warning event per degraded
request with at least:

- `event=readiness_digest_generation_failed`
- `requestId`
- `sliceId=SECOND-SLICE-RD-001`
- `source` naming the failing dependency (`issues`, `documents`, or `authz`)
- `degraded=true|false`
- `warningCodes`

This preserves the architecture requirement for structured logs without
inventing a broader observability claim.

## 6. Focused verification performed

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
    print(body["sliceId"])
    print(body["summary"])
PY

python3 - <<'PY'
import json
from pathlib import Path

required_top = {
    "sliceId",
    "generatedAt",
    "scope",
    "overallVerdict",
    "summary",
    "workstreams",
    "blockers",
    "evidenceLinks",
    "warnings",
}
required_scope = {"programIssue", "architectureIssue"}
required_summary = {
    "completedWorkstreams",
    "blockedWorkstreams",
    "inProgressWorkstreams",
}

for name in [
    "docs/second-slice-readiness-digest-sample-response.json",
    "docs/second-slice-readiness-digest-sample-degraded-response.json",
]:
    data = json.loads(Path(name).read_text())
    missing = required_top - data.keys()
    assert not missing, f"{name} missing top-level fields: {sorted(missing)}"
    assert required_scope <= data["scope"].keys(), f"{name} bad scope"
    assert required_summary <= data["summary"].keys(), f"{name} bad summary"
    assert data["sliceId"] == "SECOND-SLICE-RD-001", f"{name} wrong slice"
    assert data["generatedAt"].endswith("Z"), f"{name} generatedAt not UTC"

print("validated readiness digest fixtures")
PY
```

Observed results:

- `python3 -m unittest tests/test_readiness_digest.py` -> `Ran 7 tests` and `OK`
- live request check -> `200`, `SECOND-SLICE-RD-001`, and `{'completedWorkstreams': 2, 'blockedWorkstreams': 1, 'inProgressWorkstreams': 3}`
- fixture validation -> `validated readiness digest fixtures`

## 7. Residual gap

This issue now has executable issue-local backend evidence, but it still does
not prove integration into a larger application repository, CI pipeline, or
staging deployment because no broader service repo is attached to this
workspace.

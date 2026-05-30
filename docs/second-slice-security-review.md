# Second Slice Security Review

Date: 2026-05-30
Issue: VOL-141
Parent: VOL-132
Reviewer: Security Auditor

## Scope

Reviewed artifacts:

- `backend/readiness_digest_server.py`
- `backend/readiness_digest.py`
- `ops/readiness-digest/app.js`
- `api/v1/ops/readiness-digest/index.json`
- `docs/second-slice-readiness-digest-architecture.md`
- `docs/second-slice-readiness-digest-openapi.yaml`

Verification performed:

```bash
python3 -m unittest tests/test_readiness_digest.py
```

Observed result:

- `Ran 7 tests in 1.035s`
- `OK`

The passing test suite proves current behavior, but it does not prove compliance with the operator-only auth boundary defined for this slice.

## Auth and access-control verdict

Auth/access-control review result: fail.

The implementation does not satisfy the documented trust boundary that all routes require authenticated internal operator access.

## Findings

### P1 - Hard-coded fallback bearer token creates a predictable authentication bypass

Evidence:

- `backend/readiness_digest_server.py:57-60` accepts `READINESS_DIGEST_TOKEN` from the environment but silently falls back to the literal value `paperclip-internal-operator-token`.
- The same literal token is repeated in executable examples and tests, which makes the fallback value non-secret and broadly knowable.
- The contract requires an existing internal auth adapter with bearer JWT semantics, not a shared hard-coded secret. See `docs/second-slice-readiness-digest-openapi.yaml:18-19` and `docs/second-slice-readiness-digest-openapi.yaml:53-60`.

Impact:

- Any deployment started without explicit environment configuration will accept a known bearer token.
- This collapses the intended operator-only boundary into source-code knowledge and blocks approval for any environment beyond a disposable local prototype.

Blocking call:

- Block approval until the route fails closed when auth configuration is absent and is wired to the intended internal auth adapter or equivalent trusted verifier.

### P1 - Frontend prototype bypasses the protected API and reads a published static digest artifact directly

Evidence:

- `ops/readiness-digest/app.js:1` points the UI at `../../api/v1/ops/readiness-digest/index.json`.
- `ops/readiness-digest/app.js:141-149` fetches that static JSON directly instead of the authenticated API route.
- `api/v1/ops/readiness-digest/index.json:1-110` contains the full digest payload as a published artifact.
- The architecture contract states that all routes require authenticated internal operator access. See `docs/second-slice-readiness-digest-architecture.md:58-62`.

Impact:

- Even if backend auth is corrected, the delivered operator UI artifact still demonstrates a path that avoids the API auth boundary entirely.
- If this page and static JSON are served together, the digest becomes fetchable without proving operator identity through the backend.

Blocking call:

- Block approval until the UI consumes the authenticated API route, or the static digest fixture is clearly separated from any operator-access surface and cannot be mistaken for a deployable route.

## Residual risk

- `backend/readiness_digest.py` currently serializes only bounded identifiers, statuses, evidence paths, and warning codes. I did not find credential values, hidden comments, or unrestricted thread material in the digest payload shape itself.
- The remaining material risk is access control, not payload over-collection.
- The current unit suite should gain a negative auth regression once remediation lands, because the existing tests confirm the shared-token path instead of proving fail-closed behavior.

## Recommendation

Security recommendation: fail pending remediation.

This review is complete, but the slice should not be treated as security-approved until both P1 findings are remediated and re-reviewed.

## Re-review after auth remediation

Date: 2026-05-30
Issue: VOL-146
Reviewer: Security Auditor

### Verification performed

```bash
python3 -m unittest tests/test_readiness_digest.py
```

Observed result:

- `Ran 10 tests in 1.033s`
- `OK`

### Re-review verdict

Auth/access-control re-review result: fail.

The remediation closed one of the original blocking findings, but the implementation still does not satisfy the documented internal-operator auth boundary and still leaves a route-like static digest artifact exposed outside that boundary.

### Fixed since the first review

- `backend/readiness_digest_server.py:57-62` now fails closed when `READINESS_DIGEST_TOKEN` is absent. The old hard-coded fallback token bypass is no longer present.
- `ops/readiness-digest/app.js:1` and `ops/readiness-digest/app.js:148-168` now fetch the protected API route and show an explicit auth-required state instead of reading `index.json`.
- `tests/test_readiness_digest.py:87-115` now proves both `401` behavior without auth and fail-closed behavior when auth configuration is missing.

### Remaining findings

#### P1 - Auth remediation still uses a shared bearer secret instead of the documented internal auth adapter or JWT boundary

Evidence:

- `backend/readiness_digest_server.py:57-62` authorizes requests by exact string comparison against `READINESS_DIGEST_TOKEN`.
- `docs/second-slice-readiness-digest-openapi.yaml:18-19` and `docs/second-slice-readiness-digest-openapi.yaml:54-60` still document `internalOperatorAuth` with `bearerFormat: JWT` resolved through the existing auth adapter boundary.
- `tests/test_readiness_digest.py:96-115` exercises the same shared-token pattern rather than any trusted issuer, expiry, or operator claim validation.

Impact:

- The route is no longer fail-open, but it is still guarded by a deploy-time shared secret rather than the documented operator identity boundary.
- Any holder of that one token gets full access, and the server does not validate issuer, expiry, audience, or operator role claims.
- This remains a blocking auth-contract mismatch for a route explicitly described as operator-only.

Blocking call:

- Block security approval until the route is wired to the intended internal auth adapter or an equivalent verifier that enforces operator identity claims, not only possession of a shared secret.

#### P1 - Static digest fixture remains published at a route-like path and is still treated as a served review surface

Evidence:

- `api/v1/ops/readiness-digest/index.json` still contains the full digest payload as a static artifact.
- `tests/test_readiness_digest.py:63-66` preserves that published fixture as a first-class output expected to match the live digest.
- `docs/second-slice-staging-rollback-evidence.md:35-45` and `docs/second-slice-staging-rollback-evidence.md:57-67` still document serving and fetching `http://127.0.0.1:4173/api/v1/ops/readiness-digest/index.json` as a reachable review target.

Impact:

- The frontend no longer consumes the static JSON, but the digest payload is still packaged and exercised as a directly fetchable route-like artifact outside the backend auth check.
- This leaves a second delivery path that can be mistaken for or used as a deployable API surface, which defeats the requirement that all routes require authenticated internal operator access.

Blocking call:

- Block security approval until the static digest fixture is removed from route-like published paths or clearly relocated to non-served test-only evidence storage that cannot be confused with a live operator endpoint.

### Residual risk

- I still do not see credential values, hidden issue comments, or unbounded thread material in the digest payload shape produced by `backend/readiness_digest.py`.
- The blocking risk remains access control and distribution of the digest artifact, not payload-field over-collection.

### Recommendation

Security recommendation after re-review: fail pending further remediation.

This re-review is complete. The original fallback-token bypass is resolved, but the slice should not be treated as security-approved until the remaining two P1 access-control findings are remediated and re-reviewed.

## Remediation addendum for VOL-148

Date: 2026-05-30
Issue: VOL-148
Reviewer note: implementation follow-up

Observed remediation:

- the route-like static digest artifact at `api/v1/ops/readiness-digest/index.json` has been removed from the workspace
- regression coverage now compares `build_digest()` against `docs/second-slice-readiness-digest-sample-response.json` instead of a published route-like JSON file
- staging and frontend evidence now treat `docs/` fixtures as audit artifacts only, not as a served operator surface

Residual security status:

- this closes the specific exposure path called out in the P1 static-fixture finding
- the separate shared-secret auth-boundary mismatch remains unresolved and still requires security re-review before approval

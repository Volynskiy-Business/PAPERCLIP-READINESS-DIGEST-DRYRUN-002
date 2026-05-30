# Second Slice Readiness Digest Dry-Run Repo

This repository is the bounded dry-run export for the second-slice readiness digest prototype. It contains only the operator UI, authenticated backend route, focused tests, and evidence artifacts needed to prove the slice in CI without claiming broader product readiness.

## Repository scope

- `backend/`: authenticated readiness digest API handler and digest assembly logic
- `ops/readiness-digest/`: static operator-facing review page
- `tests/`: focused contract and runtime checks for the bounded slice
- `docs/`: evidence pack, API contract, staging proof, and residual-risk notes
- `.github/workflows/readiness-digest-ci.yml`: GitHub Actions verification workflow

## Local verification

Run the same bounded smoke used by CI:

```bash
./ops/ci/smoke_readiness_digest.sh
```

The script proves:

- focused Python tests pass
- the digest API returns `401` without a token
- the digest API returns `200` with the bounded operator token
- the static operator page is reachable
- the removed route-like static digest fixture still returns `404`

## Manual review targets

Serve the backend:

```bash
READINESS_DIGEST_TOKEN=paperclip-internal-operator-token python3 -m backend.readiness_digest_server
```

Serve the static operator page in another shell:

```bash
python3 -m http.server 4173
```

Review URLs:

- API: `http://127.0.0.1:4180/api/v1/ops/readiness-digest`
- UI: `http://127.0.0.1:4173/ops/readiness-digest/`

This repo remains intentionally issue-bounded. It is evidence for dry-run repeatability and CI portability only.

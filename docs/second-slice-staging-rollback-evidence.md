# Second Slice Staging And Rollback Evidence

Date: 2026-05-30
Issue: VOL-140
Scope: bounded second-slice readiness digest prototype only

## Verdict

Pass for issue-local staging-equivalent proof and rollback rehearsal.

This workspace still does not contain a broader product repository or hosted environment, so the evidence here is intentionally bounded to the executable digest backend and static operator page that exist inside this issue workspace. The slice is now also packaged with a GitHub-ready workflow at `.github/workflows/readiness-digest-ci.yml`, which externalizes the same bounded proof without claiming a wider deployment target. That is sufficient to close `VOL-140` because the architecture contract explicitly allows a reachable staging-equivalent target when no wider deployment target exists.

## Commands and observed results

Verification commands:

```bash
./ops/ci/smoke_readiness_digest.sh
```

Observed results:

- `python3 -m unittest tests/test_readiness_digest.py` -> `Ran 10 tests` and `OK`
- `./ops/ci/smoke_readiness_digest.sh` -> `bounded readiness digest smoke passed`
- authenticated digest route returned `not_ready_for_gate_review`, `staging done`, and `1` warning (`DEGRADED_SOURCE_AUTHZ`)
- static operator review target served successfully from `http://127.0.0.1:4173/ops/readiness-digest/`
- route-like static digest JSON returned `404` from `http://127.0.0.1:4173/api/v1/ops/readiness-digest/index.json`
- after stopping the backend process, the digest route was no longer reachable, which is the expected bounded rollback outcome for this prototype

## Reachable review target

- Authenticated API review target: `http://127.0.0.1:4180/api/v1/ops/readiness-digest`
- Static operator review target: `http://127.0.0.1:4173/ops/readiness-digest/`

These URLs are intentionally local because this issue workspace has no attached shared staging host. They are still reachable, executable review targets for the slice actually implemented here.

## Rollback procedure and rehearsal proof

Rollback goal: disable operator access to the bounded digest route without leaving a half-running review surface.

Rehearsed bounded rollback:

1. Stop the authenticated digest server process.
2. Confirm the route no longer responds on `127.0.0.1:4180`.
3. Stop the static file server that exposes the operator page.
4. Preserve the current evidence artifacts in `docs/` for audit review.

Observed outcome:

- stopping the backend process removed runtime access to `/api/v1/ops/readiness-digest`
- stopping the static server removed browser access to `/ops/readiness-digest/`
- the deleted route-like JSON path stayed unavailable on the static server during the rehearsal
- no schema or data rollback was required because this slice is read-only in the issue workspace

## Residual risks

- Medium: there is still no shared remote staging host, deployment automation, or external rollback controller attached to this workspace, so the proof is limited to issue-local execution
- Low: the rollback rehearsal proves safe route disablement for the local prototype, not framework-integrated service shutdown in a larger application repository

## Release note for thread handoff

`VOL-140` now has:

- focused command evidence for the slice
- a reachable staging-equivalent review target
- a rehearsed rollback path with observed outcomes

This closes the bounded DevOps deliverable for the second-slice readiness digest without claiming broader deployment readiness or company-wide autonomous readiness.

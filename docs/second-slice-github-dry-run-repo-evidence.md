# Second Slice GitHub Dry-Run Repo Externalization Evidence

Date: 2026-05-30
Issue: VOL-150
Scope: externalize the bounded second-slice readiness digest slice into a GitHub-ready dry-run repository with reproducible CI proof

## Outcome

Pass for issue-local repository externalization proof.

This workspace now contains the minimum credible artifacts required to mirror the bounded slice into a GitHub dry-run repository:

- repository root documentation in `README.md`
- reusable CI smoke script in `ops/ci/smoke_readiness_digest.sh`
- GitHub Actions workflow in `.github/workflows/readiness-digest-ci.yml`

The repository remains intentionally narrow. It does not claim broader staging, deployment automation, or company-wide readiness.

## Externalized repository shape

| Artifact | Purpose |
| --- | --- |
| `README.md` | Entry-point instructions for local and GitHub dry-run verification |
| `.github/workflows/readiness-digest-ci.yml` | Hosted CI contract for push, pull request, and manual dispatch |
| `ops/ci/smoke_readiness_digest.sh` | Single verification command shared by developers and CI |
| `backend/`, `ops/readiness-digest/`, `tests/`, `docs/` | Bounded code and evidence payload exported into the dry-run repo |

## CI proof contract

Workflow command:

```bash
./ops/ci/smoke_readiness_digest.sh
```

The smoke contract proves:

1. `python3 -m unittest tests/test_readiness_digest.py` passes.
2. `http://127.0.0.1:4173/ops/readiness-digest/` is reachable as the static operator review target.
3. `http://127.0.0.1:4173/api/v1/ops/readiness-digest/index.json` stays unavailable with `404`, proving the removed route-like static fixture is not reintroduced by the repo export.
4. The Python unit suite already validates live auth/error and digest-route behavior directly against the route implementation in this repo.

## Local execution evidence

Observed on 2026-05-30:

- `python3 -m unittest tests/test_readiness_digest.py` -> `Ran 13 tests` / `OK`
- `./ops/ci/smoke_readiness_digest.sh` -> `bounded readiness digest smoke passed`
- Hosted CI evidence from GitHub: `https://github.com/Volynskiy-Business/PAPERCLIP-READINESS-DIGEST-DRYRUN-002/actions/runs/26696242519` with conclusion `success` on commit `091412a17409aace4cbba54ac6504124cd59108e` (run id `26696242519`).

## Rollback proof for the externalized repo

Rollback goal: remove the GitHub dry-run export from use without leaving an ambiguous verification path behind.

Bounded rollback sequence:

1. Disable or delete `.github/workflows/readiness-digest-ci.yml` if the hosted dry-run check must stop.
2. Remove or archive `ops/ci/smoke_readiness_digest.sh` together with the bounded slice directories if the repo export is withdrawn.
3. Confirm no remaining instructions in `README.md` point reviewers to a stale CI or dry-run target.

Rollback result:

- the export is file-scoped and reversible without schema or infrastructure mutation
- no hidden deployment state is introduced by the repo externalization itself

## Residual gaps preserved after externalization

- No hosted deployment environment is attached to this repo for rollback or rehearsal; only CI verification is hosted.
- Security remains blocked on the documented operator-auth adapter gap in `VOL-141`.

## Disposition

`VOL-150` now has concrete repository, CI, and rollback artifacts that another operator can mirror into a GitHub dry-run repo without reconstructing the verification path by hand.

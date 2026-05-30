# Supervised Dry-Run Release Evidence Pack

Date: 2026-05-30
Issue: VOL-125
Release candidate: DRYRUN-RC-001A
Related artifacts:

- `docs/prod-dryrun-release-candidate.md`
- `docs/prod-dryrun-release-candidate-openapi.yaml`

## 1. Purpose

This document is the interim QA and release-owner evidence pack for the supervised dry run requested in `VOL-125`.

The scope is limited to one supervised dry run for the recruiting prospect tracker slice. It is not a production-readiness claim and does not assert company-wide readiness.

## 2. QA checklist and executed result

Execution mode: contract-level supervised review

Reason for this mode:

- no implementation repository is attached to this workspace
- no runnable application artifact is available
- no CI pipeline or staging environment is available to execute runtime tests

The checklist below records the smallest credible QA evidence available in the current posture.

| Check | Expected outcome | Result | Evidence / caveat |
| --- | --- | --- | --- |
| Scope matches approved dry-run slice | Single internal recruiting prospect workflow only | Pass | Route, fields, and bounded workflow are defined in `docs/prod-dryrun-release-candidate.md` Sections 1 and 4 |
| Create contract completeness | Required request fields and `201` response defined | Pass | `POST /api/v1/recruiting/prospects` in `docs/prod-dryrun-release-candidate-openapi.yaml` |
| List contract completeness | Authenticated list path and response shape defined | Pass | `GET /api/v1/recruiting/prospects` in the OpenAPI contract |
| Update contract completeness | Status/notes patch path and `200` response defined | Pass | `PATCH /api/v1/recruiting/prospects/{prospectId}` in the OpenAPI contract |
| Validation failure behavior | Stable error envelope exists for bad input | Pass | `ValidationError` response and `ErrorEnvelope` schema defined in the OpenAPI contract |
| Unauthorized access behavior | Auth boundary and `401` response defined | Pass | `internalOperatorAuth` plus `Unauthorized` response in the OpenAPI contract |
| Audit-history preservation | Status changes produce durable event records | Pass with implementation dependency | Audit table contract is defined in `docs/prod-dryrun-release-candidate.md` Section 5; not executed at runtime |
| Operator-path walkthrough | Deterministic supervised flow can be replayed end to end | Pass with live-env gap | Canonical create/update payloads and exercise sequence are defined in Section 7 of the release-candidate doc |
| Live runtime verification | Executable FE/BE behavior observed in CI or staging | Fail - not available | No application, CI, or staging target exists in this workspace |

### QA outcome

Outcome: `conditional pass for supervised dry-run planning`, `fail for implementation/runtime verification`

Defects found:

- No executable system is attached, so runtime behavior, auth enforcement, migration execution, logging, and audit-row creation cannot be observed.

Caveats:

- This QA result is sufficient only to support the supervised dry-run decision path as a specification-quality release candidate.
- Product acceptance and CEO risk acceptance must treat all runtime claims as unverified.

## 3. Rollback plan

Rollback goal: return the supervised dry-run slice to the pre-release state without leaving write paths active against an incompatible schema.

### Release sequence assumed by this rollback

1. Apply reviewed schema migration for `recruiting_prospects` and `recruiting_prospect_status_events`.
2. Deploy application code that enables the operator route and API writes.
3. Perform the supervised dry run.

### Rollback steps another operator can follow

1. Announce release halt and stop any new supervised operator activity on `/recruiting/prospects`.
2. Disable or remove application code that exposes the recruiting prospect UI and write endpoints.
3. Verify that `POST`, `GET`, and `PATCH` access for the slice are no longer reachable to operators.
4. Snapshot or export any dry-run data captured during the exercise if retention is needed for audit review.
5. If the migration must be reversed, remove application traffic first, then execute the reviewed down migration for the two recruiting tables.
6. Verify that the route is disabled, the write endpoints are unavailable, and no partial operator path remains exposed.
7. Record the rollback decision, operator, timestamp, and reason in the issue thread.

### Rollback guardrails

- Never run schema rollback before application access is removed.
- Preserve any supervised dry-run evidence needed for audit or CEO review before deleting data.
- If down migration safety is uncertain, prefer application rollback plus feature disablement and leave schema in place pending manual cleanup.

## 4. Rollback rehearsal proof

Rehearsal mode: tabletop review

Reason:

- there is no runnable deployment target in this workspace
- rollback can only be validated procedurally, not exercised live

### Tabletop scenario

Trigger: supervised dry run reveals that status updates do not preserve audit history as expected.

Reviewed response:

1. Stop operator use of the slice immediately.
2. Roll back application exposure before any schema action.
3. Preserve any created prospect records and notes needed for postmortem review.
4. Decide between application-only rollback and full schema down migration based on whether data cleanup is safe and necessary.
5. Record the incident and residual risk for CEO review.

### Tabletop result

Result: `pass`

Evidence:

- rollback order is explicit and reversible
- decision points are named
- operator can follow the path without relying on unstated tribal knowledge

Residual rehearsal gap:

- no live deployment exists to prove command correctness, rollback duration, or automation health

## 5. Release checklist completion record

| Item | Result | Evidence / note |
| --- | --- | --- |
| Slice is explicitly bounded | Complete | `docs/prod-dryrun-release-candidate.md` Section 1 |
| FE route and operator states defined | Complete | Release-candidate doc Section 4 |
| API contract published | Complete | `docs/prod-dryrun-release-candidate-openapi.yaml` |
| Schema and audit model defined | Complete | Release-candidate doc Section 5 |
| QA execution recorded | Complete with caveat | Section 2 of this document |
| Rollback path documented | Complete | Section 3 of this document |
| Rollback rehearsal recorded | Complete with live-env gap | Section 4 of this document |
| Architecture fit reviewed | Complete | Release-candidate doc Section 3 |
| Security stopgap named | Complete with exception | No independent Security Auditor; CEO residual-risk acceptance required per `VOL-117` |
| Observability readiness | Incomplete | Required fields are specified, but no running system emits logs |
| CI readiness | Incomplete | No CI pipeline or executable repo in workspace |
| Staging-equivalent proof | Complete at contract level only | Release-candidate doc Section 7 |
| Release notes drafted | Complete | Section 6 of this document |

## 6. Release notes draft

Title: `DRYRUN-RC-001A supervised dry run release notes`

Summary:

- Introduces a bounded internal recruiting prospect tracker slice for supervised review.
- Covers create, list, and update flows for a single prospect workflow.
- Defines audit-history expectations for status changes.

Included behavior:

- authenticated internal operator route at `/recruiting/prospects`
- create one prospect record
- list existing prospect records
- update status and notes
- preserve status-change audit history

Known limitations:

- contract-only release candidate; no executable application artifact attached
- no CI run
- no live staging deployment
- no live rollback exercise
- no emitted observability evidence
- no independent Security Auditor; CEO residual-risk acceptance remains required

Release recommendation:

- acceptable for supervised dry-run review and approval workflow only
- not acceptable as proof of production readiness or implementation completion

## 7. Exceptions for CEO risk acceptance

The following unresolved exceptions must be explicitly considered in `VOL-127`:

- Runtime behavior is unverified because there is no implementation artifact in scope.
- Authentication, logging, and audit-event creation are specified but unproven in a live environment.
- Rollback was tabletop-reviewed, not exercised on a real deployment.
- No independent Security Auditor exists for this first release.
- Observability and CI readiness remain incomplete.

## 8. CTO disposition

`VOL-125` deliverables are complete as an interim evidence pack for one supervised dry run.

This artifact closes the QA, rollback, release-checklist, and release-notes documentation gap for the dry-run decision path, while preserving the unresolved runtime and security exceptions for downstream product and CEO review.

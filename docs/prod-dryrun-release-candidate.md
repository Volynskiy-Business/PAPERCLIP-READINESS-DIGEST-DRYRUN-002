# Supervised Dry-Run Release Candidate

Date: 2026-05-30
Issue: VOL-124
Release candidate: DRYRUN-RC-001A
Slice source: VOL-118 supervised pilot slice, tied to the warm-path recruiting workflow referenced in VOL-119

## 1. Scope

This release candidate is the narrowest technical slice that can satisfy the dry-run objective without expanding beyond the accepted first slice.

### Exact slice

Internal recruiting tracker for one candidate-prospect record:

- one authenticated internal page for recruiting operations
- create one prospect record
- list the saved record in a table
- update status and operator notes
- preserve audit history for status changes

The slice is intentionally limited to internal use, one business workflow, and one reversible data model.

## 2. Release-candidate artifact set

- Product and technical release note: this document
- Operational release evidence pack: `docs/prod-dryrun-release-evidence.md`
- API contract: `docs/prod-dryrun-release-candidate-openapi.yaml`
- Data model and migration notes: Sections 4 and 5 of this document
- Staging-equivalent exercise transcript: Section 7 of this document

## 3. Architecture fit and ADR stance

This release candidate stays within the VOL-116 architecture baseline:

- modular monolith
- versioned HTTP/JSON API
- one primary relational database
- explicit auth boundary
- structured logging for user-facing mutations

ADR status for this slice:

| ADR | Status for DRYRUN-RC-001A | Notes |
| --- | --- | --- |
| ADR-001 architecture style | accepted | Modular monolith retained |
| ADR-002 datastore rules | accepted | Relational schema with reviewed migration sequencing |
| ADR-003 auth boundary | accepted | Internal operator access behind auth adapter |
| ADR-004 API contract style | accepted | Versioned HTTP/JSON with stable error envelope |
| ADR-005 CI/CD and rollback | partial waiver | No executable build or staging pipeline exists in this workspace; rollback is documented but not exercised |
| ADR-006 observability minimum bar | partial waiver | Required log/event fields are specified but not emitted by running code |
| ADR-007 secrets handling | partial waiver | Boundary is named, but no live environment configuration is present in this workspace |

## 4. Frontend and operator contract

### Page

- Route: `/recruiting/prospects`
- Audience: authenticated internal operator only

### Required fields

- `fullName`
- `fitRationale`
- `relationshipSource`
- `contactPath`
- `intendedMotion`
- `intendedSender`
- `status`

### Optional fields

- `notes`
- `linkedinUrl`
- `company`

### Required UX states

- empty table state before the first prospect exists
- inline validation errors for missing required fields
- loading state for create/list/update actions
- success confirmation after create and update
- failure state using the stable API error envelope

## 5. Backend, schema, and audit contract

### API operations

- `POST /api/v1/recruiting/prospects`
- `GET /api/v1/recruiting/prospects`
- `PATCH /api/v1/recruiting/prospects/{prospectId}`

The exact request and response schema, auth model, and error envelope are defined in `docs/prod-dryrun-release-candidate-openapi.yaml`.

### Persistence model

Primary table: `recruiting_prospects`

Columns:

- `id` uuid primary key
- `full_name` text not null
- `fit_rationale` text not null
- `relationship_source` text not null
- `contact_path` text not null
- `intended_motion` text not null
- `intended_sender` text not null
- `status` text not null
- `notes` text null
- `linkedin_url` text null
- `company` text null
- `created_at` timestamptz not null
- `updated_at` timestamptz not null
- `created_by` uuid not null
- `updated_by` uuid not null

Audit table: `recruiting_prospect_status_events`

Columns:

- `id` uuid primary key
- `prospect_id` uuid not null references `recruiting_prospects(id)`
- `from_status` text null
- `to_status` text not null
- `changed_by` uuid not null
- `change_note` text null
- `changed_at` timestamptz not null

### Migration and deploy notes

- create both tables in the same reviewed migration
- deploy schema before enabling writes from the UI
- keep status values constrained to the enumerated set in the API contract
- rollback-safe sequence is schema first, application second; rollback reverses that order

## 6. Technical evidence captured in this heartbeat

### FE/BE/API contract evidence

- Exact UI fields, states, and route are defined in this document
- Exact API contract is published in `docs/prod-dryrun-release-candidate-openapi.yaml`
- Explicit schema and audit-history model are defined in Section 5

### Test evidence at the smallest credible level available

Because there is no application repository, executable implementation, CI pipeline, or staging environment attached to this issue workspace, the only credible evidence available in this heartbeat is specification-level evidence:

- contract completeness review against VOL-118 definition of done
- schema review for create/list/update plus audit-history preservation
- operator-path validation using deterministic request/response fixtures in the API contract

Required test cases for the future executable implementation:

- create prospect success
- create prospect required-field failure
- unauthorized access rejected
- list prospects for internal operator
- status update persists and creates an audit event
- notes update persists without dropping prior status history

Outcome for this heartbeat: specification evidence exists; executable test evidence does not yet exist.

## 7. Staging-equivalent exercise proof

No live staging environment exists for this slice in the current product posture. The staging-equivalent proof for this release candidate is a deterministic supervised transcript against the published contract.

### Exercise sequence

1. Operator opens `/recruiting/prospects` and sees the empty-table state.
2. Operator submits a valid create payload for one prospect.
3. API returns `201` with the created record and audit fields.
4. Operator refreshes the list and sees the saved row.
5. Operator updates the status and notes.
6. API returns `200` with the updated row.
7. Audit trail records the status transition as a new event row.

### Canonical example payload

```json
{
  "fullName": "Alex Example",
  "fitRationale": "Strong backend and systems judgment for founding engineer scope.",
  "relationshipSource": "Warm intro from operator network",
  "contactPath": "Email intro",
  "intendedMotion": "Founder intro call",
  "intendedSender": "CEO",
  "status": "new",
  "notes": "Prior startup infrastructure lead."
}
```

### Canonical status update

```json
{
  "status": "contacted",
  "notes": "Intro requested from shared contact."
}
```

Outcome for this heartbeat: staging-equivalent supervised exercise path is explicit and reproducible at the contract level; live staging proof remains a gap.

## 8. Residual gaps carried into release decision

- No implementation repository or running application artifact is attached to this issue workspace.
- No executable frontend or backend code exists here to validate the contract against runtime behavior.
- No CI run exists for this slice.
- No live staging deployment or rollback rehearsal exists for this slice.
- No live observability output exists for create/update mutations.
- No independent Security Auditor exists; CEO residual-risk acceptance remains mandatory under VOL-117.

## 9. CTO decision note

`DRYRUN-RC-001A` is acceptable as a bounded technical release-candidate dossier for the supervised dry-run decision path only.

It is **not** evidence of implementation completion, green CI, or production readiness. The value of this artifact is that it removes ambiguity around the exact slice, the contract to build, the schema to migrate, the operator flow to exercise, and the technical gaps that still require QA, product acceptance, and CEO residual-risk review.

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger("readiness_digest")
SLICE_ID = "SECOND-SLICE-RD-001"
PROGRAM_ISSUE = "VOL-132"
ARCHITECTURE_ISSUE = "VOL-136"
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent

WORKSTREAM_SOURCES = [
    {
        "key": "backend",
        "issue": "VOL-137",
        "status": "in_progress",
        "blockers": [],
        "requiredEvidence": [
            "API handler and mapping logic",
            "Focused backend test run",
            "Sample response fixture",
        ],
    },
    {
        "key": "frontend",
        "issue": "VOL-138",
        "status": "in_progress",
        "blockers": [],
        "requiredEvidence": [
            "Route artifact",
            "Responsive layout verification",
            "Browser-visible smoke check",
        ],
    },
    {
        "key": "qa",
        "issue": "VOL-139",
        "status": "done",
        "blockers": [],
        "requiredEvidence": [
            "Happy-path regression pass",
            "Degraded-state test",
        ],
    },
    {
        "key": "staging",
        "issue": "VOL-140",
        "status": "done",
        "blockers": [],
        "requiredEvidence": [
            "Focused CI command evidence",
            "Reachable review target",
            "Rollback rehearsal note",
        ],
    },
    {
        "key": "security",
        "issue": "VOL-141",
        "status": "in_review",
        "blockers": [],
        "requiredEvidence": [
            "Auth and exposure review",
            "Residual risk note",
        ],
    },
    {
        "key": "technical_audit",
        "issue": "VOL-142",
        "status": "in_progress",
        "blockers": [],
        "requiredEvidence": [
            "Repeatability verdict",
            "Comparison to first dry run",
        ],
    },
]

EVIDENCE_SOURCES = [
    {
        "label": "Architecture contract",
        "path": "docs/second-slice-readiness-digest-architecture.md",
    },
    {
        "label": "Portfolio synthesis",
        "path": "docs/portfolio-autonomy-readiness-evidence-synthesis.md",
    },
    {
        "label": "Frontend UI evidence",
        "path": "docs/second-slice-frontend-ui-evidence.md",
    },
    {
        "label": "Backend API contract",
        "path": "docs/second-slice-readiness-digest-openapi.yaml",
    },
    {
        "label": "Backend implementation evidence",
        "path": "docs/second-slice-readiness-digest-backend-evidence.md",
    },
    {
        "label": "QA regression evidence",
        "path": "docs/second-slice-qa-regression-evidence.md",
    },
    {
        "label": "Staging and rollback evidence",
        "path": "docs/second-slice-staging-rollback-evidence.md",
    },
]

KNOWN_WARNING_CODES = {
    "MISSING_WORKSTREAM_EVIDENCE",
    "STALE_DIGEST_DATA",
    "DEGRADED_SOURCE_ISSUES",
    "DEGRADED_SOURCE_DOCUMENTS",
    "DEGRADED_SOURCE_AUTHZ",
}


@dataclass
class DigestSourceError(Exception):
    source: str
    code: str
    message: str
    degraded: bool = True

    def __str__(self) -> str:
        return f"{self.source}: {self.code}: {self.message}"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def summary_counts(workstreams: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "completedWorkstreams": sum(1 for ws in workstreams if ws["status"] == "done"),
        "blockedWorkstreams": sum(1 for ws in workstreams if ws["status"] == "blocked"),
        "inProgressWorkstreams": sum(1 for ws in workstreams if ws["status"] == "in_progress"),
    }


def determine_verdict(workstreams: list[dict[str, Any]], warnings: list[dict[str, str]]) -> str:
    if warnings or any(ws["status"] == "blocked" for ws in workstreams):
        return "not_ready_for_gate_review"
    if all(ws["status"] in {"done", "in_review"} for ws in workstreams if ws["key"] in {"backend", "frontend", "security"}):
        return "ready_for_cto_review"
    return "not_ready_for_gate_review"


def build_blockers(workstreams: list[dict[str, Any]]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    for workstream in workstreams:
        if workstream["status"] != "blocked":
            continue
        reason = "; ".join(workstream["blockers"]) if workstream["blockers"] else "Blocked without recorded reason."
        blockers.append({"issue": workstream["issue"], "reason": reason})
    return blockers


def load_evidence_links(workspace_root: Path = WORKSPACE_ROOT) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    links: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    missing: list[str] = []
    for evidence in EVIDENCE_SOURCES:
        rel_path = evidence["path"]
        if (workspace_root / rel_path).exists():
            links.append(evidence)
        else:
            missing.append(rel_path)
    if missing:
        warnings.append(
            {
                "code": "DEGRADED_SOURCE_DOCUMENTS",
                "message": "One or more expected evidence documents could not be resolved: " + ", ".join(missing),
            }
        )
    return links, warnings


def detect_evidence_gaps(workstreams: list[dict[str, Any]], evidence_links: list[dict[str, str]]) -> list[dict[str, str]]:
    evidence_paths = {item["path"] for item in evidence_links}
    warnings: list[dict[str, str]] = []
    if "docs/second-slice-readiness-digest-backend-evidence.md" not in evidence_paths:
        warnings.append(
            {
                "code": "MISSING_WORKSTREAM_EVIDENCE",
                "message": "Backend evidence artifact is missing from the bounded workspace.",
            }
        )
    if "docs/second-slice-qa-regression-evidence.md" not in evidence_paths:
        warnings.append(
            {
                "code": "MISSING_WORKSTREAM_EVIDENCE",
                "message": "QA regression evidence artifact is missing from the bounded workspace.",
            }
        )

    blocked_verification_streams = [ws["key"] for ws in workstreams if ws["status"] == "blocked" and ws["key"] in {"qa", "staging"}]
    if blocked_verification_streams:
        names = " and ".join(blocked_verification_streams)
        warnings.append(
            {
                "code": "MISSING_WORKSTREAM_EVIDENCE",
                "message": f"{names.capitalize()} evidence remains incomplete for the second slice.",
            }
        )

    return warnings


def build_digest(
    *,
    workspace_root: Path = WORKSPACE_ROOT,
    generated_at: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    workstreams = [dict(item) for item in WORKSTREAM_SOURCES]
    evidence_links, doc_warnings = load_evidence_links(workspace_root)
    warnings = list(doc_warnings)
    warnings.extend(detect_evidence_gaps(workstreams, evidence_links))

    for warning in warnings:
        if warning["code"] not in KNOWN_WARNING_CODES:
            raise DigestSourceError(
                source="issues",
                code="DEGRADED_SOURCE_ISSUES",
                message=f"Unknown warning code emitted: {warning['code']}",
                degraded=False,
            )

    digest = {
        "sliceId": SLICE_ID,
        "generatedAt": generated_at or utc_now_iso(),
        "scope": {
            "programIssue": PROGRAM_ISSUE,
            "architectureIssue": ARCHITECTURE_ISSUE,
        },
        "overallVerdict": determine_verdict(workstreams, warnings),
        "summary": summary_counts(workstreams),
        "workstreams": workstreams,
        "blockers": build_blockers(workstreams),
        "evidenceLinks": evidence_links,
        "warnings": warnings,
    }

    if warnings:
        LOGGER.warning(
            json.dumps(
                {
                    "event": "readiness_digest_generation_failed",
                    "requestId": request_id,
                    "sliceId": SLICE_ID,
                    "source": "documents",
                    "degraded": True,
                    "warningCodes": [warning["code"] for warning in warnings],
                }
            )
        )

    return digest

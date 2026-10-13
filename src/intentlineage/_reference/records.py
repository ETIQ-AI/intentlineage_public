"""Adapted from raluca07/use_case_icp at 5bd37b1ca3e49e940fc885839fa56411203afee0.
Source provenance and adaptation map: resources/reference-use-case-icp/reuse-v4.json.
No top-level upstream licence was found; retained for authorized local adaptation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid
SCHEMA_VERSION = "1"

def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


@dataclass(slots=True)
class EtiqNodeRecord:
    node_ref: str
    raw_id: str | None
    names: list[str]
    line_no: int | None
    state_type: str
    value_type: str | None
    func_stack: list[str]
    source: str | None
    scope_type: str | None
    raw_metadata: dict[str, Any]
    value_preview: Any | None = None
    preview_truncated: bool = False
    artifact_kind: str | None = None
    artifact_content: Any | None = None
    artifact_truncated: bool = False
    artifact_size: dict[str, int] | None = None


@dataclass(slots=True)
class EtiqRelationshipRecord:
    relationship_ref: str
    source_ref: str
    target_ref: str
    relationship_type: str
    direction: str
    raw_metadata: dict[str, Any]


@dataclass(slots=True)
class EtiqEvidenceSnapshot:
    snapshot_id: str
    job_id: str
    run_id: str
    nodes: list[EtiqNodeRecord]
    relationships: list[EtiqRelationshipRecord]
    inventories: dict[str, Any]
    scan_errors: list[Any]
    created_at: str = field(default_factory=utc_now)
    schema_version: str = SCHEMA_VERSION

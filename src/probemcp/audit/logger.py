"""Local audit logging primitives."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import Field

from probemcp.mcp_server.schemas import (
    DebugError,
    JsonValue,
    PermissionLevel,
    SchemaModel,
    TargetState,
)


class AuditOutcome(StrEnum):
    """Tool call outcome recorded in the audit log."""

    SUCCESS = "success"
    ERROR = "error"


class AuditEvent(SchemaModel):
    """Serializable audit event for one tool call."""

    audit_id: str = Field(default_factory=lambda: f"audit_{uuid4().hex}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    session_id: str | None = None
    tool_name: str
    permission_mode: PermissionLevel
    target_state_before: TargetState = TargetState.UNKNOWN
    target_state_after: TargetState = TargetState.UNKNOWN
    outcome: AuditOutcome
    request_summary: dict[str, JsonValue] = Field(default_factory=dict)
    result_summary: dict[str, JsonValue] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    error: DebugError | None = None


class JsonlAuditWriter:
    """Append-only JSONL audit writer."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: AuditEvent) -> None:
        """Append one audit event as one JSON object per line."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as audit_file:
            audit_file.write(event.model_dump_json())
            audit_file.write("\n")

    def read_events(self) -> list[AuditEvent]:
        """Read all events from the JSONL file."""

        if not self.path.exists():
            return []

        events: list[AuditEvent] = []
        with self.path.open("r", encoding="utf-8") as audit_file:
            for line in audit_file:
                stripped = line.strip()
                if stripped:
                    events.append(AuditEvent.model_validate_json(stripped))
        return events

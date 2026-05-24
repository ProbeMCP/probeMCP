"""Local audit logging primitives."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import Field

from probemcp.mcp_server.schemas import (
    DebugError,
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
    request_summary: dict[str, Any] = Field(default_factory=dict)
    result_summary: dict[str, Any] = Field(default_factory=dict)
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


class SQLiteAuditWriter:
    """Append-only SQLite audit writer."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._initialize()

    def append(self, event: AuditEvent) -> None:
        """Append one audit event as a JSON payload."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "insert into audit_events (audit_id, timestamp, session_id, tool_name, "
                "outcome, payload_json) values (?, ?, ?, ?, ?, ?)",
                (
                    event.audit_id,
                    event.timestamp.isoformat(),
                    event.session_id,
                    event.tool_name,
                    event.outcome.value,
                    event.model_dump_json(),
                ),
            )

    def read_events(self) -> list[AuditEvent]:
        """Read all events ordered by insertion."""

        if not self.path.exists():
            return []
        with sqlite3.connect(self.path) as connection:
            rows = connection.execute(
                "select payload_json from audit_events order by id asc"
            ).fetchall()
        return [AuditEvent.model_validate_json(row[0]) for row in rows]

    def _initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "create table if not exists audit_events ("
                "id integer primary key autoincrement, "
                "audit_id text not null unique, "
                "timestamp text not null, "
                "session_id text, "
                "tool_name text not null, "
                "outcome text not null, "
                "payload_json text not null)"
            )

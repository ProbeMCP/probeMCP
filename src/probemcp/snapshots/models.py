"""Debug snapshot data models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import Field

from probemcp.mcp_server.schemas import SchemaModel, TargetState
from probemcp.symbols import SymbolContext


class DebugSnapshot(SchemaModel):
    """Point-in-time target state used by analyzers."""

    snapshot_id: str = Field(default_factory=lambda: f"snapshot_{uuid4().hex}")
    session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    state: TargetState
    core_registers: dict[str, str] = Field(default_factory=dict)
    fault_registers: dict[str, str] = Field(default_factory=dict)
    stack_address: str | None = None
    stack_data_hex: str | None = None
    symbol_context: SymbolContext | None = None
    summary: str = ""

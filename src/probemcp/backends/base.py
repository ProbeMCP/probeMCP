"""Backend adapter interfaces."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from probemcp.mcp_server.schemas import BackendKind, SchemaModel, TargetState
from probemcp.mi.controller import MIController


class BackendFeature(StrEnum):
    """Backend capability flags."""

    CONNECT = "connect"
    RESET = "reset"
    HALT = "halt"
    BREAKPOINTS = "breakpoints"
    MEMORY_READ = "memory-read"


class BackendConnection(SchemaModel):
    """Result of attaching a backend to a target."""

    backend: BackendKind
    endpoint: str
    profile: str
    architecture: str | None = None
    state: TargetState = TargetState.UNKNOWN
    features: list[BackendFeature] = []


class BackendAdapter(Protocol):
    """Adapter contract for GDB-compatible backends."""

    kind: BackendKind

    async def connect(
        self,
        controller: MIController,
        *,
        endpoint: str,
        profile: str,
        timeout_ms: int,
    ) -> BackendConnection:
        """Connect the controller to a backend target."""

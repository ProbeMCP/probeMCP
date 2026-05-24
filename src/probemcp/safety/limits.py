"""Resource limits for local debugging operations."""

from __future__ import annotations

from dataclasses import dataclass

from probemcp.errors import ErrorCode, make_error
from probemcp.mcp_server.schemas import DebugError, ErrorCategory


@dataclass(frozen=True, slots=True)
class ResourceLimits:
    """Conservative defaults for AI-driven debugger sessions."""

    max_sessions: int = 4
    max_memory_read_bytes: int = 4096

    def check_session_count(self, active_sessions: int) -> DebugError | None:
        """Return an error when opening another session would exceed limits."""

        if active_sessions >= self.max_sessions:
            return make_error(
                ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                f"active session limit reached ({self.max_sessions})",
                ErrorCategory.VALIDATION,
                details={"max_sessions": self.max_sessions},
            )
        return None

    def check_memory_read(self, length: int) -> DebugError | None:
        """Return an error when a memory read is too large."""

        if length > self.max_memory_read_bytes:
            return make_error(
                ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                f"memory read length {length} exceeds limit {self.max_memory_read_bytes}",
                ErrorCategory.VALIDATION,
                details={"max_memory_read_bytes": self.max_memory_read_bytes},
            )
        return None

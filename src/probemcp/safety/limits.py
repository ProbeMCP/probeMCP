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
    max_memory_write_bytes: int = 256
    max_snapshot_stack_bytes: int = 4096
    max_concurrent_tool_calls: int = 8
    max_session_operations: int = 1
    max_mi_command_queue: int = 32

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

    def check_memory_write(self, length: int) -> DebugError | None:
        """Return an error when a memory write is too large."""

        if length > self.max_memory_write_bytes:
            return make_error(
                ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                f"memory write length {length} exceeds limit {self.max_memory_write_bytes}",
                ErrorCategory.VALIDATION,
                details={"max_memory_write_bytes": self.max_memory_write_bytes},
            )
        return None

    def check_snapshot_stack(self, stack_bytes: int) -> DebugError | None:
        """Return an error when a snapshot stack capture is too large."""

        if stack_bytes > self.max_snapshot_stack_bytes:
            return make_error(
                ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                f"snapshot stack bytes {stack_bytes} exceeds limit "
                f"{self.max_snapshot_stack_bytes}",
                ErrorCategory.VALIDATION,
                details={"max_snapshot_stack_bytes": self.max_snapshot_stack_bytes},
            )
        return None

    def check_tool_concurrency(self, active_calls: int) -> DebugError | None:
        """Return an error when too many tool calls are active."""

        if active_calls >= self.max_concurrent_tool_calls:
            return make_error(
                ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                f"concurrent tool call limit reached ({self.max_concurrent_tool_calls})",
                ErrorCategory.VALIDATION,
                details={"max_concurrent_tool_calls": self.max_concurrent_tool_calls},
            )
        return None

    def check_session_operations(self, active_operations: int) -> DebugError | None:
        """Return an error when a session already has too many active operations."""

        if active_operations >= self.max_session_operations:
            return make_error(
                ErrorCode.RESOURCE_LIMIT_EXCEEDED,
                f"active session operation limit reached ({self.max_session_operations})",
                ErrorCategory.VALIDATION,
                details={"max_session_operations": self.max_session_operations},
            )
        return None

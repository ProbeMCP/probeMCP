"""Tool metadata registry for ProbeMCP MCP tools."""

from __future__ import annotations

from dataclasses import dataclass

from probemcp.mcp_server.schemas import PermissionLevel
from probemcp.safety.policy import DebugOperation


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    """Static tool metadata used by the MCP layer and safety engine."""

    name: str
    operation: DebugOperation
    permission: PermissionLevel
    timeout_ms: int
    description: str


class ToolRegistry:
    """Registry of supported v0.1 tools."""

    def __init__(self) -> None:
        self._tools = {tool.name: tool for tool in _DEFAULT_TOOLS}

    def get(self, name: str) -> ToolDefinition:
        """Return one tool definition."""

        return self._tools[name]

    def list(self) -> list[ToolDefinition]:
        """List all tool definitions sorted by name."""

        return [self._tools[name] for name in sorted(self._tools)]


_DEFAULT_TOOLS = (
    ToolDefinition(
        "connect_target",
        DebugOperation.CONNECT_TARGET,
        PermissionLevel.CONFIRM_REQUIRED,
        30_000,
        "Connect to a GDB-compatible target.",
    ),
    ToolDefinition(
        "disconnect_target",
        DebugOperation.DISCONNECT_TARGET,
        PermissionLevel.CONFIRM_REQUIRED,
        5000,
        "Disconnect from a target.",
    ),
    ToolDefinition(
        "halt",
        DebugOperation.HALT,
        PermissionLevel.CONFIRM_REQUIRED,
        2000,
        "Interrupt target execution.",
    ),
    ToolDefinition(
        "resume",
        DebugOperation.RESUME,
        PermissionLevel.CONFIRM_REQUIRED,
        1000,
        "Resume target execution with a bounded timeout.",
    ),
    ToolDefinition(
        "step_instruction",
        DebugOperation.STEP_INSTRUCTION,
        PermissionLevel.CONFIRM_REQUIRED,
        5000,
        "Step one target instruction.",
    ),
    ToolDefinition(
        "read_registers",
        DebugOperation.READ_REGISTERS,
        PermissionLevel.READONLY,
        3000,
        "Read target registers.",
    ),
    ToolDefinition(
        "read_memory",
        DebugOperation.READ_MEMORY,
        PermissionLevel.READONLY,
        3000,
        "Read target memory bytes.",
    ),
    ToolDefinition(
        "set_breakpoint",
        DebugOperation.SET_BREAKPOINT,
        PermissionLevel.CONFIRM_REQUIRED,
        3000,
        "Set a target breakpoint.",
    ),
    ToolDefinition(
        "clear_breakpoint",
        DebugOperation.CLEAR_BREAKPOINT,
        PermissionLevel.CONFIRM_REQUIRED,
        3000,
        "Clear a target breakpoint.",
    ),
    ToolDefinition(
        "debug_snapshot",
        DebugOperation.DEBUG_SNAPSHOT,
        PermissionLevel.READONLY,
        5000,
        "Capture a structured debug snapshot.",
    ),
    ToolDefinition(
        "analyze_fault",
        DebugOperation.ANALYZE_FAULT,
        PermissionLevel.READONLY,
        5000,
        "Analyze Cortex-M fault state.",
    ),
)

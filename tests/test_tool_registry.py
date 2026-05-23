from probemcp.mcp_server.schemas import PermissionLevel
from probemcp.mcp_server.tools import ToolRegistry
from probemcp.safety.policy import DebugOperation


def test_tool_registry_lists_v0_1_tools_with_permissions() -> None:
    registry = ToolRegistry()

    tools = {tool.name: tool for tool in registry.list()}

    assert tools["read_registers"].permission == PermissionLevel.READONLY
    assert tools["halt"].permission == PermissionLevel.CONFIRM_REQUIRED
    assert tools["analyze_fault"].operation == DebugOperation.ANALYZE_FAULT


def test_tool_registry_get_returns_static_definition() -> None:
    tool = ToolRegistry().get("connect_target")

    assert tool.timeout_ms == 30_000
    assert tool.operation == DebugOperation.CONNECT_TARGET

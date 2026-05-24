import pytest

from probemcp.mcp_server.app import create_app
from probemcp.mcp_server.schemas import (
    DebugSnapshotRequest,
    ReadMemoryData,
    RegisterGroup,
    TargetState,
)
from probemcp.mcp_server.service import ToolService
from probemcp.safety.policy import PolicyEngine
from probemcp.sessions.manager import SessionManager


class FakeAppSession:
    session_id = "session_01"
    state = TargetState.HALTED

    async def read_registers(self, group: RegisterGroup = RegisterGroup.CORE) -> dict[str, str]:
        return {"pc": "0x08001234", "sp": "0x20000000"}

    async def read_memory(
        self,
        *,
        address: str,
        length: int,
        width: int = 1,
        timeout_ms: int = 3000,
    ) -> ReadMemoryData:
        return ReadMemoryData(address=address, length=length, width=width, data_hex="00000000")


def make_app_service() -> ToolService:
    manager = SessionManager()
    manager.add(FakeAppSession())  # type: ignore[arg-type]
    return ToolService(sessions=manager, policy=PolicyEngine())


@pytest.mark.asyncio
async def test_create_app_registers_metadata_tool() -> None:
    app = create_app()

    tools = await app.list_tools()

    assert any(tool.name == "list_supported_tools" for tool in tools)
    assert any(tool.name == "read_registers" for tool in tools)
    assert any(tool.name == "debug_snapshot" for tool in tools)
    assert all(tool.name != "execute_gdb_command" for tool in tools)


@pytest.mark.asyncio
async def test_list_supported_tools_returns_safe_tool_metadata() -> None:
    app = create_app()

    result = await app.call_tool("list_supported_tools", {})

    assert result
    assert "execute_gdb_command" not in str(result)
    assert "read_registers" in str(result)


@pytest.mark.asyncio
async def test_registered_tool_returns_structured_error_without_session() -> None:
    app = create_app()

    result = await app.call_tool("read_registers", {"session_id": "missing"})

    assert "SESSION_NOT_FOUND" in str(result)


@pytest.mark.asyncio
async def test_connect_target_tool_returns_factory_error_by_default() -> None:
    app = create_app()

    result = await app.call_tool(
        "connect_target",
        {
            "backend": "generic-remote",
            "endpoint": "localhost:3333",
            "confirmation_token": "confirmed",
        },
    )

    assert "SESSION_FACTORY_UNAVAILABLE" in str(result)


@pytest.mark.asyncio
async def test_app_exposes_readonly_resources(tmp_path) -> None:
    service = make_app_service()
    app = create_app(service=service)

    sessions = await app.read_resource("probemcp://sessions")

    assert "session_01" in str(sessions)


@pytest.mark.asyncio
async def test_app_registered_high_level_tools(tmp_path) -> None:
    service = make_app_service()
    app = create_app(service=service)
    snapshot_result = await service.debug_snapshot(DebugSnapshotRequest(session_id="session_01"))
    assert snapshot_result.data is not None

    explain = await app.call_tool(
        "explain_current_state",
        {"snapshot_id": snapshot_result.data.snapshot_id},
    )
    suggest = await app.call_tool(
        "suggest_next_debug_steps",
        {"snapshot_id": snapshot_result.data.snapshot_id, "goal": "triage fault"},
    )

    assert "Target state is halted" in str(explain)
    assert "Analyze the current fault registers" in str(suggest)

import pytest

from probemcp.mcp_server.app import create_app


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

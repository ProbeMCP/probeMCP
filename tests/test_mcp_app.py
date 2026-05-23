import pytest

from probemcp.mcp_server.app import create_app


@pytest.mark.asyncio
async def test_create_app_registers_metadata_tool() -> None:
    app = create_app()

    tools = await app.list_tools()

    assert any(tool.name == "list_supported_tools" for tool in tools)


@pytest.mark.asyncio
async def test_list_supported_tools_returns_safe_tool_metadata() -> None:
    app = create_app()

    result = await app.call_tool("list_supported_tools", {})

    assert result
    assert "execute_gdb_command" not in str(result)
    assert "read_registers" in str(result)

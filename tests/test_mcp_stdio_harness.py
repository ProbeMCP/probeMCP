import sys
from datetime import timedelta

import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.mark.asyncio
async def test_stdio_mcp_client_harness_lists_tools_resources_and_errors() -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from probemcp.cli import main; main()", "serve"],
    )

    async with stdio_client(server) as (read_stream, write_stream), ClientSession(
        read_stream,
        write_stream,
        read_timeout_seconds=timedelta(seconds=10),
    ) as session:
        await session.initialize()

        tools = await session.list_tools()
        tool_names = {tool.name for tool in tools.tools}
        assert "read_registers" in tool_names
        assert "execute_gdb_command" not in tool_names

        resources = await session.list_resources()
        resource_uris = {str(resource.uri) for resource in resources.resources}
        assert "probemcp://sessions" in resource_uris
        assert "probemcp://audit" in resource_uris

        schemas = await session.read_resource("probemcp://schema")
        assert "json_schemas" in str(schemas.contents)

        result = await session.call_tool("read_registers", {"session_id": "missing"})
        assert "SESSION_NOT_FOUND" in str(result.content)

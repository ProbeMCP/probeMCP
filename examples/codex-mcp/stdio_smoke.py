#!/usr/bin/env python3
"""ProbeMCP stdio smoke test for Codex-style MCP integration cases."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

DEFAULT_SERVER_ARGS = ["-c", "from probemcp.cli import main; main()", "serve"]
RAW_GDB_TOOL = "execute_gdb_command"


async def run_smoke(
    *,
    server_command: str,
    server_args: Sequence[str],
    timeout_seconds: int,
) -> dict[str, Any]:
    """Run safe MCP client checks against a ProbeMCP stdio server."""

    server = StdioServerParameters(command=server_command, args=list(server_args))

    async with stdio_client(server) as (read_stream, write_stream), ClientSession(
        read_stream,
        write_stream,
        read_timeout_seconds=timedelta(seconds=timeout_seconds),
    ) as session:
        await session.initialize()

        tools = await session.list_tools()
        tool_names = sorted(tool.name for tool in tools.tools)

        resources = await session.list_resources()
        resource_uris = sorted(str(resource.uri) for resource in resources.resources)

        schema = await session.read_resource("probemcp://schema")
        missing_session = await session.call_tool(
            "read_registers",
            {"session_id": "missing"},
        )

    missing_session_text = str(missing_session.content)

    return {
        "tool_count": len(tool_names),
        "tools": tool_names,
        "raw_gdb_tool_exposed": RAW_GDB_TOOL in tool_names,
        "resources": resource_uris,
        "schema_has_json_schemas": "json_schemas" in str(schema.contents),
        "missing_session_has_error": "SESSION_NOT_FOUND" in missing_session_text,
        "missing_session_text": missing_session_text,
    }


async def async_main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a ProbeMCP MCP stdio smoke test matching Codex integration cases."
    )
    parser.add_argument(
        "--server-command",
        default=sys.executable,
        help="Executable used to start the ProbeMCP MCP server.",
    )
    parser.add_argument(
        "--server-arg",
        dest="server_args",
        action="append",
        default=None,
        help="Append one argument for the server command. Repeat for multiple arguments.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=10,
        help="MCP read timeout for each operation.",
    )
    args = parser.parse_args(argv)

    result = await run_smoke(
        server_command=args.server_command,
        server_args=args.server_args or DEFAULT_SERVER_ARGS,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))

    if result["raw_gdb_tool_exposed"]:
        return 1
    if not result["schema_has_json_schemas"]:
        return 1
    if not result["missing_session_has_error"]:
        return 1
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())

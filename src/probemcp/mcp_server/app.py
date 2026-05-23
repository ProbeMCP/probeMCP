"""FastMCP application factory."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from probemcp.mcp_server.tools import ToolRegistry


def create_app(registry: ToolRegistry | None = None) -> FastMCP:
    """Create the ProbeMCP FastMCP server.

    v0.1 exposes metadata first; execution tools are wired once the session
    manager is connected to real or fake GDB/MI controllers.
    """

    tool_registry = registry or ToolRegistry()
    app = FastMCP(
        "ProbeMCP",
        instructions=(
            "Safe local-first embedded debugging through structured GDB/MI tools. "
            "Arbitrary GDB and shell command execution are intentionally not exposed."
        ),
    )

    @app.tool()
    async def list_supported_tools() -> list[dict[str, object]]:
        """List ProbeMCP tool contracts and safety requirements."""

        return [
            {
                "name": tool.name,
                "operation": tool.operation.value,
                "permission": tool.permission.value,
                "timeout_ms": tool.timeout_ms,
                "description": tool.description,
            }
            for tool in tool_registry.list()
        ]

    return app

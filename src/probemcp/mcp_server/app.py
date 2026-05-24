"""FastMCP application factory."""

from __future__ import annotations

import json
from typing import Literal

from mcp.server.fastmcp import FastMCP

from probemcp.mcp_server.schemas import (
    AnalyzeFaultRequest,
    BackendKind,
    BreakpointLocation,
    BreakpointType,
    ClearBreakpointRequest,
    CompareSnapshotsRequest,
    ConnectTargetRequest,
    DebugSnapshotRequest,
    DetailLevel,
    DisconnectTargetRequest,
    ExplainCurrentStateRequest,
    HaltPolicy,
    HaltRequest,
    InspectPeripheralRequest,
    ReadMemoryRequest,
    ReadRegistersRequest,
    RegisterGroup,
    ResetMode,
    ResetTargetRequest,
    ResumeRequest,
    SetBreakpointRequest,
    StepInstructionRequest,
    SuggestNextDebugStepsRequest,
    WriteMemoryRequest,
)
from probemcp.mcp_server.service import ToolService
from probemcp.mcp_server.tools import ToolRegistry
from probemcp.safety.policy import PolicyEngine
from probemcp.schemas_export import export_public_json_schemas
from probemcp.sessions.manager import SessionManager


def create_app(
    registry: ToolRegistry | None = None,
    service: ToolService | None = None,
) -> FastMCP:
    """Create the ProbeMCP FastMCP server."""

    tool_registry = registry or ToolRegistry()
    tool_service = service or ToolService(sessions=SessionManager(), policy=PolicyEngine())
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

    @app.resource(
        "probemcp://sessions",
        name="sessions",
        description="Active ProbeMCP debug sessions.",
        mime_type="application/json",
    )
    def sessions_resource() -> str:
        """Expose active session summaries as a read-only MCP resource."""

        return json.dumps({"sessions": tool_service.list_session_summaries()})

    @app.resource(
        "probemcp://snapshots/{snapshot_id}",
        name="snapshot",
        description="Captured ProbeMCP debug snapshot.",
        mime_type="application/json",
    )
    def snapshot_resource(snapshot_id: str) -> str:
        """Expose captured snapshots as read-only MCP resources."""

        snapshot = tool_service.get_snapshot(snapshot_id)
        if snapshot is None:
            return json.dumps({"error": "SNAPSHOT_NOT_FOUND", "snapshot_id": snapshot_id})
        return snapshot.model_dump_json()

    @app.resource(
        "probemcp://audit",
        name="audit",
        description="Local ProbeMCP audit events.",
        mime_type="application/json",
    )
    def audit_resource() -> str:
        """Expose local audit events as a read-only MCP resource."""

        return json.dumps({"events": tool_service.list_audit_events()})

    @app.resource(
        "probemcp://schema",
        name="schema",
        description="ProbeMCP public schema metadata.",
        mime_type="application/json",
    )
    def schema_resource() -> str:
        """Expose public schema metadata for MCP clients."""

        return json.dumps(
            {
                "schema_version": "0.1",
                "tools": [tool.name for tool in tool_registry.list()],
                "resources": [
                    "probemcp://sessions",
                    "probemcp://snapshots/{snapshot_id}",
                    "probemcp://audit",
                    "probemcp://schema",
                ],
                "json_schemas": export_public_json_schemas(),
            }
        )

    @app.tool()
    async def connect_target(
        backend: str,
        endpoint: str | None = None,
        gdb_path: str = "arm-none-eabi-gdb",
        elf_path: str | None = None,
        profile: str = "cortex-m",
        timeout_ms: int = 30_000,
        confirmation_token: str | None = None,
    ) -> dict[str, object]:
        """Connect to a GDB-compatible target."""

        result = await tool_service.connect_target(
            ConnectTargetRequest(
                backend=BackendKind(backend),
                endpoint=endpoint,
                gdb_path=gdb_path,
                elf_path=elf_path,
                profile=profile,
                timeout_ms=timeout_ms,
            ),
            confirmation_token=confirmation_token,
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def disconnect_target(
        session_id: str,
        kill_backend: bool = False,
        timeout_ms: int = 5000,
        confirmation_token: str | None = None,
    ) -> dict[str, object]:
        """Disconnect from a target."""

        result = await tool_service.disconnect_target(
            DisconnectTargetRequest(
                session_id=session_id,
                kill_backend=kill_backend,
                timeout_ms=timeout_ms,
            ),
            confirmation_token=confirmation_token,
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def halt(
        session_id: str,
        timeout_ms: int = 2000,
        confirmation_token: str | None = None,
    ) -> dict[str, object]:
        """Interrupt target execution."""

        result = await tool_service.halt(
            HaltRequest(session_id=session_id, timeout_ms=timeout_ms),
            confirmation_token=confirmation_token,
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def resume(
        session_id: str,
        max_run_ms: int,
        auto_interrupt: bool = True,
        confirmation_token: str | None = None,
    ) -> dict[str, object]:
        """Resume target execution with a bounded timeout."""

        result = await tool_service.resume(
            ResumeRequest(
                session_id=session_id,
                max_run_ms=max_run_ms,
                auto_interrupt=auto_interrupt,
            ),
            confirmation_token=confirmation_token,
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def step_instruction(
        session_id: str,
        count: int = 1,
        timeout_ms: int = 5000,
        confirmation_token: str | None = None,
    ) -> dict[str, object]:
        """Step one or more target instructions."""

        result = await tool_service.step_instruction(
            StepInstructionRequest(
                session_id=session_id,
                count=count,
                timeout_ms=timeout_ms,
            ),
            confirmation_token=confirmation_token,
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def reset_target(
        session_id: str,
        mode: Literal["halt", "run"] = "halt",
        timeout_ms: int = 10_000,
        confirmation_token: str | None = None,
    ) -> dict[str, object]:
        """Reset the target through the active backend policy."""

        result = await tool_service.reset_target(
            ResetTargetRequest(
                session_id=session_id,
                mode=ResetMode(mode),
                timeout_ms=timeout_ms,
            ),
            confirmation_token=confirmation_token,
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def read_registers(
        session_id: str,
        group: Literal["core", "fault", "all"] = "core",
    ) -> dict[str, object]:
        """Read target registers."""

        result = await tool_service.read_registers(
            ReadRegistersRequest(session_id=session_id, group=RegisterGroup(group))
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def read_memory(
        session_id: str,
        address: str,
        length: int,
        width: int = 1,
        timeout_ms: int = 3000,
    ) -> dict[str, object]:
        """Read target memory bytes."""

        result = await tool_service.read_memory(
            ReadMemoryRequest(
                session_id=session_id,
                address=address,
                length=length,
                width=width,
                timeout_ms=timeout_ms,
            )
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def write_memory(
        session_id: str,
        address: str,
        data_hex: str,
        expected_old_hex: str | None = None,
        timeout_ms: int = 3000,
        confirmation_token: str | None = None,
    ) -> dict[str, object]:
        """Write target memory when explicitly enabled by full-control policy."""

        result = await tool_service.write_memory(
            WriteMemoryRequest(
                session_id=session_id,
                address=address,
                data_hex=data_hex,
                expected_old_hex=expected_old_hex,
                timeout_ms=timeout_ms,
            ),
            confirmation_token=confirmation_token,
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def set_breakpoint(
        session_id: str,
        location_kind: Literal["symbol", "address", "file-line"],
        location_value: str,
        breakpoint_type: Literal["hardware", "software"] = "hardware",
        temporary: bool = False,
        timeout_ms: int = 3000,
        confirmation_token: str | None = None,
    ) -> dict[str, object]:
        """Set a target breakpoint."""

        result = await tool_service.set_breakpoint(
            SetBreakpointRequest(
                session_id=session_id,
                location=BreakpointLocation(kind=location_kind, value=location_value),
                type=BreakpointType(breakpoint_type),
                temporary=temporary,
                timeout_ms=timeout_ms,
            ),
            confirmation_token=confirmation_token,
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def clear_breakpoint(
        session_id: str,
        breakpoint_id: str,
        timeout_ms: int = 3000,
        confirmation_token: str | None = None,
    ) -> dict[str, object]:
        """Clear a target breakpoint."""

        result = await tool_service.clear_breakpoint(
            ClearBreakpointRequest(
                session_id=session_id,
                breakpoint_id=breakpoint_id,
                timeout_ms=timeout_ms,
            ),
            confirmation_token=confirmation_token,
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def debug_snapshot(
        session_id: str,
        halt_policy: Literal[
            "require_already_halted",
            "halt_if_running",
        ] = "require_already_halted",
        include_core_registers: bool = True,
        include_fault_registers: bool = True,
        include_stack: bool = False,
        stack_bytes: int = 128,
        include_symbol_context: bool = True,
        disassembly_instructions: int = 6,
    ) -> dict[str, object]:
        """Capture a structured debug snapshot."""

        result = await tool_service.debug_snapshot(
            DebugSnapshotRequest(
                session_id=session_id,
                halt_policy=HaltPolicy(halt_policy),
                include_core_registers=include_core_registers,
                include_fault_registers=include_fault_registers,
                include_stack=include_stack,
                stack_bytes=stack_bytes,
                include_symbol_context=include_symbol_context,
                disassembly_instructions=disassembly_instructions,
            )
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def analyze_fault(
        session_id: str | None = None,
        snapshot_id: str | None = None,
    ) -> dict[str, object]:
        """Analyze Cortex-M fault state from a snapshot."""

        result = await tool_service.analyze_fault(
            AnalyzeFaultRequest(session_id=session_id, snapshot_id=snapshot_id)
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def inspect_peripheral(
        session_id: str,
        svd_path: str,
        peripheral: str,
        registers: list[str] | None = None,
        timeout_ms: int = 3000,
    ) -> dict[str, object]:
        """Decode peripheral registers using a local SVD file."""

        result = await tool_service.inspect_peripheral(
            InspectPeripheralRequest(
                session_id=session_id,
                svd_path=svd_path,
                peripheral=peripheral,
                registers=registers,
                timeout_ms=timeout_ms,
            )
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def compare_snapshots(
        before_snapshot_id: str,
        after_snapshot_id: str,
        include_memory_diffs: bool = False,
    ) -> dict[str, object]:
        """Compare two captured snapshots."""

        result = await tool_service.compare_snapshots(
            CompareSnapshotsRequest(
                before_snapshot_id=before_snapshot_id,
                after_snapshot_id=after_snapshot_id,
                include_memory_diffs=include_memory_diffs,
            )
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def explain_current_state(
        session_id: str | None = None,
        snapshot_id: str | None = None,
        detail_level: Literal["brief", "normal", "verbose"] = "normal",
    ) -> dict[str, object]:
        """Explain target state from a snapshot."""

        result = await tool_service.explain_current_state(
            ExplainCurrentStateRequest(
                session_id=session_id,
                snapshot_id=snapshot_id,
                detail_level=DetailLevel(detail_level),
            )
        )
        return result.model_dump(mode="json")

    @app.tool()
    async def suggest_next_debug_steps(
        goal: str,
        session_id: str | None = None,
        snapshot_id: str | None = None,
    ) -> dict[str, object]:
        """Suggest conservative next debugging steps."""

        result = await tool_service.suggest_next_debug_steps(
            SuggestNextDebugStepsRequest(
                session_id=session_id,
                snapshot_id=snapshot_id,
                goal=goal,
            )
        )
        return result.model_dump(mode="json")

    return app

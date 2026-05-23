"""FastMCP application factory."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP

from probemcp.mcp_server.schemas import (
    AnalyzeFaultRequest,
    BackendKind,
    BreakpointLocation,
    BreakpointType,
    ClearBreakpointRequest,
    ConnectTargetRequest,
    DebugSnapshotRequest,
    DisconnectTargetRequest,
    HaltPolicy,
    HaltRequest,
    ReadMemoryRequest,
    ReadRegistersRequest,
    RegisterGroup,
    ResetMode,
    ResetTargetRequest,
    ResumeRequest,
    SetBreakpointRequest,
    StepInstructionRequest,
)
from probemcp.mcp_server.service import ToolService
from probemcp.mcp_server.tools import ToolRegistry
from probemcp.safety.policy import PolicyEngine
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

    return app

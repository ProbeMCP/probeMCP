"""Debug session orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from probemcp.backends.base import BackendAdapter, BackendConnection
from probemcp.debug.state import DebugSessionStateMachine
from probemcp.mcp_server.schemas import (
    BreakpointData,
    BreakpointLocation,
    BreakpointType,
    ClearBreakpointData,
    ConnectTargetRequest,
    HaltData,
    ReadMemoryData,
    RegisterGroup,
    ResetMode,
    StepInstructionData,
    TargetState,
)
from probemcp.mi.commands import (
    break_delete,
    break_insert,
    data_list_register_values,
    data_read_memory_bytes,
    exec_continue,
    exec_interrupt,
    exec_step_instruction,
    gdb_exit,
)
from probemcp.mi.controller import MIController, MITimeoutError
from probemcp.mi.records import MIRecord, MIValue
from probemcp.targets import normalize_registers


class DebugSessionError(RuntimeError):
    """Raised when a debug session operation fails."""


@dataclass(slots=True)
class DebugSession:
    """One active target debugging session."""

    controller: MIController
    backend: BackendAdapter
    session_id: str = field(default_factory=lambda: f"session_{uuid4().hex}")
    state_machine: DebugSessionStateMachine = field(default_factory=DebugSessionStateMachine)
    connection: BackendConnection | None = None

    @property
    def state(self) -> TargetState:
        """Return current target state."""

        return self.state_machine.state

    async def connect(self, request: ConnectTargetRequest) -> BackendConnection:
        """Connect the session to a target through its backend adapter."""

        if request.endpoint is None:
            raise DebugSessionError("connect_target requires an endpoint for this backend")

        self.state_machine.transition(TargetState.CONNECTING, "connect requested")
        connection = await self.backend.connect(
            self.controller,
            endpoint=request.endpoint,
            profile=request.profile,
            timeout_ms=request.timeout_ms,
        )
        self.connection = connection
        self.state_machine.transition(connection.state, "backend connected")
        return connection

    async def disconnect(self, *, timeout_ms: int = 5000) -> None:
        """Disconnect by asking GDB to exit, then closing the transport."""

        await self.controller.execute(gdb_exit(), timeout_ms=timeout_ms)
        await self.controller.close()
        self.state_machine.transition(TargetState.DISCONNECTED, "disconnect requested")

    async def halt(self, *, timeout_ms: int = 2000) -> HaltData:
        """Interrupt a running target."""

        result = await self.controller.execute(exec_interrupt(), timeout_ms=timeout_ms)
        pc = _first_frame_addr(result.async_records)
        self.state_machine.transition(TargetState.HALTED, "target interrupted")
        return HaltData(stop_reason=_first_stop_reason(result.async_records), pc=pc)

    async def resume(self, *, max_run_ms: int, auto_interrupt: bool = True) -> TargetState:
        """Resume target execution with a bounded timeout policy."""

        try:
            await self.controller.execute(exec_continue(), timeout_ms=max_run_ms)
        except MITimeoutError:
            if auto_interrupt:
                await self.halt(timeout_ms=2000)
                return self.state
            self.state_machine.transition(TargetState.UNKNOWN, "resume timed out")
            return self.state

        self.state_machine.transition(TargetState.RUNNING, "target resumed")
        return self.state

    async def step_instruction(self, *, timeout_ms: int = 5000) -> StepInstructionData:
        """Step one instruction."""

        result = await self.controller.execute(exec_step_instruction(), timeout_ms=timeout_ms)
        pc = _first_frame_addr(result.async_records)
        self.state_machine.transition(TargetState.HALTED, "instruction stepped")
        return StepInstructionData(pc=pc)

    async def read_registers(self, group: RegisterGroup = RegisterGroup.CORE) -> dict[str, str]:
        """Read register values from GDB."""

        result = await self.controller.execute(data_list_register_values(), timeout_ms=3000)
        registers = _parse_register_values(result.result_record)
        profile = self.connection.profile if self.connection is not None else "cortex-m"
        registers = normalize_registers(registers, profile=profile)
        if group == RegisterGroup.CORE:
            return registers
        return registers

    async def read_memory(
        self,
        *,
        address: str,
        length: int,
        width: int = 1,
        timeout_ms: int = 3000,
    ) -> ReadMemoryData:
        """Read memory bytes."""

        result = await self.controller.execute(
            data_read_memory_bytes(address, length),
            timeout_ms=timeout_ms,
        )
        data_hex = _parse_memory_contents(result.result_record)
        return ReadMemoryData(address=address, length=length, width=width, data_hex=data_hex)

    async def set_breakpoint(
        self,
        *,
        location: BreakpointLocation,
        breakpoint_type: BreakpointType,
        temporary: bool,
        timeout_ms: int = 3000,
    ) -> BreakpointData:
        """Set a breakpoint."""

        result = await self.controller.execute(
            break_insert(location.value, breakpoint_type=breakpoint_type, temporary=temporary),
            timeout_ms=timeout_ms,
        )
        breakpoint_id = _parse_breakpoint_id(result.result_record)
        return BreakpointData(
            breakpoint_id=breakpoint_id,
            location=location,
            type=breakpoint_type,
            temporary=temporary,
        )

    async def clear_breakpoint(
        self,
        *,
        breakpoint_id: str,
        timeout_ms: int = 3000,
    ) -> ClearBreakpointData:
        """Clear a breakpoint."""

        await self.controller.execute(break_delete(breakpoint_id), timeout_ms=timeout_ms)
        return ClearBreakpointData(breakpoint_id=breakpoint_id, removed=True)

    async def reset_target(self, *, mode: ResetMode, timeout_ms: int = 10_000) -> TargetState:
        """Reset the target through a backend-specific allowlisted path when available."""

        resetter = getattr(self.backend, "reset_target", None)
        if resetter is not None:
            state = await resetter(self.controller, mode=mode, timeout_ms=timeout_ms)
            self.state_machine.transition(state, f"backend reset {mode.value} requested")
            return self.state

        if mode == ResetMode.HALT:
            self.state_machine.transition(TargetState.HALTED, "reset halt requested")
        else:
            self.state_machine.transition(TargetState.RUNNING, "reset run requested")
        return self.state


def _parse_register_values(record: MIRecord) -> dict[str, str]:
    raw_values = record.results.get("register-values")
    registers: dict[str, str] = {}
    if not isinstance(raw_values, list):
        return registers

    for item in raw_values:
        if isinstance(item, dict):
            data = item.get("value")
            number = item.get("number")
            if isinstance(data, dict):
                number = data.get("number")
                value = data.get("value")
            else:
                value = data
            if isinstance(number, str) and isinstance(value, str):
                registers[number] = value
    return registers


def _parse_memory_contents(record: MIRecord) -> str:
    memory = record.results.get("memory")
    if isinstance(memory, list) and memory:
        first = memory[0]
        if isinstance(first, dict):
            block = first.get("memory")
            contents = block.get("contents") if isinstance(block, dict) else first.get("contents")
            if isinstance(contents, str):
                return contents

    contents = record.results.get("contents")
    if isinstance(contents, str):
        return contents
    return ""


def _parse_breakpoint_id(record: MIRecord) -> str:
    breakpoint_data = record.results.get("bkpt")
    if isinstance(breakpoint_data, dict):
        number = breakpoint_data.get("number")
        if isinstance(number, str):
            return number
    return "unknown"


def _first_stop_reason(records: tuple[MIRecord, ...]) -> str | None:
    for record in records:
        reason = record.results.get("reason")
        if isinstance(reason, str):
            return reason
    return None


def _first_frame_addr(records: tuple[MIRecord, ...]) -> str | None:
    for record in records:
        frame = record.results.get("frame")
        if isinstance(frame, dict):
            addr: MIValue | None = frame.get("addr")
            if isinstance(addr, str):
                return addr
    return None

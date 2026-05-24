from collections import deque
from typing import cast

import pytest

from probemcp.backends.generic_remote import GenericRemoteBackend
from probemcp.debug.session import DebugSession, DebugSessionError
from probemcp.mcp_server.schemas import (
    BackendKind,
    BreakpointLocation,
    BreakpointType,
    ConnectTargetRequest,
    RegisterGroup,
    ResetMode,
    TargetState,
)
from probemcp.mi.commands import MICommand
from probemcp.mi.controller import MICommandResult, MIController, MITimeoutError
from probemcp.mi.parser import parse_mi_record
from probemcp.mi.records import MIRecord


class FakeController:
    def __init__(self, result_lines: list[str], *, timeout_on: str | None = None) -> None:
        self.result_lines = deque(result_lines)
        self.commands: list[str] = []
        self.closed = False
        self.timeout_on = timeout_on

    async def execute(self, command: MICommand, *, timeout_ms: int = 3000) -> MICommandResult:
        serialized = command.serialize()
        self.commands.append(serialized)
        if self.timeout_on is not None and serialized.startswith(f"-{self.timeout_on}"):
            raise MITimeoutError("timeout")
        line = self.result_lines.popleft()
        record = parse_mi_record(line)
        if not isinstance(record, MIRecord):
            raise AssertionError("expected MI result record")
        return MICommandResult(result_record=record)

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_generic_remote_backend_connects_with_target_select() -> None:
    controller = FakeController(["1^done"])

    connection = await GenericRemoteBackend().connect(
        cast(MIController, controller),
        endpoint="localhost:3333",
        profile="cortex-m",
        timeout_ms=1000,
    )

    assert controller.commands == ["-target-select extended-remote localhost:3333"]
    assert connection.backend == BackendKind.GENERIC_REMOTE
    assert connection.endpoint == "localhost:3333"


@pytest.mark.asyncio
async def test_debug_session_connect_requires_endpoint() -> None:
    session = DebugSession(
        controller=cast(MIController, FakeController([])),
        backend=GenericRemoteBackend(),
    )

    with pytest.raises(DebugSessionError, match="endpoint"):
        await session.connect(ConnectTargetRequest(backend=BackendKind.GENERIC_REMOTE))


@pytest.mark.asyncio
async def test_debug_session_connect_and_disconnect_lifecycle() -> None:
    controller = FakeController(["1^done", "2^done"])
    session = DebugSession(
        controller=cast(MIController, controller),
        backend=GenericRemoteBackend(),
    )

    await session.connect(
        ConnectTargetRequest(
            backend=BackendKind.GENERIC_REMOTE,
            endpoint="localhost:3333",
        )
    )
    await session.disconnect()

    assert controller.commands == [
        "-target-select extended-remote localhost:3333",
        "-gdb-exit",
    ]
    assert controller.closed
    assert session.state == TargetState.DISCONNECTED


@pytest.mark.asyncio
async def test_debug_session_reads_registers_and_memory() -> None:
    controller = FakeController(
        [
            '1^done,register-values=[{number="15",value="0x08001234"}]',
            '2^done,memory=[{begin="0x20000000",offset="0x0",end="0x20000004",contents="01020304"}]',
        ]
    )
    session = DebugSession(
        controller=cast(MIController, controller),
        backend=GenericRemoteBackend(),
    )

    registers = await session.read_registers(RegisterGroup.CORE)
    memory = await session.read_memory(address="0x20000000", length=4)

    assert registers == {"15": "0x08001234", "pc": "0x08001234"}
    assert memory.data_hex == "01020304"


@pytest.mark.asyncio
async def test_debug_session_breakpoint_flow() -> None:
    controller = FakeController(['1^done,bkpt={number="1"}', "2^done"])
    session = DebugSession(
        controller=cast(MIController, controller),
        backend=GenericRemoteBackend(),
    )

    breakpoint = await session.set_breakpoint(
        location=BreakpointLocation(kind="symbol", value="main"),
        breakpoint_type=BreakpointType.HARDWARE,
        temporary=False,
    )
    cleared = await session.clear_breakpoint(breakpoint_id=breakpoint.breakpoint_id)

    assert breakpoint.breakpoint_id == "1"
    assert cleared.removed
    assert controller.commands == ["-break-insert -h main", "-break-delete 1"]


@pytest.mark.asyncio
async def test_debug_session_resume_timeout_auto_interrupts() -> None:
    controller = FakeController(["1^done"], timeout_on="exec-continue")
    session = DebugSession(
        controller=cast(MIController, controller),
        backend=GenericRemoteBackend(),
    )
    session.state_machine.transition(TargetState.CONNECTING, "test")
    session.state_machine.transition(TargetState.HALTED, "test")

    state = await session.resume(max_run_ms=1, auto_interrupt=True)

    assert state == TargetState.HALTED
    assert controller.commands == ["-exec-continue", "-exec-interrupt"]


@pytest.mark.asyncio
async def test_debug_session_reset_placeholder_updates_state() -> None:
    session = DebugSession(
        controller=cast(MIController, FakeController([])),
        backend=GenericRemoteBackend(),
    )
    session.state_machine.transition(TargetState.CONNECTING, "test")
    session.state_machine.transition(TargetState.HALTED, "test")

    assert await session.reset_target(mode=ResetMode.RUN) == TargetState.RUNNING

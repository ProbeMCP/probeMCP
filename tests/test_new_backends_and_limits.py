from collections import deque
from typing import cast

import pytest

from probemcp.backends.factory import create_backend
from probemcp.backends.openocd import OpenOCDBackend
from probemcp.backends.qemu import QemuBackend
from probemcp.backends.vendor import jlink_backend, pyocd_backend
from probemcp.mcp_server.schemas import BackendKind, ResetMode, TargetState
from probemcp.mi.commands import MICommand
from probemcp.mi.controller import MICommandResult, MIController
from probemcp.mi.parser import parse_mi_record
from probemcp.mi.records import MIRecord
from probemcp.safety.limits import ResourceLimits
from probemcp.targets import infer_architecture, normalize_registers


class FakeController:
    def __init__(self, lines: list[str]) -> None:
        self.lines = deque(lines)
        self.commands: list[str] = []

    async def execute(self, command: MICommand, *, timeout_ms: int = 3000) -> MICommandResult:
        self.commands.append(command.serialize())
        record = parse_mi_record(self.lines.popleft())
        assert isinstance(record, MIRecord)
        return MICommandResult(result_record=record)


@pytest.mark.asyncio
async def test_qemu_backend_attaches_and_sets_architecture() -> None:
    controller = FakeController(["1^done"])

    connection = await QemuBackend().connect(
        cast(MIController, controller),
        endpoint="localhost:1234",
        profile="cortex-m",
        timeout_ms=1000,
    )

    assert connection.backend == BackendKind.QEMU
    assert connection.architecture == "arm"
    assert controller.commands == ["-target-select extended-remote localhost:1234"]


@pytest.mark.asyncio
async def test_openocd_backend_uses_allowlisted_reset_monitor_command() -> None:
    controller = FakeController(["1^done", "2^done"])
    backend = OpenOCDBackend()
    await backend.connect(
        cast(MIController, controller),
        endpoint="localhost:3333",
        profile="cortex-m",
        timeout_ms=1000,
    )

    state = await backend.reset_target(
        cast(MIController, controller),
        mode=ResetMode.HALT,
        timeout_ms=1000,
    )

    assert state == TargetState.HALTED
    assert controller.commands[-1] == '-interpreter-exec console "monitor reset halt"'


@pytest.mark.asyncio
async def test_vendor_backends_are_attach_only() -> None:
    controller = FakeController(["1^done", "2^done"])

    jlink = await jlink_backend().connect(
        cast(MIController, controller),
        endpoint="localhost:2331",
        profile="cortex-m",
        timeout_ms=1000,
    )
    pyocd = await pyocd_backend().connect(
        cast(MIController, controller),
        endpoint="localhost:3333",
        profile="cortex-m",
        timeout_ms=1000,
    )

    assert jlink.backend == BackendKind.JLINK
    assert pyocd.backend == BackendKind.PYOCD


def test_backend_factory_returns_supported_adapters() -> None:
    assert create_backend(BackendKind.GENERIC_REMOTE).kind == BackendKind.GENERIC_REMOTE
    assert create_backend(BackendKind.QEMU).kind == BackendKind.QEMU
    assert create_backend(BackendKind.OPENOCD).kind == BackendKind.OPENOCD
    assert create_backend(BackendKind.JLINK).kind == BackendKind.JLINK
    assert create_backend(BackendKind.PYOCD).kind == BackendKind.PYOCD


def test_register_normalization_and_architecture_inference() -> None:
    normalized = normalize_registers({"15": "0x08000000", "16": "0x01000000"})

    assert normalized["pc"] == "0x08000000"
    assert normalized["xpsr"] == "0x01000000"
    assert infer_architecture(BackendKind.QEMU, "riscv32") == "riscv"


def test_resource_limits_return_structured_errors() -> None:
    limits = ResourceLimits(max_sessions=1, max_memory_read_bytes=8)

    assert limits.check_session_count(0) is None
    assert limits.check_session_count(1).code == "RESOURCE_LIMIT_EXCEEDED"
    assert limits.check_memory_read(4) is None
    assert limits.check_memory_read(9).code == "RESOURCE_LIMIT_EXCEEDED"

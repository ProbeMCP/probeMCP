from collections import deque
from typing import cast

import pytest

from probemcp.backends.factory import create_backend
from probemcp.mcp_server.schemas import BackendKind
from probemcp.mi.commands import MICommand
from probemcp.mi.controller import MICommandResult, MIController
from probemcp.mi.parser import parse_mi_record
from probemcp.mi.records import MIRecord


class ConformanceController:
    def __init__(self) -> None:
        self.lines = deque(["1^done"] * 8)
        self.commands: list[str] = []

    async def execute(self, command: MICommand, *, timeout_ms: int = 3000) -> MICommandResult:
        self.commands.append(command.serialize())
        record = parse_mi_record(self.lines.popleft())
        assert isinstance(record, MIRecord)
        return MICommandResult(result_record=record)


@pytest.mark.parametrize(
    "kind",
    [
        BackendKind.GENERIC_REMOTE,
        BackendKind.QEMU,
        BackendKind.OPENOCD,
        BackendKind.JLINK,
        BackendKind.PYOCD,
    ],
)
@pytest.mark.asyncio
async def test_attach_backends_share_connect_contract(kind: BackendKind) -> None:
    backend = create_backend(kind)
    controller = ConformanceController()

    connection = await backend.connect(
        cast(MIController, controller),
        endpoint="localhost:3333",
        profile="cortex-m",
        timeout_ms=1000,
    )

    assert connection.backend == kind
    assert connection.endpoint == "localhost:3333"
    assert controller.commands == ["-target-select extended-remote localhost:3333"]

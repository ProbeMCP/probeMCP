import asyncio
from collections import deque

import pytest

from probemcp.mi.commands import data_list_register_values, exec_continue
from probemcp.mi.controller import MICommandError, MIController, MIControllerError, MITimeoutError
from probemcp.mi.records import MIRecordKind


class FakeMITransport:
    def __init__(self, lines: list[str]) -> None:
        self.lines = deque(lines)
        self.writes: list[str] = []
        self.closed = False

    async def write_line(self, line: str) -> None:
        self.writes.append(line)

    async def read_line(self) -> str:
        if not self.lines:
            await asyncio.sleep(1)
        return self.lines.popleft()

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_controller_correlates_tokenized_result_and_preserves_events() -> None:
    transport = FakeMITransport(
        [
            '~"reading registers\\n"',
            '*running,thread-id="all"',
            '1^done,register-values=[{number="15",value="0x08001234"}]',
        ]
    )
    controller = MIController(transport)

    result = await controller.execute(data_list_register_values(), timeout_ms=100)

    assert transport.writes == ["1-data-list-register-values x"]
    assert result.result_record.record_class == "done"
    assert result.async_records[0].kind == MIRecordKind.EXEC_ASYNC
    assert result.stream_records[0].text == "reading registers\n"


@pytest.mark.asyncio
async def test_controller_raises_on_gdb_error_result() -> None:
    transport = FakeMITransport(['1^error,msg="Cannot access memory"'])
    controller = MIController(transport)

    with pytest.raises(MICommandError, match="Cannot access memory"):
        await controller.execute(data_list_register_values(), timeout_ms=100)


@pytest.mark.asyncio
async def test_controller_serializes_commands_with_lock_and_incrementing_tokens() -> None:
    transport = FakeMITransport(["1^running", "2^running"])
    controller = MIController(transport)

    first = await controller.execute(exec_continue(), timeout_ms=100)
    second = await controller.execute(exec_continue(), timeout_ms=100)

    assert [record.result_record.token for record in (first, second)] == [1, 2]
    assert transport.writes == ["1-exec-continue", "2-exec-continue"]


@pytest.mark.asyncio
async def test_controller_times_out_when_result_never_arrives() -> None:
    transport = FakeMITransport(['*running,thread-id="all"'])
    controller = MIController(transport)

    with pytest.raises(MITimeoutError):
        await controller.execute(exec_continue(), timeout_ms=1)


@pytest.mark.asyncio
async def test_controller_reports_parse_errors_as_controller_errors() -> None:
    transport = FakeMITransport(["1^done,broken"])
    controller = MIController(transport)

    with pytest.raises(MIControllerError):
        await controller.execute(exec_continue(), timeout_ms=100)


@pytest.mark.asyncio
async def test_controller_closes_transport() -> None:
    transport = FakeMITransport([])
    controller = MIController(transport)

    await controller.close()

    assert transport.closed

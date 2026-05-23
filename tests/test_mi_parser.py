import pytest

from probemcp.mi.errors import MIParseError
from probemcp.mi.parser import parse_mi_record
from probemcp.mi.records import MIRecord, MIRecordKind, MIStreamRecord


def test_parse_tokenized_done_record_with_nested_results() -> None:
    record = parse_mi_record('12^done,bkpt={number="1",type="hw breakpoint"},thread-ids=["1","2"]')

    assert isinstance(record, MIRecord)
    assert record.kind == MIRecordKind.RESULT
    assert record.token == 12
    assert record.record_class == "done"
    assert record.results == {
        "bkpt": {"number": "1", "type": "hw breakpoint"},
        "thread-ids": ["1", "2"],
    }


def test_parse_error_record() -> None:
    record = parse_mi_record('7^error,msg="Cannot access memory at address 0x0"')

    assert isinstance(record, MIRecord)
    assert record.kind == MIRecordKind.RESULT
    assert record.record_class == "error"
    assert record.results["msg"] == "Cannot access memory at address 0x0"


def test_parse_exec_async_stopped_record() -> None:
    record = parse_mi_record(
        '*stopped,reason="breakpoint-hit",frame={addr="0x08001234",func="main"}'
    )

    assert isinstance(record, MIRecord)
    assert record.kind == MIRecordKind.EXEC_ASYNC
    assert record.record_class == "stopped"
    assert record.results["reason"] == "breakpoint-hit"
    assert record.results["frame"] == {"addr": "0x08001234", "func": "main"}


def test_parse_exec_async_running_record() -> None:
    record = parse_mi_record('*running,thread-id="all"')

    assert isinstance(record, MIRecord)
    assert record.kind == MIRecordKind.EXEC_ASYNC
    assert record.record_class == "running"
    assert record.results == {"thread-id": "all"}


def test_parse_stream_record_with_escaped_text() -> None:
    record = parse_mi_record('~"hello\\n"')

    assert isinstance(record, MIStreamRecord)
    assert record.kind == MIRecordKind.CONSOLE_STREAM
    assert record.text == "hello\n"


def test_parse_prompt_record() -> None:
    record = parse_mi_record("(gdb)")

    assert isinstance(record, MIRecord)
    assert record.kind == MIRecordKind.PROMPT


def test_invalid_input_raises_structured_parse_error() -> None:
    with pytest.raises(MIParseError) as exc:
        parse_mi_record("^done,broken")

    assert exc.value.line == "^done,broken"
    assert exc.value.position > 0

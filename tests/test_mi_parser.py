import random

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


@pytest.mark.parametrize(
    ("line", "kind"),
    [
        ('@"target output"', MIRecordKind.TARGET_STREAM),
        ('&"log output"', MIRecordKind.LOG_STREAM),
        ('+download,section=".text",size="12"', MIRecordKind.STATUS_ASYNC),
        ('=thread-created,id="1",group-id="i1"', MIRecordKind.NOTIFY_ASYNC),
    ],
)
def test_parse_additional_mi_record_kinds(line: str, kind: MIRecordKind) -> None:
    record = parse_mi_record(line)

    assert record.kind == kind


def test_parse_empty_tuple_and_result_list_entries() -> None:
    record = parse_mi_record('4^done,empty={},values=[name="r0",value="0x1"],bare=abc')

    assert isinstance(record, MIRecord)
    assert record.results["empty"] == {}
    assert record.results["values"] == [{"name": "r0"}, {"value": "0x1"}]
    assert record.results["bare"] == "abc"


@pytest.mark.parametrize("line", ["", "^", '~"unterminated', "1^done,foo=", "1^done,foo=[]x"])
def test_malformed_mi_input_fails_without_hanging(line: str) -> None:
    with pytest.raises(MIParseError):
        parse_mi_record(line)


def test_parse_prompt_record() -> None:
    record = parse_mi_record("(gdb)")

    assert isinstance(record, MIRecord)
    assert record.kind == MIRecordKind.PROMPT


def test_invalid_input_raises_structured_parse_error() -> None:
    with pytest.raises(MIParseError) as exc:
        parse_mi_record("^done,broken")

    assert exc.value.line == "^done,broken"
    assert exc.value.position > 0

@pytest.mark.parametrize(
    "line",
    [
        '1^done,value="unterminated',
        '1^done,tuple={name="r0",value="0x1"',
        '1^done,list=[{name="r0",value="0x1"}',
        '1^done,unicode="µ",trailing',
        '1^done,bytes="\\xff\\xfe",bad={]',
        '*stopped,frame={addr="0x08000000",func="main",args=[name="x",value=]}',
    ],
)
def test_malformed_mi_seed_corpus_fails_with_structured_errors(line: str) -> None:
    with pytest.raises(MIParseError):
        parse_mi_record(line)

def test_deterministic_fuzz_inputs_do_not_escape_parser_errors() -> None:
    rng = random.Random(0)  # noqa: S311 - deterministic parser fuzzing, not security
    alphabet = '^*+=~@&,"{}[]_abcdefghijklmnopqrstuvwxyz0123456789\\'

    for _ in range(500):
        line = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 96)))
        try:
            parse_mi_record(line)
        except MIParseError:
            continue

from probemcp.mcp_server.schemas import BreakpointType
from probemcp.mi.commands import (
    break_delete,
    break_insert,
    data_list_register_values,
    data_read_memory_bytes,
    exec_continue,
    interpreter_exec_console,
    target_select,
)


def test_target_select_serializes_with_token() -> None:
    assert target_select("localhost:3333").serialize(7) == (
        "7-target-select extended-remote localhost:3333"
    )


def test_read_register_and_memory_commands() -> None:
    assert data_list_register_values().serialize(1) == "1-data-list-register-values x"
    assert data_read_memory_bytes("0x20000000", 64).serialize(2) == (
        "2-data-read-memory-bytes 0x20000000 64"
    )


def test_breakpoint_command_quotes_locations_with_spaces() -> None:
    command = break_insert(
        "main file.c:42",
        breakpoint_type=BreakpointType.HARDWARE,
        temporary=True,
    )

    assert command.serialize(3) == '3-break-insert -t -h "main file.c:42"'


def test_continue_and_delete_commands() -> None:
    assert exec_continue().serialize(4) == "4-exec-continue"
    assert break_delete("1").serialize(5) == "5-break-delete 1"


def test_interpreter_exec_console_is_allowlisted() -> None:
    assert interpreter_exec_console("monitor reset halt").serialize(6) == (
        '6-interpreter-exec console "monitor reset halt"'
    )

    try:
        interpreter_exec_console("monitor flash erase")
    except ValueError as exc:
        assert "not allowlisted" in str(exc)
    else:  # pragma: no cover - test guard
        raise AssertionError("expected allowlist rejection")

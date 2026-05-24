"""Allowlisted GDB/MI command builders."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from probemcp.mcp_server.schemas import BreakpointType


class MICommandName(StrEnum):
    """Supported GDB/MI command names."""

    TARGET_SELECT = "target-select"
    GDB_EXIT = "gdb-exit"
    DATA_LIST_REGISTER_VALUES = "data-list-register-values"
    DATA_READ_MEMORY_BYTES = "data-read-memory-bytes"
    DATA_WRITE_MEMORY_BYTES = "data-write-memory-bytes"
    EXEC_INTERRUPT = "exec-interrupt"
    EXEC_CONTINUE = "exec-continue"
    EXEC_STEP_INSTRUCTION = "exec-step-instruction"
    BREAK_INSERT = "break-insert"
    BREAK_DELETE = "break-delete"
    INTERPRETER_EXEC = "interpreter-exec"
    STACK_INFO_FRAME = "stack-info-frame"
    DATA_DISASSEMBLE = "data-disassemble"

ALLOWLISTED_CONSOLE_COMMANDS = frozenset(
    {
        "monitor reset halt",
        "monitor reset run",
    }
)


@dataclass(frozen=True, slots=True)
class MICommand:
    """A single allowlisted MI command without token prefix."""

    name: MICommandName
    args: tuple[str, ...] = ()

    def serialize(self, token: int | None = None) -> str:
        """Serialize command with an optional MI token prefix."""

        prefix = "" if token is None else str(token)
        parts = [f"{prefix}-{self.name.value}"]
        parts.extend(_quote_arg(arg) for arg in self.args)
        return " ".join(parts)


def target_select(endpoint: str, *, extended: bool = True) -> MICommand:
    """Build a target-select command for a GDB remote endpoint."""

    mode = "extended-remote" if extended else "remote"
    return MICommand(MICommandName.TARGET_SELECT, (mode, endpoint))


def gdb_exit() -> MICommand:
    """Build a command that exits GDB."""

    return MICommand(MICommandName.GDB_EXIT)


def data_list_register_values(*, fmt: str = "x") -> MICommand:
    """Build a register read command."""

    return MICommand(MICommandName.DATA_LIST_REGISTER_VALUES, (fmt,))


def data_read_memory_bytes(address: str, length: int) -> MICommand:
    """Build a memory read command."""

    return MICommand(MICommandName.DATA_READ_MEMORY_BYTES, (address, str(length)))


def data_write_memory_bytes(address: str, data_hex: str) -> MICommand:
    """Build a memory write command."""

    return MICommand(MICommandName.DATA_WRITE_MEMORY_BYTES, (address, data_hex))

def stack_info_frame() -> MICommand:
    """Build a current-frame symbol/source lookup command."""

    return MICommand(MICommandName.STACK_INFO_FRAME)

def data_disassemble(address: str, *, instruction_count: int = 6) -> MICommand:
    """Build a bounded disassembly command around an address."""

    return MICommand(
        MICommandName.DATA_DISASSEMBLE,
        ("-a", address, "-n", str(instruction_count), "--", "0"),
    )


def exec_interrupt() -> MICommand:
    """Build an interrupt command."""

    return MICommand(MICommandName.EXEC_INTERRUPT)


def exec_continue() -> MICommand:
    """Build a continue command."""

    return MICommand(MICommandName.EXEC_CONTINUE)


def exec_step_instruction() -> MICommand:
    """Build a single-instruction step command."""

    return MICommand(MICommandName.EXEC_STEP_INSTRUCTION)


def break_insert(
    location: str,
    *,
    breakpoint_type: BreakpointType,
    temporary: bool = False,
) -> MICommand:
    """Build a breakpoint insertion command."""

    flags: list[str] = []
    if temporary:
        flags.append("-t")
    if breakpoint_type == BreakpointType.HARDWARE:
        flags.append("-h")
    return MICommand(MICommandName.BREAK_INSERT, (*flags, location))


def break_delete(breakpoint_id: str) -> MICommand:
    """Build a breakpoint deletion command."""

    return MICommand(MICommandName.BREAK_DELETE, (breakpoint_id,))

def interpreter_exec_console(command: str) -> MICommand:
    """Build an allowlisted interpreter-exec console command."""

    if command not in ALLOWLISTED_CONSOLE_COMMANDS:
        raise ValueError(f"console command is not allowlisted: {command}")
    return MICommand(MICommandName.INTERPRETER_EXEC, ("console", command))


def _quote_arg(arg: str) -> str:
    if arg == "":
        return '""'
    if any(char.isspace() or char in {'"', "\\"} for char in arg):
        escaped = arg.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return arg

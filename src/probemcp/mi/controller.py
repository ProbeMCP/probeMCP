"""Async GDB/MI controller foundation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Protocol

from probemcp.mi.commands import MICommand
from probemcp.mi.errors import MIParseError
from probemcp.mi.parser import parse_mi_record
from probemcp.mi.records import MIRecord, MIRecordKind, MIStreamRecord


class MIControllerError(RuntimeError):
    """Base controller error."""


class MICommandError(MIControllerError):
    """Raised when GDB returns a `^error` result record."""

    def __init__(self, record: MIRecord) -> None:
        self.record = record
        message = str(record.results.get("msg", record.raw))
        super().__init__(message)


class MITimeoutError(TimeoutError, MIControllerError):
    """Raised when a command does not complete within its timeout."""


class MITransport(Protocol):
    """Minimal async line transport used by MIController."""

    async def write_line(self, line: str) -> None:
        """Write one MI command line without a trailing newline requirement."""

    async def read_line(self) -> str:
        """Read one MI output line."""

    async def close(self) -> None:
        """Close the transport."""


@dataclass(frozen=True, slots=True)
class MICommandResult:
    """Result of one tokenized MI command."""

    result_record: MIRecord
    async_records: tuple[MIRecord, ...] = ()
    stream_records: tuple[MIStreamRecord, ...] = ()


@dataclass(slots=True)
class MIController:
    """Serialize MI commands and correlate tokenized result records."""

    transport: MITransport
    _next_token: int = 1
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def execute(self, command: MICommand, *, timeout_ms: int = 3000) -> MICommandResult:
        """Execute one command and return its token-matched result."""

        async with self._lock:
            token = self._allocate_token()
            await self.transport.write_line(command.serialize(token))
            try:
                return await self._read_until_result(token, timeout_ms=timeout_ms)
            except TimeoutError as exc:
                raise MITimeoutError(
                    f"MI command {command.name.value} timed out after {timeout_ms} ms"
                ) from exc

    async def close(self) -> None:
        """Close the underlying transport."""

        await self.transport.close()

    def _allocate_token(self) -> int:
        token = self._next_token
        self._next_token += 1
        return token

    async def _read_until_result(self, token: int, *, timeout_ms: int) -> MICommandResult:
        async_records: list[MIRecord] = []
        stream_records: list[MIStreamRecord] = []
        timeout_s = timeout_ms / 1000

        async with asyncio.timeout(timeout_s):
            while True:
                line = await self.transport.read_line()
                try:
                    record = parse_mi_record(line)
                except MIParseError as exc:
                    raise MIControllerError(str(exc)) from exc

                if isinstance(record, MIStreamRecord):
                    stream_records.append(record)
                    continue

                if record.kind != MIRecordKind.RESULT:
                    async_records.append(record)
                    continue

                if record.token != token:
                    async_records.append(record)
                    continue

                result = MICommandResult(
                    result_record=record,
                    async_records=tuple(async_records),
                    stream_records=tuple(stream_records),
                )
                if record.record_class == "error":
                    raise MICommandError(record)
                return result


class SubprocessMITransport:
    """Async subprocess-backed GDB/MI transport."""

    def __init__(self, process: asyncio.subprocess.Process) -> None:
        if process.stdin is None or process.stdout is None:
            raise ValueError("GDB process must expose stdin and stdout pipes")
        self.process = process
        self._stdin = process.stdin
        self._stdout = process.stdout

    @classmethod
    async def spawn(
        cls,
        args: list[str],
    ) -> SubprocessMITransport:
        """Spawn a subprocess exposing a GDB/MI-like stdin/stdout transport."""

        process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        return cls(process)

    @classmethod
    async def spawn_gdb(cls, gdb_path: str, elf_path: str | None = None) -> SubprocessMITransport:
        """Spawn GDB in MI mode without loading user init files."""

        args = [gdb_path, "--interpreter=mi2", "--nx", "--nh", "-q"]
        if elf_path is not None:
            args.append(elf_path)
        return await cls.spawn(args)

    async def write_line(self, line: str) -> None:
        self._stdin.write(f"{line}\n".encode())
        await self._stdin.drain()

    async def read_line(self) -> str:
        line = await self._stdout.readline()
        if line == b"":
            raise MIControllerError("GDB process closed stdout")
        return line.decode(errors="replace").rstrip("\r\n")

    async def close(self) -> None:
        if self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=2)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()

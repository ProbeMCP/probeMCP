"""Snapshot capture service."""

from __future__ import annotations

from typing import Protocol

from probemcp.mcp_server.schemas import DebugSnapshotRequest, ReadMemoryData, RegisterGroup
from probemcp.snapshots.models import DebugSnapshot
from probemcp.symbols import SymbolContext
from probemcp.targets import normalize_registers

FAULT_REGISTER_ADDRESSES = {
    "cfsr": "0xE000ED28",
    "hfsr": "0xE000ED2C",
    "dfsr": "0xE000ED30",
    "mmfar": "0xE000ED34",
    "bfar": "0xE000ED38",
}


class SnapshotTarget(Protocol):
    """Minimal target interface needed to capture a snapshot."""

    @property
    def state(self) -> object:
        """Return current target state."""

    async def read_registers(self, group: RegisterGroup = RegisterGroup.CORE) -> dict[str, str]:
        """Read target registers."""

    async def read_memory(
        self,
        *,
        address: str,
        length: int,
        width: int = 1,
        timeout_ms: int = 3000,
    ) -> ReadMemoryData:
        """Read target memory."""


class SnapshotService:
    """Capture analyzer-friendly snapshots from a target."""

    async def capture(
        self,
        *,
        session_id: str,
        target: SnapshotTarget,
        request: DebugSnapshotRequest,
    ) -> DebugSnapshot:
        """Capture a debug snapshot."""

        core_registers: dict[str, str] = {}
        fault_registers: dict[str, str] = {}
        stack_address: str | None = None
        stack_data_hex: str | None = None
        symbol_context: SymbolContext | None = None

        if request.include_core_registers:
            core_registers = normalize_registers(await target.read_registers(RegisterGroup.CORE))

        if request.include_fault_registers:
            fault_registers = await self._read_fault_registers(target)

        if request.include_stack and request.stack_bytes > 0:
            stack_address = _select_stack_pointer(core_registers)
            if stack_address is not None:
                memory = await target.read_memory(
                    address=stack_address,
                    length=request.stack_bytes,
                    timeout_ms=3000,
                )
                stack_data_hex = memory.data_hex

        pc = core_registers.get("pc") or core_registers.get("15")
        resolver = getattr(target, "symbol_context", None)
        if request.include_symbol_context and pc is not None and callable(resolver):
            symbol_context = await resolver(
                address=pc,
                instruction_count=request.disassembly_instructions,
            )

        summary = _build_summary(core_registers, fault_registers, symbol_context)
        return DebugSnapshot(
            session_id=session_id,
            state=target.state,  # type: ignore[arg-type]
            core_registers=core_registers,
            fault_registers=fault_registers,
            stack_address=stack_address,
            stack_data_hex=stack_data_hex,
            symbol_context=symbol_context,
            summary=summary,
        )

    async def _read_fault_registers(self, target: SnapshotTarget) -> dict[str, str]:
        fault_registers: dict[str, str] = {}
        for name, address in FAULT_REGISTER_ADDRESSES.items():
            memory = await target.read_memory(address=address, length=4, timeout_ms=3000)
            fault_registers[name] = _little_endian_hex(memory.data_hex)
        return fault_registers


def _little_endian_hex(data_hex: str) -> str:
    data = bytes.fromhex(data_hex)
    value = int.from_bytes(data, byteorder="little", signed=False)
    return f"0x{value:08x}"


def _select_stack_pointer(registers: dict[str, str]) -> str | None:
    return registers.get("sp") or registers.get("13") or registers.get("msp")


def _build_summary(
    core_registers: dict[str, str],
    fault_registers: dict[str, str],
    symbol_context: SymbolContext | None = None,
) -> str:
    pc = core_registers.get("pc") or core_registers.get("15")
    cfsr = fault_registers.get("cfsr")
    symbol = symbol_context.symbol if symbol_context is not None else None
    if pc and cfsr:
        location = f" ({symbol})" if symbol else ""
        return f"Target snapshot captured at PC {pc}{location} with CFSR {cfsr}."
    if pc:
        location = f" ({symbol})" if symbol else ""
        return f"Target snapshot captured at PC {pc}{location}."
    return "Target snapshot captured."

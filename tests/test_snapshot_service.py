from probemcp.mcp_server.schemas import (
    DebugSnapshotRequest,
    ReadMemoryData,
    RegisterGroup,
    TargetState,
)
from probemcp.snapshots.service import SnapshotService
from probemcp.symbols import DisassemblyInstruction, SymbolContext


class FakeSnapshotTarget:
    state = TargetState.HALTED

    def __init__(self) -> None:
        self.memory_reads: list[tuple[str, int]] = []

    async def read_registers(self, group: RegisterGroup = RegisterGroup.CORE) -> dict[str, str]:
        assert group == RegisterGroup.CORE
        return {"pc": "0x08001234", "sp": "0x20001000", "lr": "0xfffffff9"}

    async def read_memory(
        self,
        *,
        address: str,
        length: int,
        width: int = 1,
        timeout_ms: int = 3000,
    ) -> ReadMemoryData:
        self.memory_reads.append((address, length))
        if address == "0xE000ED28":
            return ReadMemoryData(address=address, length=length, width=width, data_hex="00000200")
        return ReadMemoryData(address=address, length=length, width=width, data_hex="00000000")

    async def symbol_context(
        self,
        *,
        address: str,
        instruction_count: int = 6,
        timeout_ms: int = 3000,
    ) -> SymbolContext:
        return SymbolContext(
            address=address,
            symbol="main",
            source="/workspace/main.c:42",
            disassembly=[
                DisassemblyInstruction(address=address, function="main", instruction="udf #0")
            ][:instruction_count],
            confidence=0.9,
        )


async def test_snapshot_service_captures_core_fault_and_stack_data() -> None:
    target = FakeSnapshotTarget()

    snapshot = await SnapshotService().capture(
        session_id="session_01",
        target=target,
        request=DebugSnapshotRequest(session_id="session_01", include_stack=True, stack_bytes=16),
    )

    assert snapshot.session_id == "session_01"
    assert snapshot.core_registers["pc"] == "0x08001234"
    assert snapshot.fault_registers["cfsr"] == "0x00020000"
    assert snapshot.stack_address == "0x20001000"
    assert snapshot.symbol_context is not None
    assert snapshot.symbol_context.symbol == "main"
    assert ("0x20001000", 16) in target.memory_reads
    assert "PC 0x08001234 (main)" in snapshot.summary

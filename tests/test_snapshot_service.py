from probemcp.mcp_server.schemas import (
    DebugSnapshotRequest,
    ReadMemoryData,
    RegisterGroup,
    TargetState,
)
from probemcp.snapshots.service import SnapshotService


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
    assert ("0x20001000", 16) in target.memory_reads
    assert "PC 0x08001234" in snapshot.summary

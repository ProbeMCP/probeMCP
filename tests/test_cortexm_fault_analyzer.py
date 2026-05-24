from probemcp.analyzers.cortexm import CortexMFaultAnalyzer
from probemcp.mcp_server.schemas import TargetState
from probemcp.snapshots.models import DebugSnapshot


def test_cortexm_fault_analyzer_decodes_usage_fault_invstate() -> None:
    snapshot = DebugSnapshot(
        session_id="session_01",
        state=TargetState.HALTED,
        core_registers={
            "pc": "0x08001234",
            "lr": "0xfffffff9",
            "sp": "0x20001000",
            "xpsr": "0x00000003",
        },
        fault_registers={
            "cfsr": "0x00020000",
            "hfsr": "0x40000000",
        },
    )

    result = CortexMFaultAnalyzer().analyze(snapshot)

    assert result.fault_type == "UsageFault: INVSTATE"
    assert result.confidence == 0.9
    assert "CFSR.UFSR.INVSTATE is set." in result.evidence
    assert result.decoded_registers["exc_return"]["stack_pointer"] == "msp"


def test_cortexm_fault_analyzer_decodes_precise_bus_fault() -> None:
    snapshot = DebugSnapshot(
        session_id="session_01",
        state=TargetState.HALTED,
        core_registers={"15": "0x08000010", "14": "0xfffffff9", "25": "0x01000003"},
        fault_registers={"cfsr": "0x00000200", "bfar": "0x2000ffff"},
    )

    result = CortexMFaultAnalyzer().analyze(snapshot)

    assert result.fault_type == "BusFault: PRECISERR"
    assert "precise data bus fault" in result.hypotheses[0]
    assert result.decoded_registers["pc"] == "0x08000010"


def test_cortexm_fault_analyzer_reports_low_confidence_without_fault_bits() -> None:
    snapshot = DebugSnapshot(
        session_id="session_01",
        state=TargetState.HALTED,
        fault_registers={"cfsr": "0x00000000", "hfsr": "0x00000000"},
    )

    result = CortexMFaultAnalyzer().analyze(snapshot)

    assert result.fault_type == "No Cortex-M fault bits set"
    assert result.confidence == 0.35


def test_cortexm_fault_analyzer_decodes_valid_fault_addresses_and_stack_frame() -> None:
    stack_words = [
        0x1,
        0x2,
        0x3,
        0x4,
        0x12,
        0xFFFF_FFF9,
        0x0800_1234,
        0x0100_0003,
    ]
    stack_hex = b"".join(word.to_bytes(4, "little") for word in stack_words).hex()
    snapshot = DebugSnapshot(
        session_id="session_01",
        state=TargetState.HALTED,
        core_registers={"lr": "0xfffffff9", "xpsr": "0x01000003"},
        fault_registers={
            "cfsr": "0x00008280",
            "mmfar": "0x20000000",
            "bfar": "0x20000004",
        },
        stack_data_hex=stack_hex,
    )

    result = CortexMFaultAnalyzer().analyze(snapshot)

    assert result.decoded_registers["mmfar_valid"] is True
    assert result.decoded_registers["bfar_valid"] is True
    assert result.decoded_registers["stacked_frame"]["pc"] == "0x08001234"


def test_cortexm_fault_analyzer_handles_malformed_numbers_and_short_stack() -> None:
    snapshot = DebugSnapshot(
        session_id="session_01",
        state=TargetState.HALTED,
        core_registers={"xpsr": "not-a-number"},
        fault_registers={"cfsr": "not-a-number", "hfsr": "0x00000002"},
        stack_data_hex="abcd",
    )

    result = CortexMFaultAnalyzer().analyze(snapshot)

    assert result.fault_type == "HardFault: VECTTBL"
    assert any("no complete frame" in item for item in result.evidence)

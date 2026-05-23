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

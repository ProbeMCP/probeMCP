"""Cortex-M fault analyzer."""

from __future__ import annotations

from probemcp.mcp_server.schemas import FaultAnalysisData, JsonScalar, JsonValue
from probemcp.snapshots.models import DebugSnapshot

USAGE_FAULT_BITS = {
    0: "UNDEFINSTR",
    1: "INVSTATE",
    2: "INVPC",
    3: "NOCP",
    8: "UNALIGNED",
    9: "DIVBYZERO",
}

BUS_FAULT_BITS = {
    0: "IBUSERR",
    1: "PRECISERR",
    2: "IMPRECISERR",
    3: "UNSTKERR",
    4: "STKERR",
    5: "LSPERR",
    7: "BFARVALID",
}

MEMMANAGE_FAULT_BITS = {
    0: "IACCVIOL",
    1: "DACCVIOL",
    3: "MUNSTKERR",
    4: "MSTKERR",
    5: "MLSPERR",
    7: "MMARVALID",
}


class CortexMFaultAnalyzer:
    """Decode Cortex-M fault evidence from a debug snapshot."""

    def analyze(self, snapshot: DebugSnapshot) -> FaultAnalysisData:
        """Return deterministic Cortex-M fault analysis."""

        registers = _normalize_registers(snapshot.core_registers)
        fault_registers = _normalize_registers(snapshot.fault_registers)
        cfsr = _parse_int(fault_registers.get("cfsr"))
        hfsr = _parse_int(fault_registers.get("hfsr"))

        evidence: list[str] = []
        hypotheses: list[str] = []
        actions: list[str] = []
        decoded: dict[str, JsonValue] = {
            "pc": registers.get("pc"),
            "lr": registers.get("lr"),
            "sp": registers.get("sp"),
            "xpsr": registers.get("xpsr"),
            "cfsr": fault_registers.get("cfsr"),
            "hfsr": fault_registers.get("hfsr"),
            "dfsr": fault_registers.get("dfsr"),
            "mmfar": fault_registers.get("mmfar"),
            "bfar": fault_registers.get("bfar"),
        }

        fault_type, bit_evidence = _classify_fault(cfsr, hfsr)
        evidence.extend(bit_evidence)

        lr = _parse_int(registers.get("lr"))
        if lr is not None and _is_exc_return(lr):
            decoded["exc_return"] = _decode_exc_return(lr)
            evidence.append(f"LR contains EXC_RETURN 0x{lr:08x}.")

        xpsr = _parse_int(registers.get("xpsr"))
        if xpsr is not None:
            active_exception = xpsr & 0x1FF
            decoded["active_exception"] = active_exception
            evidence.append(f"xPSR active exception number is {active_exception}.")
            if xpsr & (1 << 24) == 0:
                evidence.append("xPSR T bit is clear, indicating invalid Thumb state evidence.")

        if "INVSTATE" in fault_type:
            hypotheses.append("Execution branched to an invalid non-Thumb address.")
            hypotheses.append("A function pointer or return address may be corrupted.")
        elif "PRECISERR" in fault_type:
            hypotheses.append(
                "A precise data bus fault occurred at or near the faulting instruction."
            )
        elif "MemManage" in fault_type:
            hypotheses.append("The target accessed an invalid or protected memory region.")
        elif "HardFault" in fault_type:
            hypotheses.append("A configurable fault escalated into HardFault.")

        actions.extend(
            [
                "Resolve the stacked PC to a symbol.",
                "Disassemble around the PC.",
                "Inspect LR and the active stack pointer.",
            ]
        )
        if snapshot.stack_data_hex:
            actions.append("Decode the stacked exception frame from captured stack bytes.")

        confidence = 0.9 if cfsr or hfsr else 0.35
        return FaultAnalysisData(
            fault_type=fault_type,
            confidence=confidence,
            evidence=evidence or ["No Cortex-M fault status bits were set in the snapshot."],
            hypotheses=hypotheses or ["No specific fault hypothesis can be made from status bits."],
            recommended_next_actions=actions,
            decoded_registers=decoded,
        )


def _classify_fault(cfsr: int | None, hfsr: int | None) -> tuple[str, list[str]]:
    cfsr_value = cfsr or 0
    hfsr_value = hfsr or 0
    evidence: list[str] = []

    mem_bits = cfsr_value & 0xFF
    bus_bits = (cfsr_value >> 8) & 0xFF
    usage_bits = (cfsr_value >> 16) & 0xFFFF

    usage_names = _decode_bit_names(usage_bits, USAGE_FAULT_BITS)
    if usage_names:
        evidence.extend(f"CFSR.UFSR.{name} is set." for name in usage_names)
        return f"UsageFault: {', '.join(usage_names)}", evidence

    bus_names = _decode_bit_names(bus_bits, BUS_FAULT_BITS)
    if bus_names:
        evidence.extend(f"CFSR.BFSR.{name} is set." for name in bus_names)
        return f"BusFault: {', '.join(bus_names)}", evidence

    mem_names = _decode_bit_names(mem_bits, MEMMANAGE_FAULT_BITS)
    if mem_names:
        evidence.extend(f"CFSR.MMFSR.{name} is set." for name in mem_names)
        return f"MemManageFault: {', '.join(mem_names)}", evidence

    if hfsr_value & (1 << 30):
        evidence.append("HFSR.FORCED is set.")
        return "HardFault: FORCED", evidence

    if hfsr_value & (1 << 1):
        evidence.append("HFSR.VECTTBL is set.")
        return "HardFault: VECTTBL", evidence

    return "No Cortex-M fault bits set", evidence


def _decode_bit_names(value: int, names: dict[int, str]) -> list[str]:
    return [name for bit, name in names.items() if value & (1 << bit)]


def _normalize_registers(registers: dict[str, str]) -> dict[str, str]:
    normalized = {key.lower(): value for key, value in registers.items()}
    aliases = {
        "15": "pc",
        "14": "lr",
        "13": "sp",
        "25": "xpsr",
    }
    for source, target in aliases.items():
        if source in normalized and target not in normalized:
            normalized[target] = normalized[source]
    return normalized


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value, 0)


def _is_exc_return(value: int) -> bool:
    return (value & 0xFF000000) == 0xFF000000


def _decode_exc_return(value: int) -> dict[str, JsonScalar]:
    return {
        "raw": f"0x{value:08x}",
        "stack_pointer": "psp" if value & (1 << 2) else "msp",
        "return_mode": "thread" if value & (1 << 3) else "handler",
        "frame_type": "basic" if value & (1 << 4) else "extended",
    }

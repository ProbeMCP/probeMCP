"""Target-profile helpers."""

from __future__ import annotations

from probemcp.mcp_server.schemas import BackendKind

ARM_CORTEX_M_REGISTER_ALIASES = {
    "0": "r0",
    "1": "r1",
    "2": "r2",
    "3": "r3",
    "4": "r4",
    "5": "r5",
    "6": "r6",
    "7": "r7",
    "8": "r8",
    "9": "r9",
    "10": "r10",
    "11": "r11",
    "12": "r12",
    "13": "sp",
    "14": "lr",
    "15": "pc",
    "16": "xpsr",
    "17": "msp",
    "18": "psp",
    "25": "xpsr",
}


def normalize_registers(registers: dict[str, str], *, profile: str = "cortex-m") -> dict[str, str]:
    """Normalize debugger register names while preserving raw values."""

    normalized = {key.lower(): value for key, value in registers.items()}
    if profile == "cortex-m":
        for source, target in ARM_CORTEX_M_REGISTER_ALIASES.items():
            if source in normalized and target not in normalized:
                normalized[target] = normalized[source]
    return normalized


def infer_architecture(backend: BackendKind, profile: str) -> str | None:
    """Infer a coarse architecture string from a backend/profile pair."""

    if profile == "cortex-m":
        return "arm"
    if profile.startswith("riscv"):
        return "riscv"
    if profile.startswith("xtensa"):
        return "xtensa"
    if backend == BackendKind.QEMU:
        return "unknown-emulated"
    return None

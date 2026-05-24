"""Symbol and disassembly context models."""

from __future__ import annotations

from pydantic import Field

from probemcp.mcp_server.schemas import SchemaModel
from probemcp.mi.records import MIValue


class DisassemblyInstruction(SchemaModel):
    """One instruction near a target address."""

    address: str
    function: str | None = None
    offset: int | None = None
    instruction: str


class SymbolContext(SchemaModel):
    """Best-effort symbol/disassembly context for a stopped PC."""

    address: str
    symbol: str | None = None
    source: str | None = None
    disassembly: list[DisassemblyInstruction] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


def summarize_symbol_context(context: SymbolContext) -> str:
    """Summarize symbol context without overstating certainty."""

    if context.symbol:
        return f"{context.address} resolves near {context.symbol}."
    if context.disassembly:
        return f"{context.address} has disassembly context but no symbol."
    return f"No symbol context is available for {context.address}."

def symbol_context_from_mi(
    *,
    address: str,
    frame: MIValue | None,
    asm_insns: MIValue | None,
) -> SymbolContext:
    """Build best-effort source and disassembly context from MI results."""

    frame_data = frame if isinstance(frame, dict) else {}
    symbol = _string_value(frame_data.get("func"))
    source = _format_source(frame_data)
    disassembly = _parse_disassembly(asm_insns)
    confidence = _confidence(symbol=symbol, source=source, disassembly=disassembly)
    return SymbolContext(
        address=address,
        symbol=symbol,
        source=source,
        disassembly=disassembly,
        confidence=confidence,
    )

def _parse_disassembly(asm_insns: MIValue | None) -> list[DisassemblyInstruction]:
    if not isinstance(asm_insns, list):
        return []

    instructions: list[DisassemblyInstruction] = []
    for item in asm_insns:
        if not isinstance(item, dict):
            continue
        address = _string_value(item.get("address"))
        instruction = _string_value(item.get("inst"))
        if address is None or instruction is None:
            continue
        instructions.append(
            DisassemblyInstruction(
                address=address,
                function=_string_value(item.get("func-name")),
                offset=_int_value(item.get("offset")),
                instruction=instruction,
            )
        )
    return instructions

def _format_source(frame: dict[str, MIValue]) -> str | None:
    file_name = _string_value(frame.get("fullname")) or _string_value(frame.get("file"))
    line = _string_value(frame.get("line"))
    if file_name is None:
        return None
    if line is None:
        return file_name
    return f"{file_name}:{line}"

def _confidence(
    *,
    symbol: str | None,
    source: str | None,
    disassembly: list[DisassemblyInstruction],
) -> float:
    if symbol and source and disassembly:
        return 0.9
    if symbol and disassembly:
        return 0.75
    if symbol or source:
        return 0.6
    if disassembly:
        return 0.4
    return 0.0

def _string_value(value: MIValue | None) -> str | None:
    return value if isinstance(value, str) and value else None

def _int_value(value: MIValue | None) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None

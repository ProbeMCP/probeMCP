from probemcp.symbols import (
    DisassemblyInstruction,
    SymbolContext,
    summarize_symbol_context,
    symbol_context_from_mi,
)


def test_symbol_context_summary_uses_available_evidence() -> None:
    with_symbol = SymbolContext(address="0x08001234", symbol="HardFault_Handler", confidence=0.8)
    with_disassembly = SymbolContext(
        address="0x08001234",
        disassembly=[
            DisassemblyInstruction(address="0x08001234", instruction="ldr r0, [r0]")
        ],
        confidence=0.4,
    )
    without_context = SymbolContext(address="0x08001234", confidence=0.0)

    assert "HardFault_Handler" in summarize_symbol_context(with_symbol)
    assert "disassembly context" in summarize_symbol_context(with_disassembly)
    assert "No symbol context" in summarize_symbol_context(without_context)

def test_symbol_context_from_mi_uses_frame_and_disassembly() -> None:
    context = symbol_context_from_mi(
        address="0x08001234",
        frame={
            "addr": "0x08001234",
            "func": "main",
            "fullname": "/workspace/main.c",
            "line": "42",
        },
        asm_insns=[
            {
                "address": "0x08001234",
                "func-name": "main",
                "offset": "4",
                "inst": "udf #0",
            }
        ],
    )

    assert context.symbol == "main"
    assert context.source == "/workspace/main.c:42"
    assert context.disassembly[0].instruction == "udf #0"
    assert context.confidence == 0.9

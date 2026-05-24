# Backend Checklist

## Backend Adapter Scope

- Implement adapter behavior in `src/probemcp/backends/`.
- Return `BackendConnection` with backend kind, endpoint, profile, architecture when known, target state, and feature flags.
- Keep backend-specific reset/halt monitor commands allowlisted.
- Never expose arbitrary monitor, shell, or GDB command execution through MCP.

## Tests

- Add adapter conformance coverage in `tests/test_adapter_conformance.py` or a focused backend test.
- Add session-level tests in `tests/test_backend_and_session.py` when `DebugSession` behavior changes.
- Add MI transcript fixtures under `tests/fixtures/mi/` when using real debugger output.
- Add skipped opt-in tests for live tools:
  - `PROBEMCP_RUN_QEMU=1` for QEMU
  - `PROBEMCP_RUN_HARDWARE=1` for physical hardware

## QEMU Demo

The Cortex-M HardFault fixture lives in `examples/qemu-cortexm-hardfault/`.
Default CI checks source presence and skips live QEMU. Live runs require local `qemu-system-arm`, `arm-none-eabi-gcc`, and `arm-none-eabi-gdb`.

## Documentation

Update these docs when support changes:

- `docs/backend-adapters.md`
- `docs/compatibility-matrix.md`
- `docs/vendor-backend-research.md`
- `examples/qemu-cortexm-hardfault/README.md`

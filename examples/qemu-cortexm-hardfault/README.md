# QEMU Cortex-M HardFault Demo

This example will become the first end-to-end ProbeMCP validation target.

Planned workflow:

1. Build a small Cortex-M firmware image that intentionally triggers a fault.
2. Run it in QEMU with a GDB stub.
3. Connect ProbeMCP to the QEMU GDB endpoint.
4. Capture a debug snapshot.
5. Run `analyze_fault`.
6. Verify that ProbeMCP reports fault evidence and next actions.

The example should be deterministic and suitable for CI where possible.

---
name: probemcp-backend-lab
description: Add, debug, or validate ProbeMCP GDB-compatible debugger backends and lab workflows. Use when working on Generic Remote, QEMU gdbstub, OpenOCD, J-Link, pyOCD, ST-Link/S32DBG research, GDB/MI transcripts, adapter conformance, QEMU demos, serial capture, power control, or hardware-marked tests.
---

# ProbeMCP Backend Lab

## Workflow

Keep backend work adapter-owned and evidence-driven:

1. Identify whether the target is emulator, generic remote, OpenOCD, J-Link, pyOCD, or a research backend.
2. Add only allowlisted MI or adapter monitor actions.
3. Cover behavior with fake MI/controller tests first.
4. Add transcript fixtures when behavior depends on real debugger output.
5. Add opt-in QEMU or hardware tests only behind markers and environment variables.

Read `references/backend-checklist.md` before adding a new backend or changing reset/halt/connect behavior.

## GDB/MI Rules

- Use builders in `src/probemcp/mi/commands.py`; do not serialize ad hoc MI strings in service code.
- Keep `MIController` command execution serialized and timeout-bound.
- Preserve async and stream records in command results when they matter for state.
- Add malformed/vendor transcript coverage when parser behavior changes.

## Validation

Default validation should not require hardware:

- unit tests for adapter contract and session behavior
- MI transcript corpus tests
- fake subprocess/controller smoke tests
- skipped opt-in tests for QEMU or physical hardware

Use live hardware results only as validation evidence when logs include backend version, GDB version, host OS, target, exact operations, and sanitized transcripts.

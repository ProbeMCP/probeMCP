---
name: probemcp-safety-review
description: Review or implement safety-sensitive ProbeMCP changes. Use when modifying permission modes, confirmation tokens, target-changing tools, memory writes, reset/halt/resume behavior, hardware target classes, resource limits, audit logs, privacy/redaction, or anything that could affect real embedded hardware.
---

# ProbeMCP Safety Review

## Workflow

Treat safety as a product feature. Before editing, identify the operation class:

- read-only observation: registers, memory reads, snapshots, analysis, resources
- target-changing control: connect, disconnect, halt, resume, step, reset, breakpoints
- destructive or high-risk: memory writes, flash-like behavior, production/lab hardware reset, power control

Read `references/safety-checklist.md` for the detailed checklist when the change touches policy, target state, audit, or hardware.

## Required Checks

- Confirm the operation has a structured `DebugOperation`.
- Confirm `PolicyEngine` handles the operation deterministically.
- Confirm confirmation tokens are bound to material request data for target-changing actions.
- Confirm production/lab hardware cannot accidentally inherit emulator convenience.
- Confirm resource-limit failures return `RESOURCE_LIMIT_EXCEEDED` and are auditable.
- Confirm tool responses expose warnings when policy allows a risky operation.
- Confirm tests cover readonly, confirm-required, full-control, emulator, development hardware, lab hardware, and production hardware when relevant.

## Avoid

- Do not add raw GDB command execution as a public tool.
- Do not route MCP tool arguments into shell commands.
- Do not add flash programming in the open safety path without a dedicated policy model.
- Do not mark hardware behavior validated unless a transcript or opt-in hardware test proves it.

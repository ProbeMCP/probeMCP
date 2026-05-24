# ProbeMCP

[![CI](https://github.com/ProbeMCP/probeMCP/actions/workflows/ci.yml/badge.svg)](https://github.com/ProbeMCP/probeMCP/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

ProbeMCP is an open-source, local-first MCP server for safe AI-assisted
embedded debugging through GDB-compatible debuggers.

The project goal is not to expose arbitrary GDB commands to AI clients. The
goal is to provide a structured debugging control plane with safe tools,
session management, audit logging, backend adapters, and embedded-aware
analysis for real hardware, emulators, and remote targets.

## Vision

ProbeMCP lets MCP-compatible clients such as Claude, Cursor, Codex, ChatGPT
with tools, and custom agents inspect and debug embedded systems through
high-level, deterministic, permission-aware tools.

Initial target area:

- ARM Cortex-M
- Generic remote `gdbserver`
- QEMU gdbstub
- OpenOCD
- J-Link GDB Server
- pyOCD

Future target area:

- RISC-V
- Xtensa / ESP32
- Cortex-A
- vendor-specific GDB servers
- SVD peripheral decoding
- RTOS awareness
- multi-board lab orchestration

## Design Principles

- Local-first by default.
- Safe structured tools, not raw debugger command execution.
- GDB/MI as the orchestration protocol.
- Explicit permission modes for target-changing actions.
- Audit every tool call that observes or changes target state.
- Backend adapters isolate debugger/vendor quirks.
- Analyzers must report evidence, confidence, and uncertainty.
- The open-source core should be useful without any hosted service.

## MVP Scope

ProbeMCP v0.1 should prove one complete workflow:

1. Start a local MCP server.
2. Connect to a QEMU or hardware target through a GDB-compatible backend.
3. Halt, step, resume with a bounded timeout, read registers, and read memory.
4. Capture a debug snapshot.
5. Analyze a Cortex-M fault using core registers and SCB fault registers.
6. Return structured evidence and recommended next debugging actions.
7. Record an audit log for all tool calls.

Out of scope for v0.1:

- Flash programming
- Arbitrary GDB command execution
- Arbitrary shell execution
- SaaS features
- Production multi-board orchestration
- Complete SVD/peripheral heuristic coverage
- Full RTOS memory-structure decoding

## Architecture

```text
AI Client
  |
  v
Python MCP Server
  |
  v
ProbeMCP Tool Layer
  |
  v
Safety & Permission Engine
  |
  v
Session Manager
  |
  v
GDB/MI Orchestration Layer
  |
  v
Debugger Backend Adapter
  |
  v
GDB-compatible target
```

See [docs/architecture.md](docs/architecture.md) for the proposed module
layout and runtime model.

## v0.1 Tool Set

Primitive tools:

- `connect_target`
- `disconnect_target`
- `halt`
- `resume`
- `step_instruction`
- `reset_target`
- `read_registers`
- `read_memory`
- `write_memory` (disabled by default)
- `set_breakpoint`
- `clear_breakpoint`

High-level tools:

- `debug_snapshot`
- `analyze_fault`
- `inspect_peripheral`
- `compare_snapshots`
- `explain_current_state`
- `suggest_next_debug_steps`

See [docs/tool-contracts.md](docs/tool-contracts.md) for draft request and
response contracts.

See [docs/mvp-plan.md](docs/mvp-plan.md) for the implementation order and
release acceptance criteria.

## Safety Model

ProbeMCP uses three permission modes:

- `readonly`
- `confirm-required`
- `full-control`

The default posture is conservative. Tools that can change target state must
pass through policy checks and audit logging before execution.

See [docs/safety-model.md](docs/safety-model.md).

Additional hardening docs:

- [security threat model](docs/security-threat-model.md)
- [privacy and redaction](docs/privacy-redaction.md)
- [compatibility matrix](docs/compatibility-matrix.md)
- [MCP client setup](docs/mcp-client-setup.md)
- [troubleshooting](docs/troubleshooting.md)

Examples:

- [Codex MCP integration smoke test](examples/codex-mcp/README.md)
- [QEMU Cortex-M HardFault demo](examples/qemu-cortexm-hardfault/README.md)

## Development

```bash
uv sync --extra dev
uv run probemcp doctor
uv run pytest
uv run ruff check .
uv run ruff check . --select S --ignore S101,S105,S106
uv run mypy src
uv build
```

See [docs/development.md](docs/development.md) for the local development
workflow and quality bar.

## Technology Direction

Recommended initial stack:

- Python 3.12+
- official Python MCP SDK
- `asyncio`
- `pydantic`
- custom GDB/MI controller
- `pytest` and `pytest-asyncio`
- `ruff`
- `mypy`
- `structlog`
- `uv`
- SQLite and JSONL audit output

## Repository Status

This repository now has the core Python scaffolding for safe MCP tools,
GDB/MI orchestration, backend adapters, config, confirmation tokens, audit
logging, Cortex-M analysis, SVD/RTOS/lab primitives, and CI quality gates. The
next public milestone is a live QEMU Cortex-M HardFault demo through an MCP
client using safe structured tools.

## License

ProbeMCP is licensed under the Apache License 2.0.

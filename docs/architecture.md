# Architecture

ProbeMCP is a local-first MCP server for embedded debugging through
GDB-compatible backends. The core product is a safe debugging control plane,
not a thin wrapper around raw GDB commands.

## Runtime Layers

```text
AI Client
  |
  v
MCP Server
  |
  v
Tool Registry
  |
  v
Safety & Permission Engine
  |
  v
Session Manager
  |
  v
Debug Session
  |
  v
GDB/MI Controller
  |
  v
Backend Adapter
  |
  v
GDB-compatible Target
```

## Proposed Package Layout

```text
src/probemcp/
  mcp_server/
    app.py
    tools.py
    schemas.py
    resources.py
  sessions/
    manager.py
    models.py
  debug/
    session.py
    state.py
  mi/
    controller.py
    parser.py
    records.py
    commands.py
    errors.py
  backends/
    base.py
    generic_remote.py
    qemu.py
    openocd.py
    jlink.py
    pyocd.py
  safety/
    policy.py
    permissions.py
    confirmations.py
    memory_map.py
  analyzers/
    cortexm/
      fault_analyzer.py
      registers.py
      exc_return.py
      scb.py
  snapshots/
    service.py
    models.py
    diff.py
  audit/
    logger.py
    sqlite_store.py
  config/
    project.py
    profiles.py
  cli.py
```

## Core Responsibilities

### MCP Server

The MCP server exposes structured tools and resources to AI clients. It should
remain thin: validate requests, call application services, and serialize
responses.

### Tool Registry

The tool registry defines stable tool contracts, permission requirements,
timeout behavior, and audit metadata.

### Safety & Permission Engine

The safety engine evaluates every target-observing or target-changing
operation before execution. It owns permission modes, confirmation tokens,
memory write policy, timeout limits, and production-target guardrails.

### Session Manager

The session manager owns active debug sessions, lifecycle state, session locks,
and session lookup. v0.1 should support one robust session before expanding to
multi-session and multi-board workflows.

### Debug Session

A debug session owns one GDB process, one backend adapter, one MI controller,
one safety context, and one audit stream. Session state must be explicit:

- `disconnected`
- `connecting`
- `halted`
- `running`
- `unknown`
- `degraded`

### GDB/MI Controller

The controller speaks GDB/MI over subprocess pipes. It must tokenize commands,
parse result records, handle async records, serialize command execution, apply
timeouts, and recover from broken sessions.

### Backend Adapters

Adapters isolate backend-specific behavior:

- generic remote `gdbserver`
- QEMU gdbstub
- OpenOCD
- J-Link GDB Server
- pyOCD

Adapters may expose allowlisted backend actions such as reset/halt, but never
arbitrary shell or monitor command execution.

### Analyzers

Analyzers convert raw target data into structured findings. The first analyzer
should decode Cortex-M fault state and produce evidence, hypotheses,
confidence, and recommended next actions.

### Audit Logger

Every tool call should produce an audit event containing:

- timestamp
- session id
- tool name
- permission mode
- request summary
- result summary
- target state before and after
- warnings and errors

SQLite should be the default local store, with JSONL export for easy sharing.

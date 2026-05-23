# MVP Plan

This plan keeps ProbeMCP focused on proving real utility before expanding into
many targets and analyzers.

## Recommended v0.1 Scope

Build a local MCP server that can debug one target session through GDB/MI with
safe structured tools.

Included:

- Python MCP server
- GDB/MI controller
- session manager
- generic remote backend
- QEMU backend
- OpenOCD attach backend
- safety policy engine
- audit logger
- snapshot service
- Cortex-M fault analyzer
- QEMU Cortex-M HardFault example

Excluded:

- arbitrary GDB command MCP tool
- arbitrary shell execution
- flash programming
- cloud dashboard
- full SVD support
- RTOS awareness
- multi-board lab orchestration

## Implementation Order

1. Build the GDB/MI parser and transcript test fixtures.
2. Build the async GDB/MI controller with tokenized command dispatch.
3. Add the debug session state machine.
4. Add the audit event model and local SQLite/JSONL storage.
5. Add the generic remote backend.
6. Add the QEMU backend and deterministic HardFault demo target.
7. Add primitive tools: connect, disconnect, halt, resume, step, read
   registers, read memory, set breakpoint, clear breakpoint.
8. Add the safety policy engine and confirmation-token flow.
9. Add snapshot capture.
10. Add Cortex-M fault decoding and analysis.
11. Add OpenOCD attach support.
12. Add adapter conformance tests.

## Acceptance Criteria

v0.1 is releasable when:

- An MCP client can connect to a QEMU Cortex-M target.
- The client can halt, step, resume with a bounded timeout, read registers,
  read memory, set breakpoints, and clear breakpoints.
- The client can capture a debug snapshot.
- The client can analyze a Cortex-M HardFault and return fault type,
  confidence, evidence, hypotheses, and recommended next actions.
- No MCP tool exposes arbitrary GDB command execution.
- No MCP tool exposes arbitrary shell execution.
- Every tool call emits an audit record.
- Timeouts do not leave the session in a falsely confident state.
- GDB/MI parser behavior is covered by transcript tests.

## Example Debug Workflow

1. User starts ProbeMCP locally.
2. AI client calls `connect_target` with a QEMU backend profile and ELF path.
3. AI client calls `resume` with `max_run_ms`.
4. Target faults and stops, or ProbeMCP interrupts it on timeout.
5. AI client calls `debug_snapshot`.
6. AI client calls `analyze_fault`.
7. ProbeMCP returns a structured diagnosis:
   - fault type
   - confidence
   - evidence
   - likely hypotheses
   - next safe actions
8. AI client asks permission before any target-changing follow-up action.

## First Demo Goal

The first public demo should show:

- a small Cortex-M firmware image running in QEMU,
- a deliberate HardFault,
- ProbeMCP connected through an MCP client,
- structured fault analysis,
- audit log output.

This demo is the wedge. It proves that ProbeMCP is more than a GDB wrapper.

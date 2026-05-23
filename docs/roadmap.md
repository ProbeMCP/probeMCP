# Roadmap

## Phase 0: Prototype

Goal: prove the GDB/MI orchestration model before building many tools.

- Implement a minimal async GDB/MI controller.
- Add tokenized command dispatch.
- Parse result records and async stop/running events.
- Test against canned GDB/MI transcripts.
- Connect to a QEMU Cortex-M target.

Exit criteria:

- A scripted Python test can connect to QEMU, halt, read registers, step, and
  resume with a timeout.

## Phase 1: MVP

Goal: release the first useful open-source MCP server.

- MCP server with stable tool contracts.
- Generic remote adapter.
- QEMU adapter.
- OpenOCD attach adapter.
- Session manager.
- Safety policy engine.
- Audit logger.
- Snapshot service.
- Cortex-M fault analyzer.

Exit criteria:

- An MCP client can analyze a QEMU Cortex-M HardFault demo end to end.

## Phase 2: Intelligent Debugging

Goal: make ProbeMCP useful beyond primitive target control.

- Symbol-aware fault summaries.
- Disassembly context.
- stack-frame reconstruction.
- snapshot comparison.
- guided next-step suggestions.

## Phase 3: SVD Peripheral Intelligence

Goal: make peripheral state understandable to AI clients.

- SVD loader.
- peripheral/register/bitfield decoding.
- peripheral snapshots.
- peripheral diffing.
- common misconfiguration heuristics.

## Phase 4: RTOS Awareness

Goal: understand operating system state.

- FreeRTOS task list.
- current task detection.
- stack high-water marks.
- queue and mutex inspection.
- faulting task attribution.

## Phase 5: Multi-Board Orchestration

Goal: support labs and CI hardware benches.

- target inventory.
- session locking.
- serial log capture.
- power-control adapter interface.
- board farm workflows.

## Phase 6: Commercial Direction

Goal: build a sustainable business while keeping the core open.

Potential commercial layers:

- hosted team dashboard for snapshots and audit logs.
- policy management.
- hardware lab scheduling.
- CI integration.
- proprietary enterprise adapters.
- support and certification for vendor backends.

The open-source core should remain local-first and useful without a hosted
service.

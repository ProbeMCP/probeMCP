# Changelog

All notable changes to ProbeMCP will be documented in this file.

This project follows semantic versioning after the first public release.

## Unreleased

- Initialized the open-source project structure.
- Added architecture, safety model, tool contract, backend adapter, roadmap,
  and MVP planning documents.
- Added a Python package skeleton and development tooling baseline.
- Added core MCP schema models, safety policy, debug state machine, audit JSONL
  writer, and initial GDB/MI parser foundations.
- Added coverage enforcement, MI command serialization, async MI controller,
  generic remote backend, session manager, debug session orchestration,
  FastMCP metadata app, snapshot capture, and Cortex-M fault analysis.
- Updated CI to run on every pushed commit and added a policy/audit-backed
  tool execution service for primitive target operations, snapshots, and fault
  analysis.
- Wired FastMCP tool registrations to the tool execution service for primitive
  target operations, snapshot capture, and fault analysis.

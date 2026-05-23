# ADR 0001: Python Local-First Core

## Status

Accepted.

## Context

ProbeMCP aims to provide safe AI-assisted embedded debugging through
GDB-compatible tools. The first version needs fast iteration, strong local
developer ergonomics, and room for embedded-specific analyzers.

## Decision

Use Python 3.12+ for the open-source core.

The core will use:

- the official Python MCP SDK,
- `asyncio` for subprocess orchestration,
- `pydantic` for tool schemas,
- a custom GDB/MI controller,
- SQLite and JSONL for local audit/snapshot storage,
- `pytest`, `ruff`, and `mypy` for quality gates.

## Consequences

Benefits:

- fast prototyping,
- easy analyzer development,
- strong fit with MCP server workflows,
- simple local installation.

Costs:

- packaging external debuggers remains a user/environment concern,
- subprocess and timeout behavior must be engineered carefully,
- long-running process state must be explicit and tested.

The project should treat Python as the control-plane language, not as a loose
script wrapper around GDB.

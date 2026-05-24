---
name: probemcp-core-development
description: Develop and verify ProbeMCP Python core changes. Use when working in this repository on MCP tools/resources, pydantic schemas, ToolService behavior, session management, GDB/MI orchestration, snapshots, analyzers, audit logging, config, CLI, tests, or CI quality gates.
---

# ProbeMCP Core Development

## Workflow

Start by reading the current implementation before designing changes. Prefer these entry points:

- MCP app/tool surface: `src/probemcp/mcp_server/app.py`, `tools.py`, `schemas.py`, `service.py`
- GDB/MI core: `src/probemcp/mi/commands.py`, `controller.py`, `parser.py`, `records.py`
- sessions/backends: `src/probemcp/debug/session.py`, `src/probemcp/backends/`
- analyzers/snapshots: `src/probemcp/analyzers/`, `src/probemcp/snapshots/`
- safety/config/audit: `src/probemcp/safety/`, `src/probemcp/config.py`, `src/probemcp/audit/`

Keep the product principle intact: ProbeMCP exposes structured, safe tools, not raw arbitrary GDB or shell execution.

## Change Rules

- Extend public MCP schemas in `schemas.py` first, then wire service/app/tool registry behavior.
- Keep `ToolResult` responses structured and stable; failures need `DebugError`.
- Add or update tests beside the touched layer. Do not rely only on end-to-end tests.
- Keep hardware and live QEMU paths opt-in. Default CI must stay deterministic and hardware-free.
- Use fake transports, fake sessions, MI transcript fixtures, and parser corpus tests before requiring real tools.
- Preserve strict typing and pydantic validation. Avoid broad `Any` unless isolating protocol boundaries.
- Update docs when behavior changes public tool contracts, safety posture, backend support, or release process.

## Validation

Use `scripts/check_repo.sh` from this skill for the standard repo quality gate:

```bash
.codex/skills/probemcp-core-development/scripts/check_repo.sh
```

For smaller edits, run targeted tests first, then the full script before finalizing. The full expected gate is:

- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest`
- `uv run ruff check . --select S --ignore S101,S105,S106`
- `uvx pip-audit --progress-spinner off`
- `uv build`

## References

Read `references/repo-map.md` when you need a compact map of module ownership and test placement.

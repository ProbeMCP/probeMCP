# ProbeMCP Repo Map

## Public Contracts

- `src/probemcp/mcp_server/schemas.py`: public request/response/error models.
- `src/probemcp/mcp_server/tools.py`: static tool metadata, permissions, and timeout defaults.
- `src/probemcp/mcp_server/app.py`: FastMCP tool/resource registration.
- `docs/tool-contracts.md`: human-facing contract documentation.

When changing a tool, update schema, service, app registration, registry metadata, tests, and docs together.

## Execution Path

1. MCP client calls a tool in `app.py`.
2. Request is validated by pydantic schema models.
3. `ToolService` checks safety policy and resource limits.
4. `SessionManager` resolves the session.
5. `DebugSession` calls allowlisted MI commands through `MIController`.
6. Backend adapters isolate target-specific behavior.
7. Results are returned through `ToolResult` and optionally audited.

## Test Placement

- Schema and contract tests: `tests/test_mcp_schemas.py`, `tests/test_mcp_app.py`
- Service behavior: `tests/test_tool_service.py`
- GDB/MI parser/controller: `tests/test_mi_parser.py`, `tests/test_mi_controller.py`, `tests/test_mi_transcript_corpus.py`
- Debug sessions/backends: `tests/test_backend_and_session.py`, `tests/test_adapter_conformance.py`
- Safety: `tests/test_safety_policy.py`, `tests/test_safety_confirmation_and_privacy.py`
- Analyzers/snapshots: `tests/test_cortexm_fault_analyzer.py`, `tests/test_snapshot_service.py`
- Config/CLI/package: `tests/test_config_and_diagnostics.py`, `tests/test_cli.py`, `tests/test_package.py`

## Non-Negotiables

- No `execute_gdb_command` MCP tool.
- No shell execution from MCP tool arguments.
- GDB starts with `--nx --nh`.
- Monitor commands must be adapter-owned and allowlisted.
- Production/lab hardware operations require explicit policy interlocks.
- CI remains hardware-free unless an integration marker and env flag opt in.

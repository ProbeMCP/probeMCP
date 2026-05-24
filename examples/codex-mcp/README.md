# Codex MCP Integration Example

This example documents a real Codex-to-ProbeMCP connection over MCP stdio and
the safe cases that should work before connecting to hardware.

It validates the client integration layer only. It does not attach to a QEMU
target or physical board. Live target tests remain opt-in because they require
local toolchains, board access, or an emulator process.

## Codex Configuration

Add a ProbeMCP server entry to your Codex config and replace both absolute
paths:

```toml
[mcp_servers.probemcp]
type = "stdio"
command = "/ABS/PATH/TO/uv"
args = [
  "--directory",
  "/ABS/PATH/TO/probeMCP",
  "run",
  "probemcp",
  "serve",
]
startup_timeout_sec = 15
tool_timeout_sec = 120
```

On this workstation, the concrete entry used for validation was:

```toml
[mcp_servers.probemcp]
type = "stdio"
command = "/Users/chamnp/.local/bin/uv"
args = [
  "--directory",
  "/Users/chamnp/workspace/outsource/debuggerMCP",
  "run",
  "probemcp",
  "serve",
]
startup_timeout_sec = 15
tool_timeout_sec = 120
```

## Real Codex Validation

Validated on May 24, 2026 with:

```bash
codex exec --full-auto -C /Users/chamnp/workspace/outsource/debuggerMCP \
  -c 'model_reasoning_effort="high"' \
  -c 'mcp_servers.atms.command="/usr/bin/true"' \
  -c 'mcp_servers.atms.args=[]' \
  "Use the ProbeMCP MCP server. Call list_supported_tools, read probemcp://schema if available, then call read_registers with session_id=missing. Report the tool names count, whether execute_gdb_command is exposed, and the missing-session error. Do not edit files."
```

The `mcp_servers.atms` overrides are local to this machine. They bypass an
unrelated legacy MCP config entry that this Codex CLI build cannot deserialize.
They are not required for a clean Codex configuration.

Observed result:

- Codex called `probemcp.list_supported_tools({})` successfully.
- Codex called `probemcp.read_registers({"session_id": "missing"})` successfully.
- `execute_gdb_command` was not exposed.
- Missing session returned structured error code `SESSION_NOT_FOUND`.
- This Codex CLI build did not expose an MCP resource-read tool to the agent,
  so `probemcp://schema` is covered by the stdio smoke script below.

## Reproducible Stdio Smoke Test

Run from the repository root:

```bash
uv run python examples/codex-mcp/stdio_smoke.py
```

Expected checks:

- MCP server starts over stdio.
- `list_tools` includes the structured ProbeMCP tools.
- `execute_gdb_command` is absent.
- `probemcp://schema` includes exported JSON schemas.
- `read_registers` with `session_id="missing"` returns `SESSION_NOT_FOUND`.

To start the server exactly as Codex would through `uv`, pass the command and
arguments explicitly:

```bash
uv run python examples/codex-mcp/stdio_smoke.py \
  --server-command /Users/chamnp/.local/bin/uv \
  --server-arg --directory \
  --server-arg /Users/chamnp/workspace/outsource/debuggerMCP \
  --server-arg run \
  --server-arg probemcp \
  --server-arg serve
```

The smoke test exits non-zero if the raw GDB escape hatch appears, schema
metadata cannot be read, or the safe error path stops returning
`SESSION_NOT_FOUND`.

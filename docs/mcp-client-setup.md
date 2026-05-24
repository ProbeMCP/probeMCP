# MCP Client Setup

ProbeMCP runs as a local stdio MCP server.

```shell
uv sync --extra dev
uv run probemcp doctor --config probemcp.toml
uv run probemcp serve --config probemcp.toml
```

Example config:

```toml
schema_version = 1
default_target = "qemu-demo"

[server]
permission_mode = "confirm-required"
target_class = "emulator"
audit_log_path = ".probemcp/audit.jsonl"

[targets.qemu-demo]
backend = "qemu"
endpoint = "localhost:3333"
gdb_path = "arm-none-eabi-gdb"
elf_path = "build/firmware.elf"
profile = "cortex-m"
```

## Claude Desktop

Add a server entry that launches:

```shell
uv run probemcp serve --config /absolute/path/probemcp.toml
```

## Cursor and Codex

Use the same stdio command in the client MCP server configuration. Keep the
config path absolute so the client does not depend on its current directory.

For a concrete Codex configuration, real `codex exec` validation command, and
reproducible MCP stdio smoke test, see
[`examples/codex-mcp`](../examples/codex-mcp/README.md).

## Safety Modes

- `readonly`: inspection only.
- `confirm-required`: target-changing tools return a confirmation token first.
- `full-control`: required for memory writes, but writes still need explicit
  enablement and confirmation.

ProbeMCP intentionally does not expose arbitrary GDB command execution or shell
execution.

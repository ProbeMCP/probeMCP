# Safety Model

ProbeMCP is designed for AI-assisted debugging of real embedded systems. The
safety model is a core product feature.

## Permission Modes

### `readonly`

Allows observation-only tools:

- list sessions
- read cached session state
- read registers if the target is already halted
- read memory if the address range is allowed
- inspect snapshots
- analyze snapshots
- compare snapshots

Disallowed:

- halt
- resume
- step
- reset
- breakpoints
- memory writes
- flash operations
- arbitrary GDB commands
- arbitrary shell commands

### `confirm-required`

Allows target-changing actions only after explicit user confirmation or a
valid confirmation token. This is the recommended default for local hardware.

Examples:

- halt
- bounded resume
- step instruction
- set or clear breakpoint
- reset non-production target

### `full-control`

Allows higher-risk actions when enabled by local policy:

- memory writes to explicitly allowed RAM ranges
- reset on approved targets
- adapter-specific control actions

Even in `full-control`, ProbeMCP should not expose arbitrary shell execution,
arbitrary GDB command execution, or flash programming in v0.1.

## Hard Rules

- Do not expose a general `execute_gdb_command` MCP tool.
- Do not execute shell commands from MCP tool arguments.
- Start GDB with `--nx --nh` by default to avoid implicit local init scripts.
- Use allowlisted MI commands.
- Use adapter-owned allowlists for any required monitor commands.
- Bound all resume/continue operations with a timeout or explicit stop policy.
- If target state becomes uncertain, mark the session as `unknown` or
  `degraded`.
- Record audit events before and after state-changing actions.
- Require explicit production-target opt-in for reset or writes.
- Reject writes outside configured writable memory ranges.

## Confirmation Tokens

Confirmation tokens should be short-lived and bound to:

- session id
- tool name
- normalized request payload
- target fingerprint
- expiration timestamp

Changing any material argument invalidates the token.

## Memory Write Policy

v0.1 should default to no memory writes. When enabled later, writes should
require:

- `full-control`
- configured memory map
- writable region match
- maximum length
- optional compare-before-write value
- audit log entry

## Runaway Execution Prevention

`resume` should accept a bounded execution policy:

- `max_run_ms`
- `stop_on_breakpoint`
- `auto_interrupt`

If the timeout expires and `auto_interrupt` is true, ProbeMCP should interrupt
the target. If interrupt fails, the session state must become `unknown`.

## Resource Limits

Default local limits are intentionally conservative:

- active sessions: 4
- memory read size: 4096 bytes
- memory write size: 256 bytes, and still disabled unless policy enables it
- snapshot stack capture: 4096 bytes
- concurrent tool calls: 8
- active operations per session: 1
- queued MI commands per controller: 32

Limit failures return structured `RESOURCE_LIMIT_EXCEEDED` errors and are
recorded in the audit log when audit logging is configured.

## Hardware Interlocks

`lab-hardware` and `production-hardware` targets require explicit local
`hardware_operation_allowlist` opt-in before target-changing operations can run.
Production hardware also requires a fresh confirmation token for high-risk
control operations even when the server is in `full-control` mode.

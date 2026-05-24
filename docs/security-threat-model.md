# Security Threat Model

ProbeMCP is a local MCP server that can control debugger sessions and, in later
phases, physical hardware. The core security assumption is that structured MCP
tools are safer than exposing arbitrary GDB or shell command execution.

## Assets

- developer firmware, symbols, source paths, and ELF metadata
- target memory, registers, peripheral state, and serial logs
- physical hardware safety, reset state, and power state
- local audit logs, snapshots, and GDB/MI transcripts
- configured debugger paths and target profiles

## Trust Boundaries

- AI client to ProbeMCP MCP server
- ProbeMCP to GDB subprocess
- GDB to remote debugger server or emulator
- debugger server to real hardware
- local logs and diagnostics to public bug reports

## Attacker Capabilities

ProbeMCP should assume the AI client can receive hostile instructions from a
workspace, prompt, debug note, README, crash log, or generated analysis. The
attacker may not control ProbeMCP directly, but can try to make the AI client
request unsafe tool calls.

ProbeMCP should also assume a local workspace can contain hostile paths,
symbol names, ELF metadata, launch configuration, or transcript content. Local
configuration is not a trusted security boundary unless it has already been
validated against the active policy.

The threat model does not assume arbitrary local code execution has already
happened. If an attacker can replace the ProbeMCP package, the configured GDB
binary, or the Python interpreter, the host is outside this model.

## Boundary Requirements

- MCP tool arguments are untrusted input even when they come from a trusted AI
  client.
- Debugger paths, ELF paths, workspace paths, and target profile names must be
  normalized and policy-checked before use.
- GDB must start with `--nx --nh` so local `.gdbinit` files and home-directory
  init files are not implicitly trusted.
- GDB/MI commands must be selected from structured tool implementations, not
  assembled from arbitrary user-controlled strings.
- Adapter-specific monitor commands must stay behind explicit adapter
  allowlists.
- Target-changing actions must require the configured permission mode and
  audit entry before execution.
- Diagnostic output intended for public issues must be redacted before it
  leaves the local machine.

## Abuse Paths

- prompt-injected AI client repeatedly resumes or resets a target
- malicious workspace config points `gdb_path` at an unsafe executable
- oversized memory reads flood the debugger or leak private firmware data
- arbitrary monitor commands flash, erase, or reset hardware
- logs and transcripts leak usernames, source paths, symbols, or memory dumps
- untrusted ELF paths use traversal or symlink behavior to escape an allowed
  workspace
- debugger arguments smuggle command execution through init files, command
  files, or shell-like wrappers
- hostile symbols, serial logs, or fault text inject instructions into an AI
  client's later analysis prompt
- an AI client requests production hardware reset/write actions after reading
  malicious workspace instructions
- audit summaries expose target serial numbers, probe identifiers, or
  confirmation tokens in public bug reports

## Required Mitigations

- no raw `execute_gdb_command` MCP tool
- no arbitrary shell execution MCP tool
- confirmation-token flow for target-changing operations
- full-control requirement for memory writes
- production hardware reset/write blocked by default
- local-only config and audit storage by default
- redaction guidance for shared logs and transcripts
- resource limits for sessions and memory reads

## Security Test Matrix

| Area | Scenario | Expected check |
| --- | --- | --- |
| Raw command exposure | MCP client asks for a general GDB command tool | Tool registry has no raw GDB command or shell execution tool |
| GDB startup | Workspace contains `.gdbinit` or home init side effects | GDB is launched with `--nx --nh` |
| Debugger path | `gdb_path` points outside allowed executables or to a wrapper | Config validation rejects or requires explicit trusted local configuration |
| ELF path | ELF path contains traversal, symlink escape, or non-file target | Path normalization rejects paths outside the configured workspace/profile |
| Memory read limits | Client requests a huge or unbounded memory range | Request is bounded by maximum length and allowed address ranges |
| Target-changing calls | Client requests halt, resume, reset, breakpoint, or future write | Policy checks permission mode before backend invocation |
| Confirmation replay | Client reuses a token with changed arguments or target | Token binding rejects changed session, tool, payload, target, or expiration |
| Monitor commands | Adapter needs a backend-specific monitor command | Command must come from adapter allowlist, not MCP input |
| Production hardware | Client requests reset/write on a production target | Operation blocks unless production target opt-in and permission mode allow it |
| Prompt-injected logs | Fault text or serial output contains agent-directed instructions | Output is treated as data and does not change policy or tool availability |
| Audit leakage | User shares logs from a failed session | Redaction removes paths, tokens, serials, probe IDs, and large memory dumps |
| Unknown state | Resume timeout or interrupt fails | Session becomes `unknown` or `degraded` and follow-up calls are constrained |

Each scenario should become either an automated test, a documented manual test,
or a follow-up issue before ProbeMCP is treated as safe for real hardware.

## Traceability

Safety requirements should be traceable from this document to implementation
checks:

- tool availability: registry tests prove raw GDB and shell tools are absent
- command construction: MI/controller tests prove allowlisted structured
  commands are used
- path handling: config/session tests prove debugger and ELF paths are
  normalized before use
- permission gates: safety policy tests prove target-changing tools are gated
- redaction: audit logger tests prove sensitive diagnostics are removed
- uncertain target state: session manager tests prove failed stop/interrupt
  paths degrade the session state

Security-sensitive bugs should be reported privately through GitHub security
advisories when enabled.

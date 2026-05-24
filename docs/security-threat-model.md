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

## Abuse Paths

- prompt-injected AI client repeatedly resumes or resets a target
- malicious workspace config points `gdb_path` at an unsafe executable
- oversized memory reads flood the debugger or leak private firmware data
- arbitrary monitor commands flash, erase, or reset hardware
- logs and transcripts leak usernames, source paths, symbols, or memory dumps

## Required Mitigations

- no raw `execute_gdb_command` MCP tool
- no arbitrary shell execution MCP tool
- confirmation-token flow for target-changing operations
- full-control requirement for memory writes
- production hardware reset/write blocked by default
- local-only config and audit storage by default
- redaction guidance for shared logs and transcripts
- resource limits for sessions and memory reads

Security-sensitive bugs should be reported privately through GitHub security
advisories when enabled.

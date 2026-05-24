# Privacy and Redaction

ProbeMCP is local-first and does not upload audit logs, snapshots, transcripts,
or serial logs by default. Users may still accidentally share sensitive data in
bug reports, so diagnostics should be sanitized before posting publicly.

## Sensitive Data

- firmware and ELF paths
- usernames and workspace directories
- symbols and source locations from proprietary firmware
- memory dumps and stack contents
- serial logs containing credentials or device identifiers
- target serial numbers and probe identifiers
- confirmation tokens and future policy tokens

## Redaction Rules

- replace absolute paths with the basename when possible
- truncate long hex dumps unless the exact bytes are required
- remove secrets, credentials, tokens, and private keys
- prefer small GDB/MI transcript excerpts over full logs
- include ProbeMCP version, backend, target class, and sanitized error code

The codebase includes redaction helpers for audit summaries, but maintainers
should still treat user-provided logs as potentially sensitive.

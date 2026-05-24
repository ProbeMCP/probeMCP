# Safety Checklist

## Policy Surface

- Add new operations to `DebugOperation` and classify them in `READ_ONLY_OPERATIONS`, `TARGET_CHANGING_OPERATIONS`, or a dedicated high-risk branch.
- Return `PolicyDecision` with useful `reason`, `required_permission`, and `warnings`.
- Prefer denial by default for memory writes, reset-like behavior, production hardware, lab hardware, and future flash operations.

## Tool Service

- Evaluate policy before session lookup or execution where practical.
- Enforce resource limits before target I/O.
- Preserve `ToolResult` shape on success and failure.
- Audit both denied and executed operations when an audit writer is configured.
- Include policy warnings in the result and audit event.

## Target State

- Keep target state explicit: `disconnected`, `connecting`, `halted`, `running`, `unknown`, `degraded`.
- Bound resume/continue with timeout and auto-interrupt policy.
- Mark session `degraded` when interrupt or cleanup fails after timeout.

## Tests

- Add direct policy unit tests for every permission mode and target class touched.
- Add service tests that assert the target method was not called on deny.
- Add audit/log tests when warning/error behavior changes.
- Keep QEMU/hardware validation opt-in with markers and environment flags.

## Documentation

Update `docs/safety-model.md`, `docs/security-threat-model.md`, or `docs/tool-contracts.md` when public posture changes.

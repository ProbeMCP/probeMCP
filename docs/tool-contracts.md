# Tool Contracts

This document defines the first draft of ProbeMCP tool contracts. Schemas are
intentionally structured so AI clients can reason about debugging operations
without relying on raw debugger commands.

## Response Envelope

All tools should return a common envelope:

```json
{
  "ok": true,
  "session_id": "session_01",
  "target_state": "halted",
  "data": {},
  "warnings": [],
  "audit_id": "audit_01",
  "error": null
}
```

Error shape:

```json
{
  "code": "TARGET_RUNNING_REQUIRES_HALT",
  "message": "The target must be halted before reading core registers.",
  "category": "target",
  "retryable": true,
  "details": {},
  "required_permission": "confirm-required",
  "confirmation_token": null
}
```

## Primitive Tools

### `connect_target`

Permission: `readonly` for emulator attach, `confirm-required` for hardware.

Request:

```json
{
  "backend": "qemu",
  "gdb_path": "arm-none-eabi-gdb",
  "elf_path": "build/firmware.elf",
  "endpoint": "localhost:3333",
  "profile": "cortex-m",
  "timeout_ms": 30000
}
```

Response data:

```json
{
  "session_id": "session_01",
  "backend": "qemu",
  "architecture": "arm",
  "profile": "cortex-m",
  "state": "halted"
}
```

### `disconnect_target`

Permission: `confirm-required`.

Request:

```json
{
  "session_id": "session_01",
  "kill_backend": false,
  "timeout_ms": 5000
}
```

### `halt`

Permission: `confirm-required`.

Request:

```json
{
  "session_id": "session_01",
  "timeout_ms": 2000
}
```

Response data:

```json
{
  "stop_reason": "signal-received",
  "pc": "0x08001234"
}
```

### `resume`

Permission: `confirm-required`.

Request:

```json
{
  "session_id": "session_01",
  "max_run_ms": 1000,
  "auto_interrupt": true
}
```

### `step_instruction`

Permission: `confirm-required`.

Request:

```json
{
  "session_id": "session_01",
  "count": 1,
  "timeout_ms": 5000
}
```

### `reset_target`

Permission: `confirm-required` or `full-control`, depending on target policy.

Request:

```json
{
  "session_id": "session_01",
  "mode": "halt",
  "timeout_ms": 10000
}
```

### `read_registers`

Permission: `readonly`.

Request:

```json
{
  "session_id": "session_01",
  "group": "core"
}
```

Response data:

```json
{
  "registers": {
    "pc": "0x08001234",
    "lr": "0xfffffff9",
    "sp": "0x20001000",
    "xpsr": "0x01000003"
  }
}
```

### `read_memory`

Permission: `readonly`.

Request:

```json
{
  "session_id": "session_01",
  "address": "0x20000000",
  "length": 64,
  "width": 4,
  "timeout_ms": 3000
}
```

### `write_memory`

Permission: `full-control`.

v0.1 should define the schema but keep this disabled by default.

Request:

```json
{
  "session_id": "session_01",
  "address": "0x20000000",
  "data_hex": "01020304",
  "expected_old_hex": "00000000",
  "timeout_ms": 3000
}
```

### `set_breakpoint`

Permission: `confirm-required`.

Request:

```json
{
  "session_id": "session_01",
  "location": {
    "kind": "symbol",
    "value": "main"
  },
  "type": "hardware",
  "temporary": false,
  "timeout_ms": 3000
}
```

### `clear_breakpoint`

Permission: `confirm-required`.

Request:

```json
{
  "session_id": "session_01",
  "breakpoint_id": "1",
  "timeout_ms": 3000
}
```

## High-Level Tools

### `debug_snapshot`

Permission: `readonly`, or `confirm-required` if the tool must halt the target.

Request:

```json
{
  "session_id": "session_01",
  "halt_policy": "require_already_halted",
  "include_core_registers": true,
  "include_fault_registers": true,
  "include_stack": true,
  "stack_bytes": 128
}
```

Response data:

```json
{
  "snapshot_id": "snapshot_01",
  "state": "halted",
  "summary": "Target halted in HardFault handler at 0x08001234."
}
```

### `analyze_fault`

Permission: `readonly`.

Request:

```json
{
  "session_id": "session_01",
  "snapshot_id": "snapshot_01"
}
```

Response data:

```json
{
  "fault_type": "UsageFault: INVSTATE",
  "confidence": 0.87,
  "evidence": [
    "CFSR.UFSR.INVSTATE is set",
    "LR has an EXC_RETURN value",
    "xPSR T-bit evidence suggests invalid execution state"
  ],
  "hypotheses": [
    "Branch to an invalid non-Thumb address",
    "Corrupted function pointer or return address"
  ],
  "recommended_next_actions": [
    "Inspect the stacked PC symbol and disassembly",
    "Inspect LR and the call stack",
    "Review code paths that write function pointers"
  ]
}
```

### `compare_snapshots`

Permission: `readonly`.

Request:

```json
{
  "before_snapshot_id": "snapshot_01",
  "after_snapshot_id": "snapshot_02",
  "include_memory_diffs": false
}
```

### `explain_current_state`

Permission: `readonly`.

Request:

```json
{
  "session_id": "session_01",
  "snapshot_id": "snapshot_01",
  "detail_level": "normal"
}
```

### `suggest_next_debug_steps`

Permission: `readonly`.

Request:

```json
{
  "session_id": "session_01",
  "snapshot_id": "snapshot_01",
  "goal": "Find the likely cause of the HardFault"
}
```

Response data should return ranked actions with risk level, permission level,
and expected evidence.

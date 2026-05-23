# Backend Adapters

Backend adapters isolate debugger and vendor-specific behavior from the core
MCP tools.

## Adapter Interface

Each adapter should define:

- backend name
- supported target profiles
- connection strategy
- reset strategy
- halt strategy
- target fingerprint strategy
- supported features
- known quirks

## Initial Adapters

### Generic Remote

For an already-running `gdbserver` or compatible GDB remote endpoint.

Responsibilities:

- validate endpoint
- connect using `-target-select remote` or `extended-remote`
- avoid backend-specific monitor commands

### QEMU

For local emulator workflows.

Responsibilities:

- optionally spawn QEMU
- connect to QEMU gdbstub
- provide deterministic integration tests
- support a Cortex-M HardFault demo

### OpenOCD

For common hardware debug probes and MCUs.

Responsibilities:

- attach to an existing OpenOCD server in v0.1
- later optionally spawn OpenOCD with explicit config files
- expose allowlisted reset/halt monitor actions

### J-Link GDB Server

For SEGGER J-Link workflows.

Responsibilities:

- attach to an existing J-Link GDB Server in v0.1
- document reset/halt quirks
- avoid arbitrary monitor command exposure

### pyOCD

For CMSIS-DAP and Python-native probe workflows.

Responsibilities:

- attach to a pyOCD GDB server initially
- evaluate a native pyOCD adapter later if it improves reliability

## Conformance Tests

Each adapter should eventually pass common conformance tests:

- connect
- disconnect
- halt
- bounded resume
- read core registers
- read memory
- set hardware breakpoint
- clear breakpoint
- capture snapshot
- recover from timeout

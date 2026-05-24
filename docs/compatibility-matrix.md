# Compatibility Matrix

This matrix is intentionally conservative. A backend is considered validated
only when there is a repeatable test, sanitized transcript, or maintainer
validation report.

| Backend | Status | Default CI | Notes |
| --- | --- | --- | --- |
| Generic remote gdbserver | Foundation | Unit tests | Attach-only through GDB/MI. |
| QEMU gdbstub | Experimental | Unit tests only | Live QEMU test should stay opt-in. |
| OpenOCD | Experimental | Unit tests only | Monitor actions must be allowlisted. |
| J-Link GDB Server | Skeleton | Unit tests only | Attach-only; quirks need validation. |
| pyOCD GDB server | Skeleton | Unit tests only | Native pyOCD adapter is future work. |

| Target Profile | Status | Notes |
| --- | --- | --- |
| ARM Cortex-M | Active MVP | Fault analyzer and register normalization exist. |
| RISC-V | Planned | Target profile abstraction exists; analyzer missing. |
| Xtensa / ESP32 | Planned | Requires debugger transcript research. |
| Cortex-A | Planned | Requires architecture-specific run-control assumptions. |

Validation reports should include backend version, GDB version, host OS, target
MCU/SoC, supported operations, known quirks, and sanitized transcript excerpts.

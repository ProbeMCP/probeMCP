# Commercial and Open-Core Boundaries

The open-source core should remain useful as a local-first embedded debugging
MCP server without any hosted service.

## Open-Source Core

- structured MCP tools
- GDB/MI orchestration
- local safety policy
- local audit logging
- generic/QEMU/OpenOCD/J-Link/pyOCD adapters
- Cortex-M analysis
- SVD/RTOS/lab extension points

## Possible Commercial Layers

- hosted team dashboard for uploaded snapshots and audit logs
- hardware lab scheduling
- enterprise policy management
- proprietary vendor adapters
- support and certification for validated hardware/backend combinations

Hosted features must not become a runtime dependency for the local OSS core.

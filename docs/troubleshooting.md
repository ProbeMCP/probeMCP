# Troubleshooting

Start with:

```shell
uv run probemcp doctor --config path/to/probemcp.toml
```

## Common Errors

`SESSION_FACTORY_UNAVAILABLE`

The in-process test server was created without a real GDB session factory. Use
`probemcp serve` for the configured runtime path.

`CONFIRMATION_REQUIRED`

The operation changes target state. Retry the exact same request with the
returned confirmation token if the action is intentional.

`INVALID_CONFIRMATION_TOKEN`

The token expired, was already used, or belongs to a different request.

`RESOURCE_LIMIT_EXCEEDED`

The request exceeds configured local limits, usually active sessions or memory
read size.

`SNAPSHOT_NOT_FOUND`

The snapshot ID is missing from the current local server process. Capture a new
snapshot or use the correct server instance.

## Backend Checks

- confirm the GDB executable exists
- confirm the debugger server endpoint is reachable
- keep QEMU and hardware integration tests opt-in
- avoid production hardware until the target profile and safety mode are
  explicit

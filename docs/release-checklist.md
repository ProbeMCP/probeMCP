# v0.1 Release Checklist

## Required Checks

- `uv run ruff check .`
- `uv run ruff check . --select S --ignore S101,S105,S106`
- `uv run mypy src`
- `uv run pytest`
- `uv build`
- `uvx pip-audit --progress-spinner off`

## Required Review

- no raw GDB command MCP tool
- no arbitrary shell command MCP tool
- target-changing tools are permission-gated
- memory writes are disabled by default
- audit logging works for success and failure paths
- QEMU/hardware tests are opt-in, not default CI blockers
- compatibility matrix reflects actual validation evidence

## Release Artifacts

- source distribution
- wheel
- changelog entry
- docs for MCP client setup
- known limitations and hardware validation status

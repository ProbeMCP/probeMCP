# Contributing

ProbeMCP is early. Contributions should prioritize safety, deterministic
debugging behavior, and clear tool contracts over broad feature coverage.

## Development Priorities

1. GDB/MI controller reliability
2. QEMU-based integration tests
3. safety policy enforcement
4. Cortex-M fault analysis
5. backend adapter conformance tests

## Local Development

Recommended tools:

- Python 3.12+
- `uv`
- `ruff`
- `mypy`
- `pytest`

Example setup:

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
```

You can also run:

```bash
make check
make build
```

## Contribution Rules

- Do not add a raw arbitrary GDB command MCP tool.
- Do not add arbitrary shell execution through MCP tool input.
- Add tests for parser, safety policy, and session-state changes.
- Treat target-changing behavior as high risk.
- Document backend-specific quirks.
- Prefer structured schemas over free-form strings.

## Pull Requests

Pull requests should describe:

- what changed,
- why it changed,
- target-safety impact,
- validation performed,
- backend-specific assumptions.

Changes that affect GDB/MI parsing, session state, safety policy, or analyzer
output should include tests.

## Commit Style

Use concise imperative commit messages, for example:

```text
Add initial GDB MI parser
Document safety policy
Implement QEMU backend skeleton
```

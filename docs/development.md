# Development

ProbeMCP uses Python 3.12+, `uv`, `ruff`, `mypy`, and `pytest`.

## Setup

```bash
uv sync --extra dev
```

## Common Commands

```bash
uv run pytest
uv run ruff check .
uv run mypy src
uv build
```

Or use Make:

```bash
make check
make build
```

## Quality Bar

New code should be:

- typed,
- covered by focused tests,
- deterministic under timeout,
- explicit about target state,
- conservative about target-changing behavior,
- documented when it adds backend-specific behavior.

## Test Strategy

The test suite should grow in layers:

1. unit tests for schemas, policies, and analyzers,
2. transcript tests for GDB/MI parsing,
3. fake-process tests for session state transitions,
4. QEMU integration tests,
5. optional hardware-backed adapter conformance tests.

Hardware-backed tests should be opt-in and skipped by default in CI.

## Summary

<!-- What changed and why? -->

## Safety Impact

<!-- Describe target-state changes, debugger commands, memory writes, reset behavior, or permission changes. -->

## Validation

<!-- List commands run, hardware/emulator tested, and relevant logs. -->

- [ ] `uv run ruff check .`
- [ ] `uv run mypy src`
- [ ] `uv run pytest`

## Checklist

- [ ] This change does not expose arbitrary GDB command execution.
- [ ] This change does not expose arbitrary shell execution.
- [ ] Target-changing behavior is permission-gated.
- [ ] New parser, policy, or session behavior has tests.
- [ ] Backend-specific quirks are documented.

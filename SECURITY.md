# Security Policy

ProbeMCP controls debuggers that may interact with real hardware. Security and
safety issues should be treated seriously.

## Supported Versions

The project is pre-release. Security fixes will target the main branch until
versioned releases begin.

## Reporting Issues

Please avoid publishing exploit details before maintainers have had time to
respond. Open a GitHub security advisory or contact the maintainers privately
when advisory support is available for the repository.

## High-Risk Areas

- arbitrary shell execution
- arbitrary GDB command execution
- unsafe memory writes
- flash programming
- production hardware reset
- path injection in debugger/backend launch arguments
- unbounded target execution
- incorrect target state reporting

## Baseline Safety Requirements

- GDB subprocesses must be spawned without shell interpolation.
- GDB should run with `--nx --nh` by default.
- Target-changing tools must pass through policy checks.
- All target-changing tools must be audited.
- Memory writes must be disabled by default.
- Resume/continue operations must be bounded.
- Unknown target state must be reported as unknown, not guessed.

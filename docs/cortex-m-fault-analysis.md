# Cortex-M Fault Analysis MVP

The first high-value analyzer in ProbeMCP should focus on Cortex-M crash and
fault analysis.

## Inputs

Core registers:

- `PC`
- `LR`
- `SP`
- `MSP`
- `PSP`
- `xPSR`

System Control Block fault registers:

- `CFSR` at `0xE000ED28`
- `HFSR` at `0xE000ED2C`
- `DFSR` at `0xE000ED30`
- `MMFAR` at `0xE000ED34`
- `BFAR` at `0xE000ED38`

Exception metadata:

- `EXC_RETURN` decoded from `LR` when it matches the exception return pattern
- active exception number from `xPSR`
- stacked exception frame from `MSP` or `PSP`

## Output Shape

The analyzer should return:

- fault type
- confidence
- evidence
- hypotheses
- recommended next actions
- raw decoded register fields

Example:

```json
{
  "fault_type": "UsageFault: INVSTATE",
  "confidence": 0.87,
  "evidence": [
    "CFSR.UFSR.INVSTATE is set",
    "LR contains an EXC_RETURN value",
    "The active exception number indicates fault handler context"
  ],
  "hypotheses": [
    "Execution branched to an invalid non-Thumb address",
    "A function pointer or return address was corrupted"
  ],
  "recommended_next_actions": [
    "Resolve the stacked PC to a symbol",
    "Disassemble around the stacked PC",
    "Inspect stack memory around the selected SP",
    "Compare against a pre-fault snapshot if available"
  ]
}
```

## Minimum Decoding Rules

### `CFSR`

Decode the combined Configurable Fault Status Register:

- MemManage Status Register bits
- BusFault Status Register bits
- UsageFault Status Register bits
- valid `MMFAR`
- valid `BFAR`

### `HFSR`

Decode at least:

- `VECTTBL`
- `FORCED`
- `DEBUGEVT`

### `DFSR`

Decode debug event causes when available.

### `EXC_RETURN`

Decode:

- return mode
- stack pointer selection
- stack frame type
- security state later, where supported

## Analyzer Rules

- Do not produce a single-cause diagnosis without evidence.
- Always include confidence.
- Always distinguish direct evidence from hypothesis.
- Always recommend safe next actions before target-changing actions.
- Prefer snapshot-based analysis over live repeated target reads.

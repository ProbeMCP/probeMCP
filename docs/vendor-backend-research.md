# Vendor Backend Research

## ST-Link

ST-Link workflows are usually reached through OpenOCD, STM32CubeIDE GDB server,
or vendor-specific launchers. ProbeMCP should prefer attach-only GDB server
support first and avoid flashing or erase flows until explicit safety policies
exist.

Research required before a dedicated adapter:

- reset/halt monitor semantics
- hardware breakpoint limits
- memory-map behavior
- firmware programming commands to block
- sanitized GDB/MI transcripts

## NXP S32DBG

S32DBG support should start as a research spike because licensing, target
families, and launch flows vary. The first implementation should attach to an
already-running GDB-compatible endpoint and document quirks before adding any
spawn or reset behavior.

Required evidence:

- safe launch examples
- debugger version
- supported SoC family
- reset and halt behavior
- transcript for connect, halt, register read, memory read, breakpoint

# QEMU Cortex-M HardFault Demo

This example is a deterministic local validation target for ProbeMCP. It builds
a tiny Cortex-M3 firmware image that executes a Thumb `udf` instruction. With
UsageFault disabled at reset, the fault escalates to HardFault and leaves useful
CFSR/HFSR evidence for `debug_snapshot` and `analyze_fault`.

Required local tools:

- `arm-none-eabi-gcc`
- `arm-none-eabi-gdb`
- `qemu-system-arm`

Build the fixture:

```sh
make -C examples/qemu-cortexm-hardfault
```

Run QEMU with a GDB stub:

```sh
qemu-system-arm \
  -M lm3s6965evb \
  -cpu cortex-m3 \
  -kernel examples/qemu-cortexm-hardfault/build/hardfault.elf \
  -gdb tcp::3333 \
  -nographic \
  -serial none \
  -monitor none
```

Then connect ProbeMCP to `localhost:3333` with backend `qemu`, capture a
snapshot, and run `analyze_fault`. The opt-in pytest path uses the same fixture:

```sh
PROBEMCP_RUN_QEMU=1 uv run pytest tests/test_qemu_integration_opt_in.py
```

Default CI intentionally skips the live QEMU path because host images do not
guarantee the embedded toolchain or QEMU system emulator.

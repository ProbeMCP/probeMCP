import asyncio
import os
import shutil
from pathlib import Path

import pytest

from probemcp.debug.factory import create_gdb_debug_session
from probemcp.mcp_server.schemas import (
    AnalyzeFaultRequest,
    BackendKind,
    ConnectTargetRequest,
    DebugSnapshotRequest,
    HaltRequest,
    PermissionLevel,
)
from probemcp.mcp_server.service import ToolService
from probemcp.safety.policy import PolicyEngine, TargetClass
from probemcp.sessions.manager import SessionManager

EXAMPLE_DIR = Path(__file__).parents[1] / "examples" / "qemu-cortexm-hardfault"
ELF_PATH = EXAMPLE_DIR / "build" / "hardfault.elf"

def test_qemu_hardfault_fixture_sources_are_present() -> None:
    assert (EXAMPLE_DIR / "Makefile").exists()
    assert (EXAMPLE_DIR / "startup.s").exists()
    assert (EXAMPLE_DIR / "main.c").exists()
    assert (EXAMPLE_DIR / "linker.ld").exists()

@pytest.mark.integration_qemu
@pytest.mark.asyncio
async def test_qemu_hardfault_demo_is_opt_in(unused_tcp_port: int) -> None:
    """Run the end-to-end QEMU HardFault demo when local tools are available."""

    if os.environ.get("PROBEMCP_RUN_QEMU") != "1":
        pytest.skip("set PROBEMCP_RUN_QEMU=1 to run live QEMU integration tests")

    make = shutil.which("make")
    gcc = shutil.which("arm-none-eabi-gcc")
    gdb = shutil.which("arm-none-eabi-gdb")
    qemu = shutil.which("qemu-system-arm")
    missing = [
        name
        for name, path in {
            "make": make,
            "arm-none-eabi-gcc": gcc,
            "arm-none-eabi-gdb": gdb,
            "qemu-system-arm": qemu,
        }.items()
        if path is None
    ]
    if missing:
        pytest.skip(f"missing QEMU demo tools: {', '.join(missing)}")
    assert make is not None
    assert gcc is not None
    assert gdb is not None
    assert qemu is not None

    build = await asyncio.create_subprocess_exec(
        make,
        "-C",
        str(EXAMPLE_DIR),
        f"CC={gcc}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    build_output, _ = await build.communicate()
    assert build.returncode == 0, build_output.decode(errors="replace")

    qemu_process = await asyncio.create_subprocess_exec(
        qemu,
        "-M",
        "lm3s6965evb",
        "-cpu",
        "cortex-m3",
        "-kernel",
        str(ELF_PATH),
        "-gdb",
        f"tcp::{unused_tcp_port}",
        "-nographic",
        "-serial",
        "none",
        "-monitor",
        "none",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        await asyncio.sleep(0.5)
        service = ToolService(
            sessions=SessionManager(),
            policy=PolicyEngine(),
            session_factory=create_gdb_debug_session,
            permission_mode=PermissionLevel.FULL_CONTROL,
            target_class=TargetClass.EMULATOR,
        )
        connected = await service.connect_target(
            ConnectTargetRequest(
                backend=BackendKind.QEMU,
                endpoint=f"localhost:{unused_tcp_port}",
                gdb_path=gdb,
                elf_path=str(ELF_PATH),
                timeout_ms=10_000,
            )
        )
        assert connected.ok, connected.error
        assert connected.data is not None

        await service.halt(HaltRequest(session_id=connected.data.session_id, timeout_ms=3000))
        snapshot = await service.debug_snapshot(
            DebugSnapshotRequest(
                session_id=connected.data.session_id,
                include_stack=True,
                stack_bytes=32,
            )
        )
        assert snapshot.ok, snapshot.error
        assert snapshot.data is not None

        analysis = await service.analyze_fault(
            AnalyzeFaultRequest(snapshot_id=snapshot.data.snapshot_id)
        )
        assert analysis.ok, analysis.error
        assert analysis.data is not None
        assert "Fault" in analysis.data.fault_type
    finally:
        if qemu_process.returncode is None:
            qemu_process.terminate()
            try:
                await asyncio.wait_for(qemu_process.wait(), timeout=2)
            except TimeoutError:
                qemu_process.kill()
                await qemu_process.wait()

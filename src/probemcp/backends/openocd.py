"""OpenOCD backend adapter."""

from __future__ import annotations

from probemcp.backends.base import BackendConnection, BackendFeature
from probemcp.mcp_server.schemas import BackendKind, ResetMode, TargetState
from probemcp.mi.commands import interpreter_exec_console, target_select
from probemcp.mi.controller import MIController
from probemcp.targets import infer_architecture


class OpenOCDBackend:
    """Attach-only OpenOCD adapter with allowlisted monitor actions."""

    kind = BackendKind.OPENOCD

    async def connect(
        self,
        controller: MIController,
        *,
        endpoint: str,
        profile: str,
        timeout_ms: int,
    ) -> BackendConnection:
        """Attach to an already-running OpenOCD GDB server."""

        await controller.execute(target_select(endpoint), timeout_ms=timeout_ms)
        return BackendConnection(
            backend=self.kind,
            endpoint=endpoint,
            profile=profile,
            architecture=infer_architecture(self.kind, profile),
            state=TargetState.UNKNOWN,
            features=[
                BackendFeature.CONNECT,
                BackendFeature.HALT,
                BackendFeature.RESET,
                BackendFeature.BREAKPOINTS,
                BackendFeature.MEMORY_READ,
            ],
        )

    async def reset_target(
        self,
        controller: MIController,
        *,
        mode: ResetMode,
        timeout_ms: int,
    ) -> TargetState:
        """Reset through a fixed OpenOCD monitor allowlist."""

        monitor_command = "monitor reset halt" if mode == ResetMode.HALT else "monitor reset run"
        await controller.execute(interpreter_exec_console(monitor_command), timeout_ms=timeout_ms)
        return TargetState.HALTED if mode == ResetMode.HALT else TargetState.RUNNING

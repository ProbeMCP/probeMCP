"""QEMU gdbstub backend adapter."""

from __future__ import annotations

from probemcp.backends.base import BackendConnection, BackendFeature
from probemcp.mcp_server.schemas import BackendKind, TargetState
from probemcp.mi.commands import target_select
from probemcp.mi.controller import MIController
from probemcp.targets import infer_architecture


class QemuBackend:
    """Adapter for an already-running QEMU GDB stub."""

    kind = BackendKind.QEMU

    async def connect(
        self,
        controller: MIController,
        *,
        endpoint: str,
        profile: str,
        timeout_ms: int,
    ) -> BackendConnection:
        """Attach to QEMU through its GDB stub."""

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

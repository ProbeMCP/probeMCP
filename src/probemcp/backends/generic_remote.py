"""Generic remote gdbserver backend adapter."""

from __future__ import annotations

from probemcp.backends.base import BackendConnection, BackendFeature
from probemcp.mcp_server.schemas import BackendKind, TargetState
from probemcp.mi.commands import target_select
from probemcp.mi.controller import MIController


class GenericRemoteBackend:
    """Adapter for an already-running GDB remote endpoint."""

    kind = BackendKind.GENERIC_REMOTE

    async def connect(
        self,
        controller: MIController,
        *,
        endpoint: str,
        profile: str,
        timeout_ms: int,
    ) -> BackendConnection:
        """Attach to a generic GDB remote endpoint."""

        await controller.execute(target_select(endpoint), timeout_ms=timeout_ms)
        return BackendConnection(
            backend=self.kind,
            endpoint=endpoint,
            profile=profile,
            state=TargetState.UNKNOWN,
            features=[
                BackendFeature.CONNECT,
                BackendFeature.HALT,
                BackendFeature.BREAKPOINTS,
                BackendFeature.MEMORY_READ,
            ],
        )

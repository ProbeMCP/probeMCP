"""Vendor GDB-server adapter skeletons."""

from __future__ import annotations

from dataclasses import dataclass

from probemcp.backends.base import BackendConnection, BackendFeature
from probemcp.mcp_server.schemas import BackendKind, TargetState
from probemcp.mi.commands import target_select
from probemcp.mi.controller import MIController
from probemcp.targets import infer_architecture


@dataclass(frozen=True, slots=True)
class AttachOnlyVendorBackend:
    """Attach-only adapter for vendor GDB servers."""

    kind: BackendKind
    display_name: str

    async def connect(
        self,
        controller: MIController,
        *,
        endpoint: str,
        profile: str,
        timeout_ms: int,
    ) -> BackendConnection:
        """Attach to an already-running vendor GDB server."""

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
                BackendFeature.BREAKPOINTS,
                BackendFeature.MEMORY_READ,
            ],
        )


def jlink_backend() -> AttachOnlyVendorBackend:
    """Return an experimental J-Link GDB Server adapter."""

    return AttachOnlyVendorBackend(BackendKind.JLINK, "J-Link GDB Server")


def pyocd_backend() -> AttachOnlyVendorBackend:
    """Return an experimental pyOCD GDB server adapter."""

    return AttachOnlyVendorBackend(BackendKind.PYOCD, "pyOCD GDB server")

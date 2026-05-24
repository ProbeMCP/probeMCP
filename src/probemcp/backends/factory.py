"""Backend adapter factory."""

from __future__ import annotations

from probemcp.backends.base import BackendAdapter
from probemcp.backends.generic_remote import GenericRemoteBackend
from probemcp.backends.openocd import OpenOCDBackend
from probemcp.backends.qemu import QemuBackend
from probemcp.backends.vendor import jlink_backend, pyocd_backend
from probemcp.errors import ErrorCode
from probemcp.mcp_server.schemas import BackendKind


def create_backend(kind: BackendKind) -> BackendAdapter:
    """Create an adapter for a supported backend kind."""

    match kind:
        case BackendKind.GENERIC_REMOTE:
            return GenericRemoteBackend()
        case BackendKind.QEMU:
            return QemuBackend()
        case BackendKind.OPENOCD:
            return OpenOCDBackend()
        case BackendKind.JLINK:
            return jlink_backend()
        case BackendKind.PYOCD:
            return pyocd_backend()

    raise ValueError(f"{ErrorCode.UNSUPPORTED_BACKEND.value}: {kind.value}")

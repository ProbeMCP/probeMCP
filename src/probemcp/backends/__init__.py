"""Debugger backend adapters."""

from probemcp.backends.base import BackendAdapter, BackendConnection, BackendFeature
from probemcp.backends.factory import create_backend
from probemcp.backends.generic_remote import GenericRemoteBackend
from probemcp.backends.openocd import OpenOCDBackend
from probemcp.backends.qemu import QemuBackend
from probemcp.backends.vendor import AttachOnlyVendorBackend, jlink_backend, pyocd_backend

__all__ = [
    "AttachOnlyVendorBackend",
    "BackendAdapter",
    "BackendConnection",
    "BackendFeature",
    "GenericRemoteBackend",
    "OpenOCDBackend",
    "QemuBackend",
    "create_backend",
    "jlink_backend",
    "pyocd_backend",
]

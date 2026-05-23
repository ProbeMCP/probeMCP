"""Debugger backend adapters."""

from probemcp.backends.base import BackendAdapter, BackendConnection, BackendFeature
from probemcp.backends.generic_remote import GenericRemoteBackend

__all__ = ["BackendAdapter", "BackendConnection", "BackendFeature", "GenericRemoteBackend"]

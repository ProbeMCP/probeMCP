"""Factories for configured MCP services."""

from __future__ import annotations

from pathlib import Path

from probemcp.audit.logger import JsonlAuditWriter
from probemcp.config import ProbeMCPConfig
from probemcp.debug.factory import create_gdb_debug_session
from probemcp.mcp_server.service import ToolService
from probemcp.safety.confirmation import ConfirmationTokenStore
from probemcp.safety.limits import ResourceLimits
from probemcp.safety.policy import PolicyEngine
from probemcp.sessions.manager import SessionManager


def create_tool_service_from_config(config: ProbeMCPConfig) -> ToolService:
    """Build a ToolService from local configuration."""

    audit_writer = (
        JsonlAuditWriter(Path(config.server.audit_log_path))
        if config.server.audit_log_path is not None
        else None
    )
    return ToolService(
        sessions=SessionManager(),
        policy=PolicyEngine(),
        audit_writer=audit_writer,
        session_factory=create_gdb_debug_session,
        permission_mode=config.server.permission_mode,
        target_class=config.server.target_class,
        memory_write_enabled=config.server.memory_write_enabled,
        hardware_operation_allowlist=frozenset(config.server.hardware_operation_allowlist),
        confirmation_store=ConfirmationTokenStore(
            ttl_seconds=config.server.confirmation_ttl_seconds
        ),
        resource_limits=ResourceLimits(
            max_sessions=config.server.max_sessions,
            max_memory_read_bytes=config.server.max_memory_read_bytes,
            max_memory_write_bytes=config.server.max_memory_write_bytes,
            max_snapshot_stack_bytes=config.server.max_snapshot_stack_bytes,
            max_concurrent_tool_calls=config.server.max_concurrent_tool_calls,
            max_session_operations=config.server.max_session_operations,
            max_mi_command_queue=config.server.max_mi_command_queue,
        ),
    )

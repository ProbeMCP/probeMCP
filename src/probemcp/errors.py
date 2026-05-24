"""Public error-code registry."""

from __future__ import annotations

from enum import StrEnum

from probemcp.mcp_server.schemas import DebugError, ErrorCategory, JsonValue, PermissionLevel


class ErrorCode(StrEnum):
    """Stable ProbeMCP error codes for tool clients."""

    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
    INVALID_CONFIRMATION_TOKEN = "INVALID_CONFIRMATION_TOKEN"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    SESSION_FACTORY_UNAVAILABLE = "SESSION_FACTORY_UNAVAILABLE"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SNAPSHOT_NOT_FOUND = "SNAPSHOT_NOT_FOUND"
    SNAPSHOT_REQUIRED = "SNAPSHOT_REQUIRED"
    TOOL_EXECUTION_FAILED = "TOOL_EXECUTION_FAILED"
    UNSUPPORTED_BACKEND = "UNSUPPORTED_BACKEND"
    VALIDATION_FAILED = "VALIDATION_FAILED"


def make_error(
    code: ErrorCode,
    message: str,
    category: ErrorCategory,
    *,
    retryable: bool = False,
    required_permission: PermissionLevel | None = None,
    details: dict[str, JsonValue] | None = None,
    confirmation_token: str | None = None,
) -> DebugError:
    """Build a public tool error."""

    return DebugError(
        code=code.value,
        message=message,
        category=category,
        retryable=retryable,
        required_permission=required_permission,
        details=details or {},
        confirmation_token=confirmation_token,
    )

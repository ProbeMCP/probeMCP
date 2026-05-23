from probemcp.mcp_server.schemas import ErrorCategory, PermissionLevel
from probemcp.safety.policy import (
    DebugOperation,
    PolicyDecisionKind,
    PolicyEngine,
    PolicyRequest,
    TargetClass,
)


def test_readonly_operation_is_allowed_in_readonly_mode() -> None:
    decision = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.READONLY,
            operation=DebugOperation.READ_REGISTERS,
        )
    )

    assert decision.kind == PolicyDecisionKind.ALLOW
    assert decision.allowed
    assert decision.to_error() is None


def test_target_changing_operation_requires_confirmation_without_full_control() -> None:
    decision = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.READONLY,
            operation=DebugOperation.HALT,
        )
    )

    assert decision.kind == PolicyDecisionKind.REQUIRE_CONFIRMATION
    assert decision.confirmation_required

    error = decision.to_error()
    assert error is not None
    assert error.code == "CONFIRMATION_REQUIRED"
    assert error.category == ErrorCategory.PERMISSION
    assert error.required_permission == PermissionLevel.CONFIRM_REQUIRED


def test_full_control_allows_development_hardware_target_changing_operation() -> None:
    decision = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.FULL_CONTROL,
            operation=DebugOperation.STEP_INSTRUCTION,
            target_class=TargetClass.DEVELOPMENT_HARDWARE,
        )
    )

    assert decision.kind == PolicyDecisionKind.ALLOW


def test_memory_write_is_denied_by_default() -> None:
    decision = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.FULL_CONTROL,
            operation=DebugOperation.WRITE_MEMORY,
        )
    )

    assert decision.kind == PolicyDecisionKind.DENY
    assert decision.to_error() is not None
    assert decision.to_error().required_permission == PermissionLevel.FULL_CONTROL


def test_production_reset_is_denied_even_with_full_control() -> None:
    decision = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.FULL_CONTROL,
            operation=DebugOperation.RESET_TARGET,
            target_class=TargetClass.PRODUCTION_HARDWARE,
        )
    )

    assert decision.kind == PolicyDecisionKind.DENY
    assert "Production reset" in decision.reason

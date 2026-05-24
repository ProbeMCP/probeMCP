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

def test_memory_write_requires_full_control_enablement_and_confirmation() -> None:
    needs_confirmation = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.FULL_CONTROL,
            operation=DebugOperation.WRITE_MEMORY,
            memory_write_enabled=True,
        )
    )
    allowed = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.FULL_CONTROL,
            operation=DebugOperation.WRITE_MEMORY,
            memory_write_enabled=True,
            confirmation_token="confirmed",
        )
    )

    assert needs_confirmation.kind == PolicyDecisionKind.REQUIRE_CONFIRMATION
    assert allowed.kind == PolicyDecisionKind.ALLOW


def test_production_reset_is_blocked_without_local_hardware_interlock() -> None:
    decision = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.FULL_CONTROL,
            operation=DebugOperation.RESET_TARGET,
            target_class=TargetClass.PRODUCTION_HARDWARE,
        )
    )

    assert decision.kind == PolicyDecisionKind.DENY
    assert "hardware_operation_allowlist" in decision.reason

def test_production_reset_requires_confirmation_even_after_interlock_opt_in() -> None:
    needs_confirmation = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.FULL_CONTROL,
            operation=DebugOperation.RESET_TARGET,
            target_class=TargetClass.PRODUCTION_HARDWARE,
            hardware_operation_allowlist=frozenset({DebugOperation.RESET_TARGET}),
        )
    )
    allowed = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.FULL_CONTROL,
            operation=DebugOperation.RESET_TARGET,
            target_class=TargetClass.PRODUCTION_HARDWARE,
            confirmation_token="confirmed",
            hardware_operation_allowlist=frozenset({DebugOperation.RESET_TARGET}),
        )
    )

    assert needs_confirmation.kind == PolicyDecisionKind.REQUIRE_CONFIRMATION
    assert allowed.kind == PolicyDecisionKind.ALLOW
    assert allowed.warnings

def test_lab_hardware_interlock_blocks_emulator_convenience() -> None:
    lab = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.FULL_CONTROL,
            operation=DebugOperation.RESUME,
            target_class=TargetClass.LAB_HARDWARE,
        )
    )
    emulator = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.FULL_CONTROL,
            operation=DebugOperation.RESUME,
            target_class=TargetClass.EMULATOR,
        )
    )

    assert lab.kind == PolicyDecisionKind.DENY
    assert emulator.kind == PolicyDecisionKind.ALLOW

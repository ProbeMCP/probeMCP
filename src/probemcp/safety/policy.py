"""Permission policy model for target-safe debugging operations."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from probemcp.mcp_server.schemas import (
    DebugError,
    ErrorCategory,
    PermissionLevel,
    SchemaModel,
)


class DebugOperation(StrEnum):
    """Structured operation names used by the safety engine."""

    CONNECT_TARGET = "connect_target"
    DISCONNECT_TARGET = "disconnect_target"
    HALT = "halt"
    RESUME = "resume"
    STEP_INSTRUCTION = "step_instruction"
    RESET_TARGET = "reset_target"
    READ_REGISTERS = "read_registers"
    READ_MEMORY = "read_memory"
    WRITE_MEMORY = "write_memory"
    SET_BREAKPOINT = "set_breakpoint"
    CLEAR_BREAKPOINT = "clear_breakpoint"
    DEBUG_SNAPSHOT = "debug_snapshot"
    ANALYZE_FAULT = "analyze_fault"
    COMPARE_SNAPSHOTS = "compare_snapshots"
    EXPLAIN_CURRENT_STATE = "explain_current_state"
    INSPECT_PERIPHERAL = "inspect_peripheral"
    SUGGEST_NEXT_DEBUG_STEPS = "suggest_next_debug_steps"


class OperationRisk(StrEnum):
    """Coarse target risk level for a requested operation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TargetClass(StrEnum):
    """Target safety class."""

    EMULATOR = "emulator"
    DEVELOPMENT_HARDWARE = "development-hardware"
    LAB_HARDWARE = "lab-hardware"
    PRODUCTION_HARDWARE = "production-hardware"
    UNKNOWN = "unknown"


class PolicyDecisionKind(StrEnum):
    """Policy evaluation outcome."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require-confirmation"


READ_ONLY_OPERATIONS = frozenset(
    {
        DebugOperation.READ_REGISTERS,
        DebugOperation.READ_MEMORY,
        DebugOperation.ANALYZE_FAULT,
        DebugOperation.COMPARE_SNAPSHOTS,
        DebugOperation.DEBUG_SNAPSHOT,
        DebugOperation.EXPLAIN_CURRENT_STATE,
        DebugOperation.INSPECT_PERIPHERAL,
        DebugOperation.SUGGEST_NEXT_DEBUG_STEPS,
    }
)

TARGET_CHANGING_OPERATIONS = frozenset(
    {
        DebugOperation.CONNECT_TARGET,
        DebugOperation.DISCONNECT_TARGET,
        DebugOperation.HALT,
        DebugOperation.RESUME,
        DebugOperation.STEP_INSTRUCTION,
        DebugOperation.RESET_TARGET,
        DebugOperation.SET_BREAKPOINT,
        DebugOperation.CLEAR_BREAKPOINT,
    }
)

HARDWARE_INTERLOCK_CLASSES = frozenset(
    {
        TargetClass.LAB_HARDWARE,
        TargetClass.PRODUCTION_HARDWARE,
    }
)

PRODUCTION_CONFIRMATION_OPERATIONS = frozenset(
    {
        DebugOperation.DISCONNECT_TARGET,
        DebugOperation.HALT,
        DebugOperation.RESUME,
        DebugOperation.STEP_INSTRUCTION,
        DebugOperation.RESET_TARGET,
        DebugOperation.WRITE_MEMORY,
    }
)


class PolicyRequest(SchemaModel):
    """Input to the safety policy engine."""

    permission_mode: PermissionLevel
    operation: DebugOperation
    risk: OperationRisk = OperationRisk.LOW
    target_class: TargetClass = TargetClass.UNKNOWN
    production_target: bool = False
    memory_write_enabled: bool = False
    confirmation_token: str | None = None
    hardware_operation_allowlist: frozenset[DebugOperation] = Field(default_factory=frozenset)


class PolicyDecision(SchemaModel):
    """Serializable policy decision."""

    kind: PolicyDecisionKind
    operation: DebugOperation
    required_permission: PermissionLevel
    reason: str
    confirmation_required: bool = False
    warnings: list[str] = Field(default_factory=list)

    @property
    def allowed(self) -> bool:
        """Return true when the operation can execute immediately."""

        return self.kind == PolicyDecisionKind.ALLOW

    def to_error(self) -> DebugError | None:
        """Convert deny/confirmation decisions into a tool error."""

        if self.kind == PolicyDecisionKind.ALLOW:
            return None

        category = ErrorCategory.PERMISSION
        code = "CONFIRMATION_REQUIRED" if self.confirmation_required else "PERMISSION_DENIED"
        return DebugError(
            code=code,
            message=self.reason,
            category=category,
            retryable=self.confirmation_required,
            details={
                "operation": self.operation.value,
                "decision": self.kind.value,
            },
            required_permission=self.required_permission,
        )


class PolicyEngine:
    """Evaluate safety policy for structured debugging operations."""

    def evaluate(self, request: PolicyRequest) -> PolicyDecision:
        """Return a deterministic decision for a requested operation."""

        if request.operation == DebugOperation.WRITE_MEMORY:
            return self._evaluate_memory_write(request)

        if request.operation in READ_ONLY_OPERATIONS:
            return PolicyDecision(
                kind=PolicyDecisionKind.ALLOW,
                operation=request.operation,
                required_permission=PermissionLevel.READONLY,
                reason="Read-only operation is allowed.",
            )

        if request.operation in TARGET_CHANGING_OPERATIONS:
            return self._evaluate_target_changing_operation(request)

        return PolicyDecision(
            kind=PolicyDecisionKind.DENY,
            operation=request.operation,
            required_permission=PermissionLevel.FULL_CONTROL,
            reason=f"Unsupported operation: {request.operation.value}.",
        )

    def _evaluate_target_changing_operation(self, request: PolicyRequest) -> PolicyDecision:
        interlock = self._evaluate_hardware_interlock(request)
        if interlock is not None:
            return interlock

        if request.production_target or request.target_class == TargetClass.PRODUCTION_HARDWARE:
            if request.permission_mode != PermissionLevel.FULL_CONTROL:
                return PolicyDecision(
                    kind=PolicyDecisionKind.REQUIRE_CONFIRMATION,
                    operation=request.operation,
                    required_permission=PermissionLevel.FULL_CONTROL,
                    reason="Production target operation requires full-control permission.",
                    confirmation_required=True,
                    warnings=["Production hardware guardrail is active."],
                )

            if (
                request.operation in PRODUCTION_CONFIRMATION_OPERATIONS
                and not request.confirmation_token
            ):
                return PolicyDecision(
                    kind=PolicyDecisionKind.REQUIRE_CONFIRMATION,
                    operation=request.operation,
                    required_permission=PermissionLevel.FULL_CONTROL,
                    reason="Production hardware operation requires an explicit confirmation token.",
                    confirmation_required=True,
                    warnings=["Production hardware guardrail is active."],
                )

        if request.permission_mode == PermissionLevel.READONLY:
            return PolicyDecision(
                kind=PolicyDecisionKind.REQUIRE_CONFIRMATION,
                operation=request.operation,
                required_permission=PermissionLevel.CONFIRM_REQUIRED,
                reason="Target-changing operation requires confirmation.",
                confirmation_required=True,
            )

        if request.permission_mode == PermissionLevel.CONFIRM_REQUIRED:
            if request.confirmation_token:
                return PolicyDecision(
                    kind=PolicyDecisionKind.ALLOW,
                    operation=request.operation,
                    required_permission=PermissionLevel.CONFIRM_REQUIRED,
                    reason="Confirmation token accepted for target-changing operation.",
                )

            return PolicyDecision(
                kind=PolicyDecisionKind.REQUIRE_CONFIRMATION,
                operation=request.operation,
                required_permission=PermissionLevel.CONFIRM_REQUIRED,
                reason="Target-changing operation requires an explicit confirmation token.",
                confirmation_required=True,
            )

        return PolicyDecision(
            kind=PolicyDecisionKind.ALLOW,
            operation=request.operation,
            required_permission=PermissionLevel.FULL_CONTROL,
            reason="Full-control mode allows this target-changing operation.",
            warnings=self._hardware_warnings(request),
        )

    def _evaluate_memory_write(self, request: PolicyRequest) -> PolicyDecision:
        interlock = self._evaluate_hardware_interlock(request)
        if interlock is not None:
            return interlock

        if not request.memory_write_enabled:
            return PolicyDecision(
                kind=PolicyDecisionKind.DENY,
                operation=request.operation,
                required_permission=PermissionLevel.FULL_CONTROL,
                reason="Memory writes are disabled by default.",
            )

        if request.permission_mode != PermissionLevel.FULL_CONTROL:
            return PolicyDecision(
                kind=PolicyDecisionKind.REQUIRE_CONFIRMATION,
                operation=request.operation,
                required_permission=PermissionLevel.FULL_CONTROL,
                reason="Memory writes require full-control permission.",
                confirmation_required=True,
            )

        if request.target_class == TargetClass.PRODUCTION_HARDWARE:
            return PolicyDecision(
                kind=PolicyDecisionKind.DENY,
                operation=request.operation,
                required_permission=PermissionLevel.FULL_CONTROL,
                reason="Production memory writes are denied by default.",
            )

        if not request.confirmation_token:
            return PolicyDecision(
                kind=PolicyDecisionKind.REQUIRE_CONFIRMATION,
                operation=request.operation,
                required_permission=PermissionLevel.FULL_CONTROL,
                reason="Memory writes require an explicit confirmation token.",
                confirmation_required=True,
            )

        return PolicyDecision(
            kind=PolicyDecisionKind.ALLOW,
            operation=request.operation,
            required_permission=PermissionLevel.FULL_CONTROL,
            reason="Memory write is enabled and full-control permission is active.",
            warnings=[
                *self._hardware_warnings(request),
                "Memory write policy must still validate address ranges before execution.",
            ],
        )

    def _evaluate_hardware_interlock(self, request: PolicyRequest) -> PolicyDecision | None:
        if request.target_class not in HARDWARE_INTERLOCK_CLASSES:
            return None
        if request.operation in request.hardware_operation_allowlist:
            return None
        return PolicyDecision(
            kind=PolicyDecisionKind.DENY,
            operation=request.operation,
            required_permission=PermissionLevel.FULL_CONTROL,
            reason=(
                f"{request.target_class.value} operation requires explicit local "
                "hardware_operation_allowlist opt-in."
            ),
            warnings=[f"{request.target_class.value} hardware interlock blocked the operation."],
        )

    @staticmethod
    def _hardware_warnings(request: PolicyRequest) -> list[str]:
        if request.target_class in HARDWARE_INTERLOCK_CLASSES:
            return [f"{request.target_class.value} hardware interlock allowed the operation."]
        return []

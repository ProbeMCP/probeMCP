"""Execution service for ProbeMCP tool requests."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import structlog
from pydantic import BaseModel

from probemcp.analyzers.cortexm import CortexMFaultAnalyzer
from probemcp.audit.logger import AuditEvent, AuditOutcome, JsonlAuditWriter
from probemcp.errors import ErrorCode, make_error
from probemcp.mcp_server.schemas import (
    AnalyzeFaultRequest,
    BreakpointData,
    ClearBreakpointData,
    ClearBreakpointRequest,
    CompareSnapshotsRequest,
    ConnectTargetData,
    ConnectTargetRequest,
    DebugError,
    DebugSnapshotData,
    DebugSnapshotRequest,
    DisconnectTargetRequest,
    ErrorCategory,
    ExplainCurrentStateData,
    ExplainCurrentStateRequest,
    HaltData,
    HaltRequest,
    InspectPeripheralData,
    InspectPeripheralRequest,
    PeripheralRegisterData,
    PermissionLevel,
    ReadMemoryData,
    ReadMemoryRequest,
    ReadRegistersData,
    ReadRegistersRequest,
    ResetTargetData,
    ResetTargetRequest,
    ResumeData,
    ResumeRequest,
    SetBreakpointRequest,
    SnapshotDiffData,
    StepInstructionData,
    StepInstructionRequest,
    SuggestedDebugAction,
    SuggestNextDebugStepsData,
    SuggestNextDebugStepsRequest,
    TargetState,
    ToolResult,
    WriteMemoryData,
    WriteMemoryRequest,
)
from probemcp.privacy import redact_mapping
from probemcp.safety.confirmation import ConfirmationError, ConfirmationTokenStore
from probemcp.safety.limits import ResourceLimits
from probemcp.safety.policy import (
    DebugOperation,
    PolicyDecision,
    PolicyDecisionKind,
    PolicyEngine,
    PolicyRequest,
    TargetClass,
)
from probemcp.sessions.manager import SessionManager, SessionNotFoundError
from probemcp.snapshots.models import DebugSnapshot
from probemcp.snapshots.service import SnapshotService
from probemcp.svd import load_svd

type SessionFactory = Callable[[ConnectTargetRequest], Awaitable[Any]]

LOGGER = structlog.get_logger("probemcp.tool")


@dataclass(slots=True)
class ToolService:
    """Policy-aware tool execution facade."""

    sessions: SessionManager
    policy: PolicyEngine
    audit_writer: JsonlAuditWriter | None = None
    snapshot_service: SnapshotService | None = None
    fault_analyzer: CortexMFaultAnalyzer | None = None
    session_factory: SessionFactory | None = None
    permission_mode: PermissionLevel = PermissionLevel.READONLY
    target_class: TargetClass = TargetClass.UNKNOWN
    memory_write_enabled: bool = False
    hardware_operation_allowlist: frozenset[DebugOperation] = frozenset()
    confirmation_store: ConfirmationTokenStore | None = None
    resource_limits: ResourceLimits = ResourceLimits()
    _snapshots: dict[str, DebugSnapshot] | None = None
    _limit_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _active_tool_calls: int = 0
    _active_session_operations: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.snapshot_service is None:
            self.snapshot_service = SnapshotService()
        if self.fault_analyzer is None:
            self.fault_analyzer = CortexMFaultAnalyzer()
        if self.confirmation_store is None:
            self.confirmation_store = ConfirmationTokenStore()
        if self._snapshots is None:
            self._snapshots = {}

    async def connect_target(
        self,
        request: ConnectTargetRequest,
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[ConnectTargetData]:
        """Create and connect a debug session."""

        limit_error = self.resource_limits.check_session_count(len(self.sessions.list_ids()))
        if limit_error is not None:
            return self._failure(
                operation=DebugOperation.CONNECT_TARGET,
                tool_name="connect_target",
                error=limit_error,
                request=request,
            )

        if self.session_factory is None:
            return self._failure(
                operation=DebugOperation.CONNECT_TARGET,
                tool_name="connect_target",
                error=DebugError(
                    code=ErrorCode.SESSION_FACTORY_UNAVAILABLE.value,
                    message="connect_target requires a configured session factory.",
                    category=ErrorCategory.INTERNAL,
                ),
                request=request,
            )

        decision = self._evaluate(DebugOperation.CONNECT_TARGET, request, confirmation_token)
        if not decision.allowed:
            return self._policy_failure(
                "connect_target",
                DebugOperation.CONNECT_TARGET,
                decision.to_error(),
                request,
                warnings=decision.warnings,
            )

        try:
            session = await self.session_factory(request)
            connection = await session.connect(request)
            self.sessions.add(session)
            data = ConnectTargetData(
                session_id=session.session_id,
                backend=connection.backend,
                architecture=connection.architecture,
                profile=connection.profile,
                state=session.state,
            )
            return self._success(
                "connect_target",
                DebugOperation.CONNECT_TARGET,
                request,
                data,
                session_id=session.session_id,
                target_state=session.state,
                warnings=decision.warnings,
            )
        except Exception as exc:  # pragma: no cover - defensive envelope conversion
            return self._exception_failure(
                "connect_target",
                DebugOperation.CONNECT_TARGET,
                request,
                exc,
            )

    async def disconnect_target(
        self,
        request: DisconnectTargetRequest,
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[None]:
        """Disconnect and remove a session."""

        return await self._with_session(
            "disconnect_target",
            DebugOperation.DISCONNECT_TARGET,
            request,
            lambda session: self._disconnect(session, request),
            confirmation_token=confirmation_token,
        )

    async def halt(
        self,
        request: HaltRequest,
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[HaltData]:
        """Interrupt target execution."""

        return await self._with_session(
            "halt",
            DebugOperation.HALT,
            request,
            lambda session: session.halt(timeout_ms=request.timeout_ms),
            confirmation_token=confirmation_token,
        )

    async def resume(
        self,
        request: ResumeRequest,
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[ResumeData]:
        """Resume target execution with a bounded timeout."""

        async def run(session: Any) -> ResumeData:
            state = await session.resume(
                max_run_ms=request.max_run_ms,
                auto_interrupt=request.auto_interrupt,
            )
            return ResumeData(interrupted=state == TargetState.HALTED)

        return await self._with_session(
            "resume",
            DebugOperation.RESUME,
            request,
            run,
            confirmation_token=confirmation_token,
        )

    async def step_instruction(
        self,
        request: StepInstructionRequest,
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[StepInstructionData]:
        """Step one or more instructions."""

        async def run(session: Any) -> StepInstructionData:
            result = StepInstructionData()
            for _ in range(request.count):
                result = await session.step_instruction(timeout_ms=request.timeout_ms)
            return result

        return await self._with_session(
            "step_instruction",
            DebugOperation.STEP_INSTRUCTION,
            request,
            run,
            confirmation_token=confirmation_token,
        )

    async def reset_target(
        self,
        request: ResetTargetRequest,
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[ResetTargetData]:
        """Reset target through session/backend policy."""

        async def run(session: Any) -> ResetTargetData:
            state = await session.reset_target(mode=request.mode, timeout_ms=request.timeout_ms)
            return ResetTargetData(mode=request.mode, state=state)

        return await self._with_session(
            "reset_target",
            DebugOperation.RESET_TARGET,
            request,
            run,
            confirmation_token=confirmation_token,
        )

    async def read_registers(
        self,
        request: ReadRegistersRequest,
    ) -> ToolResult[ReadRegistersData]:
        """Read registers."""

        async def run(session: Any) -> ReadRegistersData:
            return ReadRegistersData(registers=await session.read_registers(request.group))

        return await self._with_session(
            "read_registers",
            DebugOperation.READ_REGISTERS,
            request,
            run,
        )

    async def read_memory(
        self,
        request: ReadMemoryRequest,
    ) -> ToolResult[ReadMemoryData]:
        """Read memory."""

        limit_error = self.resource_limits.check_memory_read(request.length)
        if limit_error is not None:
            return self._failure(
                operation=DebugOperation.READ_MEMORY,
                tool_name="read_memory",
                error=limit_error,
                request=request,
                session_id=request.session_id,
            )

        async def run(session: Any) -> ReadMemoryData:
            return cast(
                ReadMemoryData,
                await session.read_memory(
                    address=request.address,
                    length=request.length,
                    width=request.width,
                    timeout_ms=request.timeout_ms,
                ),
            )

        return await self._with_session("read_memory", DebugOperation.READ_MEMORY, request, run)

    async def write_memory(
        self,
        request: WriteMemoryRequest,
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[WriteMemoryData]:
        """Write memory through a disabled-by-default full-control policy."""

        try:
            write_length = len(bytes.fromhex(request.data_hex))
        except ValueError as exc:
            return self._failure(
                operation=DebugOperation.WRITE_MEMORY,
                tool_name="write_memory",
                error=DebugError(
                    code=ErrorCode.VALIDATION_FAILED.value,
                    message=f"data_hex must be valid hexadecimal bytes: {exc}",
                    category=ErrorCategory.VALIDATION,
                ),
                request=request,
                session_id=request.session_id,
            )

        limit_error = self.resource_limits.check_memory_write(write_length)
        if limit_error is not None:
            return self._failure(
                operation=DebugOperation.WRITE_MEMORY,
                tool_name="write_memory",
                error=limit_error,
                request=request,
                session_id=request.session_id,
            )

        async def run(session: Any) -> WriteMemoryData:
            return cast(
                WriteMemoryData,
                await session.write_memory(
                    address=request.address,
                    data_hex=request.data_hex,
                    expected_old_hex=request.expected_old_hex,
                    timeout_ms=request.timeout_ms,
                ),
            )

        return await self._with_session(
            "write_memory",
            DebugOperation.WRITE_MEMORY,
            request,
            run,
            confirmation_token=confirmation_token,
        )

    async def set_breakpoint(
        self,
        request: SetBreakpointRequest,
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[BreakpointData]:
        """Set breakpoint."""

        async def run(session: Any) -> BreakpointData:
            return cast(
                BreakpointData,
                await session.set_breakpoint(
                    location=request.location,
                    breakpoint_type=request.type,
                    temporary=request.temporary,
                    timeout_ms=request.timeout_ms,
                ),
            )

        return await self._with_session(
            "set_breakpoint",
            DebugOperation.SET_BREAKPOINT,
            request,
            run,
            confirmation_token=confirmation_token,
        )

    async def clear_breakpoint(
        self,
        request: ClearBreakpointRequest,
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[ClearBreakpointData]:
        """Clear breakpoint."""

        async def run(session: Any) -> ClearBreakpointData:
            return cast(
                ClearBreakpointData,
                await session.clear_breakpoint(
                    breakpoint_id=request.breakpoint_id,
                    timeout_ms=request.timeout_ms,
                ),
            )

        return await self._with_session(
            "clear_breakpoint",
            DebugOperation.CLEAR_BREAKPOINT,
            request,
            run,
            confirmation_token=confirmation_token,
        )

    async def debug_snapshot(self, request: DebugSnapshotRequest) -> ToolResult[DebugSnapshotData]:
        """Capture a debug snapshot."""

        if request.include_stack:
            limit_error = self.resource_limits.check_snapshot_stack(request.stack_bytes)
            if limit_error is not None:
                return self._failure(
                    operation=DebugOperation.DEBUG_SNAPSHOT,
                    tool_name="debug_snapshot",
                    error=limit_error,
                    request=request,
                    session_id=request.session_id,
                )

        async def run(session: Any) -> DebugSnapshotData:
            assert self.snapshot_service is not None
            assert self._snapshots is not None
            snapshot = await self.snapshot_service.capture(
                session_id=request.session_id,
                target=session,
                request=request,
            )
            self._snapshots[snapshot.snapshot_id] = snapshot
            return DebugSnapshotData(
                snapshot_id=snapshot.snapshot_id,
                state=snapshot.state,
                summary=snapshot.summary,
            )

        return await self._with_session(
            "debug_snapshot",
            DebugOperation.DEBUG_SNAPSHOT,
            request,
            run,
        )

    async def analyze_fault(self, request: AnalyzeFaultRequest) -> ToolResult[Any]:
        """Analyze a captured Cortex-M fault snapshot."""

        assert self._snapshots is not None
        assert self.fault_analyzer is not None

        if request.snapshot_id is None:
            return self._failure(
                operation=DebugOperation.ANALYZE_FAULT,
                tool_name="analyze_fault",
                error=DebugError(
                    code=ErrorCode.SNAPSHOT_REQUIRED.value,
                    message="analyze_fault currently requires snapshot_id.",
                    category=ErrorCategory.VALIDATION,
                ),
                request=request,
            )

        snapshot = self._snapshots.get(request.snapshot_id)
        if snapshot is None:
            return self._failure(
                operation=DebugOperation.ANALYZE_FAULT,
                tool_name="analyze_fault",
                error=DebugError(
                    code=ErrorCode.SNAPSHOT_NOT_FOUND.value,
                    message=f"Snapshot not found: {request.snapshot_id}",
                    category=ErrorCategory.VALIDATION,
                ),
                request=request,
            )

        data = self.fault_analyzer.analyze(snapshot)
        return self._success(
            "analyze_fault",
            DebugOperation.ANALYZE_FAULT,
            request,
            data,
            session_id=snapshot.session_id,
            target_state=snapshot.state,
        )

    async def inspect_peripheral(
        self,
        request: InspectPeripheralRequest,
    ) -> ToolResult[InspectPeripheralData]:
        """Decode peripheral registers from a local SVD file and target memory."""

        device = load_svd(Path(request.svd_path))
        peripheral = device.peripheral(request.peripheral)
        register_names = request.registers or sorted(peripheral.registers)

        async def run(session: Any) -> InspectPeripheralData:
            decoded_registers: list[PeripheralRegisterData] = []
            for register_name in register_names:
                register = peripheral.registers[register_name]
                address = peripheral.register_address(register_name)
                memory = await session.read_memory(
                    address=f"0x{address:08x}",
                    length=4,
                    width=4,
                    timeout_ms=request.timeout_ms,
                )
                value = int.from_bytes(bytes.fromhex(memory.data_hex), byteorder="little")
                decoded_registers.append(
                    PeripheralRegisterData(
                        name=register.name,
                        address=f"0x{address:08x}",
                        value=f"0x{value:08x}",
                        fields=register.decode(value),
                    )
                )
            return InspectPeripheralData(
                device=device.name,
                peripheral=peripheral.name,
                registers=decoded_registers,
            )

        return await self._with_session(
            "inspect_peripheral",
            DebugOperation.INSPECT_PERIPHERAL,
            request,
            run,
        )

    async def compare_snapshots(
        self, request: CompareSnapshotsRequest
    ) -> ToolResult[SnapshotDiffData]:
        """Compare two captured debug snapshots."""

        before = self.get_snapshot(request.before_snapshot_id)
        after = self.get_snapshot(request.after_snapshot_id)
        if before is None or after is None:
            return self._failure(
                operation=DebugOperation.COMPARE_SNAPSHOTS,
                tool_name="compare_snapshots",
                error=make_error(
                    ErrorCode.SNAPSHOT_NOT_FOUND,
                    "one or both snapshots were not found",
                    ErrorCategory.VALIDATION,
                    details={
                        "before_snapshot_id": request.before_snapshot_id,
                        "after_snapshot_id": request.after_snapshot_id,
                    },
                ),
                request=request,
            )

        register_diffs = _diff_dicts(
            {**before.core_registers, **before.fault_registers},
            {**after.core_registers, **after.fault_registers},
        )
        summary = (
            "No register or fault-register differences detected."
            if not register_diffs
            else f"{len(register_diffs)} register or fault-register differences detected."
        )
        return self._success(
            "compare_snapshots",
            DebugOperation.COMPARE_SNAPSHOTS,
            request,
            SnapshotDiffData(register_diffs=register_diffs, summary=summary),
            session_id=after.session_id,
            target_state=after.state,
        )

    async def explain_current_state(
        self,
        request: ExplainCurrentStateRequest,
    ) -> ToolResult[ExplainCurrentStateData]:
        """Explain a captured snapshot in structured terms."""

        snapshot = self._snapshot_from_request(request.snapshot_id, request.session_id)
        if snapshot is None:
            return self._failure(
                operation=DebugOperation.EXPLAIN_CURRENT_STATE,
                tool_name="explain_current_state",
                error=make_error(
                    ErrorCode.SNAPSHOT_NOT_FOUND,
                    "explain_current_state currently requires an existing snapshot_id",
                    ErrorCategory.VALIDATION,
                ),
                request=request,
            )

        evidence = [snapshot.summary]
        pc = snapshot.core_registers.get("pc") or snapshot.core_registers.get("15")
        cfsr = snapshot.fault_registers.get("cfsr")
        if pc is not None:
            evidence.append(f"PC={pc}")
        if cfsr is not None:
            evidence.append(f"CFSR={cfsr}")
        data = ExplainCurrentStateData(
            summary=f"Target state is {snapshot.state.value}.",
            evidence=evidence,
        )
        return self._success(
            "explain_current_state",
            DebugOperation.EXPLAIN_CURRENT_STATE,
            request,
            data,
            session_id=snapshot.session_id,
            target_state=snapshot.state,
        )

    async def suggest_next_debug_steps(
        self,
        request: SuggestNextDebugStepsRequest,
    ) -> ToolResult[SuggestNextDebugStepsData]:
        """Suggest conservative next debugging steps."""

        snapshot = self._snapshot_from_request(request.snapshot_id, request.session_id)
        if snapshot is None:
            return self._failure(
                operation=DebugOperation.SUGGEST_NEXT_DEBUG_STEPS,
                tool_name="suggest_next_debug_steps",
                error=make_error(
                    ErrorCode.SNAPSHOT_NOT_FOUND,
                    "suggest_next_debug_steps currently requires an existing snapshot_id",
                    ErrorCategory.VALIDATION,
                ),
                request=request,
            )

        actions = [
            SuggestedDebugAction(
                title="Analyze the current fault registers",
                rationale="The action is read-only and links next steps to captured evidence.",
                tool_name="analyze_fault",
                risk="low",
                required_permission=PermissionLevel.READONLY,
            ),
            SuggestedDebugAction(
                title="Capture a second snapshot after one instruction step",
                rationale=(
                    "A bounded step plus snapshot can reveal whether state changes are stable."
                ),
                tool_name="step_instruction",
                risk="medium",
                required_permission=PermissionLevel.CONFIRM_REQUIRED,
            ),
        ]
        return self._success(
            "suggest_next_debug_steps",
            DebugOperation.SUGGEST_NEXT_DEBUG_STEPS,
            request,
            SuggestNextDebugStepsData(actions=actions),
            session_id=snapshot.session_id,
            target_state=snapshot.state,
        )

    def list_session_summaries(self) -> list[dict[str, str]]:
        """Return read-only summaries for active sessions."""

        summaries: list[dict[str, str]] = []
        for session_id in self.sessions.list_ids():
            try:
                session = self.sessions.get(session_id)
            except SessionNotFoundError:  # pragma: no cover - defensive race guard
                continue
            summaries.append({"session_id": session_id, "state": session.state.value})
        return summaries

    def get_snapshot(self, snapshot_id: str) -> DebugSnapshot | None:
        """Return a captured snapshot by ID."""

        assert self._snapshots is not None
        return self._snapshots.get(snapshot_id)

    def list_audit_events(self) -> list[dict[str, Any]]:
        """Return local audit events if an audit writer is configured."""

        if self.audit_writer is None:
            return []
        return [
            event.model_dump(mode="json", exclude_none=True)
            for event in self.audit_writer.read_events()
        ]

    def _snapshot_from_request(
        self,
        snapshot_id: str | None,
        _session_id: str | None,
    ) -> DebugSnapshot | None:
        if snapshot_id is None:
            return None
        return self.get_snapshot(snapshot_id)

    async def _disconnect(self, session: Any, request: DisconnectTargetRequest) -> None:
        await session.disconnect(timeout_ms=request.timeout_ms)
        self.sessions.remove(request.session_id)

    async def _with_session(
        self,
        tool_name: str,
        operation: DebugOperation,
        request: BaseModel,
        call: Callable[[Any], Awaitable[Any]],
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[Any]:
        decision = self._evaluate(operation, request, confirmation_token)
        if not decision.allowed:
            return self._policy_failure(
                tool_name,
                operation,
                decision.to_error(),
                request,
                warnings=decision.warnings,
            )

        try:
            session_id = cast(Any, request).session_id
            session = self.sessions.get(session_id)
        except SessionNotFoundError:
            return self._failure(
                operation=operation,
                tool_name=tool_name,
                error=DebugError(
                    code=ErrorCode.SESSION_NOT_FOUND.value,
                    message=f"Session not found: {getattr(request, 'session_id', None)}",
                    category=ErrorCategory.VALIDATION,
                ),
                request=request,
            )

        before_state = session.state
        limit_error = await self._try_reserve_operation(session_id)
        if limit_error is not None:
            return self._failure(
                operation=operation,
                tool_name=tool_name,
                error=limit_error,
                request=request,
                session_id=session_id,
            )

        try:
            data = await call(session)
        except Exception as exc:  # pragma: no cover - defensive envelope conversion
            return self._exception_failure(
                tool_name,
                operation,
                request,
                exc,
                session_id=session_id,
            )
        finally:
            await self._release_operation(session_id)

        return self._success(
            tool_name,
            operation,
            request,
            data,
            session_id=session_id,
            target_state=session.state,
            before_state=before_state,
            warnings=decision.warnings,
        )

    async def _try_reserve_operation(self, session_id: str | None) -> DebugError | None:
        async with self._limit_lock:
            tool_error = self.resource_limits.check_tool_concurrency(self._active_tool_calls)
            if tool_error is not None:
                return tool_error

            if session_id is not None:
                session_active = self._active_session_operations.get(session_id, 0)
                session_error = self.resource_limits.check_session_operations(session_active)
                if session_error is not None:
                    return session_error
                self._active_session_operations[session_id] = session_active + 1

            self._active_tool_calls += 1
            return None

    async def _release_operation(self, session_id: str | None) -> None:
        async with self._limit_lock:
            self._active_tool_calls = max(0, self._active_tool_calls - 1)
            if session_id is None:
                return
            session_active = self._active_session_operations.get(session_id, 0)
            if session_active <= 1:
                self._active_session_operations.pop(session_id, None)
            else:
                self._active_session_operations[session_id] = session_active - 1

    def _evaluate(
        self,
        operation: DebugOperation,
        request: BaseModel,
        confirmation_token: str | None,
    ) -> PolicyDecision:
        validated_token: str | None = None
        if confirmation_token is not None:
            assert self.confirmation_store is not None
            try:
                self.confirmation_store.verify(confirmation_token, operation, request)
            except ConfirmationError as exc:
                return PolicyDecision(
                    kind=PolicyDecisionKind.DENY,
                    operation=operation,
                    required_permission=PermissionLevel.CONFIRM_REQUIRED,
                    reason=str(exc),
                )
            validated_token = confirmation_token

        return self.policy.evaluate(
            PolicyRequest(
                permission_mode=self.permission_mode,
                operation=operation,
                target_class=self.target_class,
                memory_write_enabled=self.memory_write_enabled,
                confirmation_token=validated_token,
                hardware_operation_allowlist=self.hardware_operation_allowlist,
            )
        )

    def _policy_failure(
        self,
        tool_name: str,
        operation: DebugOperation,
        error: DebugError | None,
        request: BaseModel,
        *,
        warnings: list[str] | None = None,
    ) -> ToolResult[Any]:
        assert error is not None
        if error.code == ErrorCode.CONFIRMATION_REQUIRED.value:
            assert self.confirmation_store is not None
            error = error.model_copy(
                update={
                    "confirmation_token": self.confirmation_store.issue(operation, request),
                }
            )
        elif error.code == ErrorCode.PERMISSION_DENIED.value and error.message.startswith(
            "confirmation token"
        ):
            error = make_error(
                ErrorCode.INVALID_CONFIRMATION_TOKEN,
                error.message,
                ErrorCategory.PERMISSION,
                retryable=False,
                required_permission=PermissionLevel.CONFIRM_REQUIRED,
            )
        return self._failure(
            operation=operation,
            tool_name=tool_name,
            error=error,
            request=request,
            warnings=warnings,
        )

    def _success(
        self,
        tool_name: str,
        operation: DebugOperation,
        request: BaseModel,
        data: Any,
        *,
        session_id: str | None = None,
        target_state: TargetState = TargetState.UNKNOWN,
        before_state: TargetState = TargetState.UNKNOWN,
        warnings: list[str] | None = None,
    ) -> ToolResult[Any]:
        audit_id = self._audit(
            tool_name=tool_name,
            request=request,
            operation=operation,
            outcome=AuditOutcome.SUCCESS,
            session_id=session_id,
            before_state=before_state,
            after_state=target_state,
            result_summary=_summary(data),
            warnings=warnings or [],
        )
        return ToolResult(
            ok=True,
            session_id=session_id,
            target_state=target_state,
            data=data,
            warnings=warnings or [],
            audit_id=audit_id,
        )

    def _failure(
        self,
        *,
        operation: DebugOperation,
        tool_name: str,
        error: DebugError,
        request: BaseModel,
        session_id: str | None = None,
        warnings: list[str] | None = None,
    ) -> ToolResult[Any]:
        audit_id = self._audit(
            tool_name=tool_name,
            request=request,
            operation=operation,
            outcome=AuditOutcome.ERROR,
            session_id=session_id,
            error=error,
            warnings=warnings or [],
        )
        return ToolResult(
            ok=False,
            session_id=session_id,
            warnings=warnings or [],
            audit_id=audit_id,
            error=error,
        )

    def _exception_failure(
        self,
        tool_name: str,
        operation: DebugOperation,
        request: BaseModel,
        exc: Exception,
        *,
        session_id: str | None = None,
    ) -> ToolResult[Any]:
        return self._failure(
            operation=operation,
            tool_name=tool_name,
            error=DebugError(
                code=ErrorCode.TOOL_EXECUTION_FAILED.value,
                message=str(exc),
                category=ErrorCategory.INTERNAL,
            ),
            request=request,
            session_id=session_id,
        )

    def _audit(
        self,
        *,
        tool_name: str,
        request: BaseModel,
        operation: DebugOperation,
        outcome: AuditOutcome,
        session_id: str | None = None,
        before_state: TargetState = TargetState.UNKNOWN,
        after_state: TargetState = TargetState.UNKNOWN,
        result_summary: dict[str, Any] | None = None,
        error: DebugError | None = None,
        warnings: list[str] | None = None,
    ) -> str | None:
        if self.audit_writer is None:
            return None

        event = AuditEvent(
            session_id=session_id,
            tool_name=tool_name,
            permission_mode=self.permission_mode,
            target_state_before=before_state,
            target_state_after=after_state,
            outcome=outcome,
            request_summary=_summary(request),
            result_summary=result_summary or {},
            warnings=warnings or [],
            error=error,
        )
        self.audit_writer.append(event)
        LOGGER.info(
            "tool_call_audited",
            audit_id=event.audit_id,
            correlation_id=event.correlation_id,
            tool_name=tool_name,
            operation=operation.value,
            outcome=outcome.value,
            session_id=session_id,
        )
        return event.audit_id


def _summary(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return redact_mapping(value.model_dump(mode="json", exclude_none=True))
    if isinstance(value, dict):
        return redact_mapping(value)
    if value is None:
        return {}
    return {"value": str(value)}


def _diff_dicts(
    before: dict[str, str],
    after: dict[str, str],
) -> dict[str, tuple[str | None, str | None]]:
    keys = sorted(set(before) | set(after))
    return {
        key: (before.get(key), after.get(key))
        for key in keys
        if before.get(key) != after.get(key)
    }

"""Execution service for ProbeMCP tool requests."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

from pydantic import BaseModel

from probemcp.analyzers.cortexm import CortexMFaultAnalyzer
from probemcp.audit.logger import AuditEvent, AuditOutcome, JsonlAuditWriter
from probemcp.mcp_server.schemas import (
    AnalyzeFaultRequest,
    BreakpointData,
    ClearBreakpointData,
    ClearBreakpointRequest,
    ConnectTargetData,
    ConnectTargetRequest,
    DebugError,
    DebugSnapshotData,
    DebugSnapshotRequest,
    DisconnectTargetRequest,
    ErrorCategory,
    HaltData,
    HaltRequest,
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
    StepInstructionData,
    StepInstructionRequest,
    TargetState,
    ToolResult,
)
from probemcp.safety.policy import (
    DebugOperation,
    PolicyDecision,
    PolicyEngine,
    PolicyRequest,
    TargetClass,
)
from probemcp.sessions.manager import SessionManager, SessionNotFoundError
from probemcp.snapshots.models import DebugSnapshot
from probemcp.snapshots.service import SnapshotService

type SessionFactory = Callable[[ConnectTargetRequest], Awaitable[Any]]


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
    _snapshots: dict[str, DebugSnapshot] | None = None

    def __post_init__(self) -> None:
        if self.snapshot_service is None:
            self.snapshot_service = SnapshotService()
        if self.fault_analyzer is None:
            self.fault_analyzer = CortexMFaultAnalyzer()
        if self._snapshots is None:
            self._snapshots = {}

    async def connect_target(
        self,
        request: ConnectTargetRequest,
        *,
        confirmation_token: str | None = None,
    ) -> ToolResult[ConnectTargetData]:
        """Create and connect a debug session."""

        if self.session_factory is None:
            return self._failure(
                operation=DebugOperation.CONNECT_TARGET,
                tool_name="connect_target",
                error=DebugError(
                    code="SESSION_FACTORY_UNAVAILABLE",
                    message="connect_target requires a configured session factory.",
                    category=ErrorCategory.INTERNAL,
                ),
                request=request,
            )

        decision = self._evaluate(DebugOperation.CONNECT_TARGET, confirmation_token)
        if not decision.allowed:
            return self._policy_failure(
                "connect_target",
                DebugOperation.CONNECT_TARGET,
                decision.to_error(),
                request,
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
            state = await session.reset_target(mode=request.mode)
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
                    code="SNAPSHOT_REQUIRED",
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
                    code="SNAPSHOT_NOT_FOUND",
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
        decision = self._evaluate(operation, confirmation_token)
        if not decision.allowed:
            return self._policy_failure(tool_name, operation, decision.to_error(), request)

        try:
            session_id = cast(Any, request).session_id
            session = self.sessions.get(session_id)
        except SessionNotFoundError:
            return self._failure(
                operation=operation,
                tool_name=tool_name,
                error=DebugError(
                    code="SESSION_NOT_FOUND",
                    message=f"Session not found: {getattr(request, 'session_id', None)}",
                    category=ErrorCategory.VALIDATION,
                ),
                request=request,
            )

        before_state = session.state
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

        return self._success(
            tool_name,
            operation,
            request,
            data,
            session_id=session_id,
            target_state=session.state,
            before_state=before_state,
        )

    def _evaluate(
        self,
        operation: DebugOperation,
        confirmation_token: str | None,
    ) -> PolicyDecision:
        return self.policy.evaluate(
            PolicyRequest(
                permission_mode=self.permission_mode,
                operation=operation,
                target_class=self.target_class,
                confirmation_token=confirmation_token,
            )
        )

    def _policy_failure(
        self,
        tool_name: str,
        operation: DebugOperation,
        error: DebugError | None,
        request: BaseModel,
    ) -> ToolResult[Any]:
        assert error is not None
        return self._failure(
            operation=operation,
            tool_name=tool_name,
            error=error,
            request=request,
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
        )
        return ToolResult(
            ok=True,
            session_id=session_id,
            target_state=target_state,
            data=data,
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
    ) -> ToolResult[Any]:
        audit_id = self._audit(
            tool_name=tool_name,
            request=request,
            operation=operation,
            outcome=AuditOutcome.ERROR,
            session_id=session_id,
            error=error,
        )
        return ToolResult(ok=False, session_id=session_id, audit_id=audit_id, error=error)

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
                code="TOOL_EXECUTION_FAILED",
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
            error=error,
        )
        self.audit_writer.append(event)
        return event.audit_id


def _summary(value: Any) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    return {"value": str(value)}

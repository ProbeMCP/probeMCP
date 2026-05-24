import asyncio
from pathlib import Path
from typing import Any, cast

import pytest

from probemcp.audit.logger import JsonlAuditWriter
from probemcp.backends.base import BackendConnection
from probemcp.mcp_server.schemas import (
    AnalyzeFaultRequest,
    BackendKind,
    BreakpointData,
    BreakpointLocation,
    BreakpointType,
    ClearBreakpointData,
    ClearBreakpointRequest,
    CompareSnapshotsRequest,
    ConnectTargetRequest,
    DebugSnapshotRequest,
    DisconnectTargetRequest,
    ExplainCurrentStateRequest,
    HaltData,
    HaltRequest,
    InspectPeripheralRequest,
    PermissionLevel,
    ReadMemoryData,
    ReadMemoryRequest,
    ReadRegistersRequest,
    RegisterGroup,
    ResetMode,
    ResetTargetRequest,
    ResumeRequest,
    SetBreakpointRequest,
    StepInstructionData,
    StepInstructionRequest,
    SuggestNextDebugStepsRequest,
    TargetState,
    WriteMemoryData,
    WriteMemoryRequest,
)
from probemcp.mcp_server.service import ToolService
from probemcp.safety.limits import ResourceLimits
from probemcp.safety.policy import (
    DebugOperation,
    PolicyDecisionKind,
    PolicyEngine,
    PolicyRequest,
    TargetClass,
)
from probemcp.sessions.manager import SessionManager


class FakeToolSession:
    session_id = "session_01"

    def __init__(self) -> None:
        self.state = TargetState.HALTED
        self.calls: list[str] = []

    async def read_registers(self, group: RegisterGroup = RegisterGroup.CORE) -> dict[str, str]:
        self.calls.append(f"read_registers:{group.value}")
        return {
            "pc": "0x08001234",
            "lr": "0xfffffff9",
            "sp": "0x20001000",
            "xpsr": "0x00000003",
        }

    async def read_memory(
        self,
        *,
        address: str,
        length: int,
        width: int = 1,
        timeout_ms: int = 3000,
    ) -> ReadMemoryData:
        self.calls.append(f"read_memory:{address}:{length}:{width}:{timeout_ms}")
        if address == "0xE000ED28":
            return ReadMemoryData(address=address, length=length, width=width, data_hex="00000200")
        return ReadMemoryData(address=address, length=length, width=width, data_hex="01020304")

    async def halt(self, *, timeout_ms: int = 2000) -> HaltData:
        self.calls.append(f"halt:{timeout_ms}")
        self.state = TargetState.HALTED
        return HaltData(stop_reason="signal-received", pc="0x08001234")

    async def resume(self, *, max_run_ms: int, auto_interrupt: bool = True) -> TargetState:
        self.calls.append(f"resume:{max_run_ms}:{auto_interrupt}")
        self.state = TargetState.RUNNING
        return self.state

    async def step_instruction(self, *, timeout_ms: int = 5000):
        self.calls.append(f"step:{timeout_ms}")
        return StepInstructionData(pc="0x08001238")

    async def reset_target(self, *, mode: ResetMode, timeout_ms: int = 10_000) -> TargetState:
        self.calls.append(f"reset:{mode.value}:{timeout_ms}")
        self.state = TargetState.HALTED if mode == ResetMode.HALT else TargetState.RUNNING
        return self.state

    async def disconnect(self, *, timeout_ms: int = 5000) -> None:
        self.calls.append(f"disconnect:{timeout_ms}")
        self.state = TargetState.DISCONNECTED

    async def connect(self, request: ConnectTargetRequest) -> BackendConnection:
        self.calls.append(f"connect:{request.endpoint}")
        self.state = TargetState.HALTED
        return BackendConnection(
            backend=request.backend,
            endpoint=request.endpoint or "",
            profile=request.profile,
            state=self.state,
        )

    async def set_breakpoint(
        self,
        *,
        location: BreakpointLocation,
        breakpoint_type: BreakpointType,
        temporary: bool,
        timeout_ms: int = 3000,
    ) -> BreakpointData:
        self.calls.append(f"set_breakpoint:{location.value}:{breakpoint_type.value}:{temporary}")
        return BreakpointData(
            breakpoint_id="1",
            location=location,
            type=breakpoint_type,
            temporary=temporary,
        )

    async def clear_breakpoint(
        self,
        *,
        breakpoint_id: str,
        timeout_ms: int = 3000,
    ) -> ClearBreakpointData:
        self.calls.append(f"clear_breakpoint:{breakpoint_id}")
        return ClearBreakpointData(breakpoint_id=breakpoint_id, removed=True)

    async def write_memory(
        self,
        *,
        address: str,
        data_hex: str,
        expected_old_hex: str | None = None,
        timeout_ms: int = 3000,
    ) -> WriteMemoryData:
        self.calls.append(f"write_memory:{address}:{data_hex}:{expected_old_hex}:{timeout_ms}")
        return WriteMemoryData(
            address=address,
            bytes_written=len(bytes.fromhex(data_hex)),
            verified_old_value=expected_old_hex is not None,
        )


def make_service(tmp_path: Path, *, permission: PermissionLevel = PermissionLevel.READONLY):
    manager = SessionManager()
    session = FakeToolSession()
    manager.add(cast(Any, session))
    service = ToolService(
        sessions=manager,
        policy=PolicyEngine(),
        audit_writer=JsonlAuditWriter(tmp_path / "audit.jsonl"),
        permission_mode=permission,
    )
    return service, session


async def confirmed(
    service: ToolService,
    method_name: str,
    request: Any,
    session: FakeToolSession | None = None,
):
    method = getattr(service, method_name)
    denied = await method(request)
    assert not denied.ok
    assert denied.error is not None
    assert denied.error.confirmation_token is not None
    if session is not None:
        session.calls.clear()
    return await method(request, confirmation_token=denied.error.confirmation_token)


def test_policy_accepts_confirmation_token_for_confirm_required_mode() -> None:
    decision = PolicyEngine().evaluate(
        PolicyRequest(
            permission_mode=PermissionLevel.CONFIRM_REQUIRED,
            operation=DebugOperation.HALT,
            confirmation_token="confirmed",
        )
    )

    assert decision.kind == PolicyDecisionKind.ALLOW


@pytest.mark.asyncio
async def test_tool_service_read_registers_returns_tool_result_and_audit(tmp_path: Path) -> None:
    service, session = make_service(tmp_path)

    result = await service.read_registers(ReadRegistersRequest(session_id="session_01"))

    assert result.ok
    assert result.data is not None
    assert result.data.registers["pc"] == "0x08001234"
    assert session.calls == ["read_registers:core"]
    assert result.audit_id is not None


@pytest.mark.asyncio
async def test_tool_service_denies_target_changing_action_without_confirmation(
    tmp_path: Path,
) -> None:
    service, session = make_service(tmp_path, permission=PermissionLevel.CONFIRM_REQUIRED)

    result = await service.halt(HaltRequest(session_id="session_01"))

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "CONFIRMATION_REQUIRED"
    assert session.calls == []


@pytest.mark.asyncio
async def test_tool_service_allows_target_changing_action_with_confirmation(
    tmp_path: Path,
) -> None:
    service, session = make_service(tmp_path, permission=PermissionLevel.CONFIRM_REQUIRED)

    result = await confirmed(
        service,
        "halt",
        HaltRequest(session_id="session_01"),
        session,
    )

    assert result.ok
    assert result.data is not None
    assert result.data.pc == "0x08001234"
    assert session.calls == ["halt:2000"]


@pytest.mark.asyncio
async def test_tool_service_read_memory_and_breakpoints(tmp_path: Path) -> None:
    service, session = make_service(tmp_path, permission=PermissionLevel.CONFIRM_REQUIRED)

    memory = await service.read_memory(
        ReadMemoryRequest(session_id="session_01", address="0x20000000", length=4)
    )
    breakpoint = await confirmed(
        service,
        "set_breakpoint",
        SetBreakpointRequest(
            session_id="session_01",
            location=BreakpointLocation(kind="symbol", value="main"),
        ),
        session,
    )
    cleared = await confirmed(
        service,
        "clear_breakpoint",
        ClearBreakpointRequest(session_id="session_01", breakpoint_id="1"),
        session,
    )

    assert memory.ok
    assert memory.data is not None
    assert memory.data.data_hex == "01020304"
    assert breakpoint.ok
    assert breakpoint.data is not None
    assert breakpoint.data.breakpoint_id == "1"
    assert cleared.ok
    assert "clear_breakpoint:1" in session.calls


@pytest.mark.asyncio
async def test_tool_service_write_memory_requires_enablement_and_confirmation(
    tmp_path: Path,
) -> None:
    service, session = make_service(tmp_path, permission=PermissionLevel.FULL_CONTROL)
    request = WriteMemoryRequest(
        session_id="session_01",
        address="0x20000000",
        data_hex="0102",
        expected_old_hex="0000",
    )

    disabled = await service.write_memory(request)
    service.memory_write_enabled = True
    written = await confirmed(service, "write_memory", request, session)

    assert disabled.error is not None
    assert disabled.error.code == "PERMISSION_DENIED"
    assert written.ok
    assert written.data is not None
    assert written.data.bytes_written == 2
    assert session.calls == ["write_memory:0x20000000:0102:0000:3000"]


@pytest.mark.asyncio
async def test_tool_service_resume_uses_bounded_request(tmp_path: Path) -> None:
    service, session = make_service(tmp_path, permission=PermissionLevel.CONFIRM_REQUIRED)

    result = await confirmed(
        service,
        "resume",
        ResumeRequest(session_id="session_01", max_run_ms=50),
        session,
    )

    assert result.ok
    assert result.target_state == TargetState.RUNNING
    assert session.calls == ["resume:50:True"]


@pytest.mark.asyncio
async def test_tool_service_step_and_reset_use_confirmation(tmp_path: Path) -> None:
    service, session = make_service(tmp_path, permission=PermissionLevel.CONFIRM_REQUIRED)

    step = await confirmed(
        service,
        "step_instruction",
        StepInstructionRequest(session_id="session_01", count=2),
        session,
    )
    reset = await confirmed(
        service,
        "reset_target",
        ResetTargetRequest(session_id="session_01", mode=ResetMode.RUN),
        session,
    )

    assert step.ok
    assert step.data is not None
    assert step.data.pc == "0x08001238"
    assert reset.ok
    assert reset.target_state == TargetState.RUNNING
    assert session.calls == ["reset:run:10000"]


@pytest.mark.asyncio
async def test_tool_service_disconnect_removes_session(tmp_path: Path) -> None:
    service, session = make_service(tmp_path, permission=PermissionLevel.CONFIRM_REQUIRED)

    result = await confirmed(
        service,
        "disconnect_target",
        DisconnectTargetRequest(session_id="session_01"),
        session,
    )

    assert result.ok
    assert session.calls == ["disconnect:5000"]
    assert service.sessions.list_ids() == []


@pytest.mark.asyncio
async def test_tool_service_connect_requires_factory(tmp_path: Path) -> None:
    manager = SessionManager()
    service = ToolService(
        sessions=manager,
        policy=PolicyEngine(),
        audit_writer=JsonlAuditWriter(tmp_path / "audit.jsonl"),
        permission_mode=PermissionLevel.FULL_CONTROL,
    )

    result = await service.connect_target(
        ConnectTargetRequest(
            backend=BackendKind.GENERIC_REMOTE,
            endpoint="localhost:3333",
        ),
    )

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "SESSION_FACTORY_UNAVAILABLE"


@pytest.mark.asyncio
async def test_tool_service_connect_registers_created_session(tmp_path: Path) -> None:
    created = FakeToolSession()

    async def factory(_request: ConnectTargetRequest) -> FakeToolSession:
        return created

    service = ToolService(
        sessions=SessionManager(),
        policy=PolicyEngine(),
        audit_writer=JsonlAuditWriter(tmp_path / "audit.jsonl"),
        permission_mode=PermissionLevel.CONFIRM_REQUIRED,
        session_factory=factory,
    )

    result = await confirmed(
        service,
        "connect_target",
        ConnectTargetRequest(
            backend=BackendKind.GENERIC_REMOTE,
            endpoint="localhost:3333",
        ),
    )

    assert result.ok
    assert result.data is not None
    assert result.data.session_id == "session_01"
    assert service.sessions.get("session_01") is created


@pytest.mark.asyncio
async def test_tool_service_rejects_invalid_confirmation_token(tmp_path: Path) -> None:
    service, session = make_service(tmp_path, permission=PermissionLevel.CONFIRM_REQUIRED)

    result = await service.halt(
        HaltRequest(session_id="session_01"),
        confirmation_token="not-issued",
    )

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "INVALID_CONFIRMATION_TOKEN"
    assert session.calls == []


@pytest.mark.asyncio
async def test_tool_service_enforces_resource_limits(tmp_path: Path) -> None:
    service, _session = make_service(tmp_path)
    service.resource_limits = ResourceLimits(
        max_sessions=1,
        max_memory_read_bytes=2,
        max_memory_write_bytes=1,
        max_snapshot_stack_bytes=8,
    )

    memory = await service.read_memory(
        ReadMemoryRequest(session_id="session_01", address="0x20000000", length=4)
    )
    write = await service.write_memory(
        WriteMemoryRequest(session_id="session_01", address="0x20000000", data_hex="0102")
    )
    snapshot = await service.debug_snapshot(
        DebugSnapshotRequest(session_id="session_01", include_stack=True, stack_bytes=16)
    )
    connect = await service.connect_target(
        ConnectTargetRequest(
            backend=BackendKind.GENERIC_REMOTE,
            endpoint="localhost:3333",
        )
    )

    assert memory.error is not None
    assert memory.error.code == "RESOURCE_LIMIT_EXCEEDED"
    assert write.error is not None
    assert write.error.code == "RESOURCE_LIMIT_EXCEEDED"
    assert snapshot.error is not None
    assert snapshot.error.code == "RESOURCE_LIMIT_EXCEEDED"
    assert connect.error is not None
    assert connect.error.code == "RESOURCE_LIMIT_EXCEEDED"

@pytest.mark.asyncio
async def test_tool_service_rejects_concurrent_session_operation(tmp_path: Path) -> None:
    service, session = make_service(tmp_path, permission=PermissionLevel.FULL_CONTROL)
    service.resource_limits = ResourceLimits(max_session_operations=1)
    resume_started = asyncio.Event()
    release_resume = asyncio.Event()

    async def slow_resume(*, max_run_ms: int, auto_interrupt: bool = True) -> TargetState:
        session.calls.append(f"resume:{max_run_ms}:{auto_interrupt}")
        resume_started.set()
        await release_resume.wait()
        return TargetState.RUNNING

    session.resume = slow_resume  # type: ignore[method-assign]
    first = asyncio.create_task(
        service.resume(ResumeRequest(session_id="session_01", max_run_ms=100))
    )
    await resume_started.wait()

    second = await service.read_registers(ReadRegistersRequest(session_id="session_01"))
    release_resume.set()
    first_result = await first

    assert first_result.ok
    assert second.error is not None
    assert second.error.code == "RESOURCE_LIMIT_EXCEEDED"

@pytest.mark.asyncio
async def test_tool_service_surfaces_hardware_interlock_warnings(tmp_path: Path) -> None:
    service, session = make_service(tmp_path, permission=PermissionLevel.FULL_CONTROL)
    service.target_class = TargetClass.PRODUCTION_HARDWARE

    denied = await service.reset_target(
        ResetTargetRequest(session_id="session_01", mode=ResetMode.HALT)
    )
    service.hardware_operation_allowlist = frozenset({DebugOperation.RESET_TARGET})
    confirmed_result = await confirmed(
        service,
        "reset_target",
        ResetTargetRequest(session_id="session_01", mode=ResetMode.HALT),
        session,
    )

    assert denied.error is not None
    assert denied.error.code == "PERMISSION_DENIED"
    assert denied.warnings
    assert confirmed_result.ok
    assert confirmed_result.warnings


@pytest.mark.asyncio
async def test_tool_service_snapshot_and_fault_analysis(tmp_path: Path) -> None:
    service, _session = make_service(tmp_path)

    snapshot_result = await service.debug_snapshot(
        DebugSnapshotRequest(session_id="session_01", include_stack=False)
    )

    assert snapshot_result.ok
    assert snapshot_result.data is not None

    analysis = await service.analyze_fault(
        AnalyzeFaultRequest(snapshot_id=snapshot_result.data.snapshot_id)
    )

    assert analysis.ok
    assert analysis.data is not None
    assert analysis.data.fault_type == "UsageFault: INVSTATE"


@pytest.mark.asyncio
async def test_tool_service_compare_explain_and_suggest(tmp_path: Path) -> None:
    service, _session = make_service(tmp_path)

    first = await service.debug_snapshot(DebugSnapshotRequest(session_id="session_01"))
    second = await service.debug_snapshot(DebugSnapshotRequest(session_id="session_01"))
    assert first.data is not None
    assert second.data is not None

    compare = await service.compare_snapshots(
        CompareSnapshotsRequest(
            before_snapshot_id=first.data.snapshot_id,
            after_snapshot_id=second.data.snapshot_id,
        )
    )
    explain = await service.explain_current_state(
        ExplainCurrentStateRequest(snapshot_id=first.data.snapshot_id)
    )
    suggest = await service.suggest_next_debug_steps(
        SuggestNextDebugStepsRequest(snapshot_id=first.data.snapshot_id, goal="triage")
    )

    assert compare.ok
    assert compare.data is not None
    assert "No register" in compare.data.summary
    assert explain.ok
    assert suggest.ok
    assert suggest.data is not None
    assert suggest.data.actions[0].tool_name == "analyze_fault"


@pytest.mark.asyncio
async def test_tool_service_inspects_peripheral_from_svd(tmp_path: Path) -> None:
    svd_path = tmp_path / "demo.svd"
    svd_path.write_text(
        """
<device><name>Demo</name><peripherals><peripheral>
<name>GPIOA</name><baseAddress>0x40020000</baseAddress>
<registers><register><name>MODER</name><addressOffset>0x00</addressOffset>
<fields><field><name>MODE0</name><bitOffset>0</bitOffset><bitWidth>2</bitWidth></field>
</fields></register></registers>
</peripheral></peripherals></device>
""",
        encoding="utf-8",
    )
    service, _session = make_service(tmp_path)

    result = await service.inspect_peripheral(
        InspectPeripheralRequest(
            session_id="session_01",
            svd_path=str(svd_path),
            peripheral="GPIOA",
        )
    )

    assert result.ok
    assert result.data is not None
    assert result.data.device == "Demo"
    assert result.data.registers[0].name == "MODER"


@pytest.mark.asyncio
async def test_tool_service_reports_missing_session(tmp_path: Path) -> None:
    service, _session = make_service(tmp_path)

    result = await service.read_registers(ReadRegistersRequest(session_id="missing"))

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "SESSION_NOT_FOUND"


@pytest.mark.asyncio
async def test_tool_service_reports_missing_snapshot(tmp_path: Path) -> None:
    service, _session = make_service(tmp_path)

    result = await service.analyze_fault(AnalyzeFaultRequest(snapshot_id="missing"))

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "SNAPSHOT_NOT_FOUND"


@pytest.mark.asyncio
async def test_tool_service_analyze_fault_requires_snapshot_id(tmp_path: Path) -> None:
    service, _session = make_service(tmp_path)

    result = await service.analyze_fault(AnalyzeFaultRequest(session_id="session_01"))

    assert not result.ok
    assert result.error is not None
    assert result.error.code == "SNAPSHOT_REQUIRED"

"""Shared MCP tool schemas.

These models define the stable JSON contracts used by ProbeMCP tools. They are
deliberately independent of the future GDB/MI implementation so MCP clients can
rely on consistent request, response, and error shapes.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonScalar] | dict[str, JsonScalar]


class SchemaModel(BaseModel):
    """Base model for public MCP schemas."""

    model_config = ConfigDict(extra="forbid")


class PermissionLevel(StrEnum):
    """Permission mode required to execute a tool."""

    READONLY = "readonly"
    CONFIRM_REQUIRED = "confirm-required"
    FULL_CONTROL = "full-control"


class TargetState(StrEnum):
    """Known target/session state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    HALTED = "halted"
    RUNNING = "running"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"


class ErrorCategory(StrEnum):
    """High-level error category for MCP tool failures."""

    PERMISSION = "permission"
    TIMEOUT = "timeout"
    TARGET = "target"
    GDB = "gdb"
    VALIDATION = "validation"
    INTERNAL = "internal"


class BackendKind(StrEnum):
    """Supported backend adapter identifiers."""

    GENERIC_REMOTE = "generic-remote"
    QEMU = "qemu"
    OPENOCD = "openocd"
    JLINK = "jlink"
    PYOCD = "pyocd"


class RegisterGroup(StrEnum):
    """Register groups exposed by read_registers."""

    CORE = "core"
    FAULT = "fault"
    ALL = "all"


class ResetMode(StrEnum):
    """Reset behavior requested by reset_target."""

    HALT = "halt"
    RUN = "run"


class BreakpointType(StrEnum):
    """Breakpoint insertion strategy."""

    HARDWARE = "hardware"
    SOFTWARE = "software"


class HaltPolicy(StrEnum):
    """Snapshot behavior when the target may be running."""

    REQUIRE_ALREADY_HALTED = "require_already_halted"
    HALT_IF_RUNNING = "halt_if_running"


class DetailLevel(StrEnum):
    """Human-facing explanation detail level."""

    BRIEF = "brief"
    NORMAL = "normal"
    VERBOSE = "verbose"


class DebugError(SchemaModel):
    """Structured error returned by a tool result."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    category: ErrorCategory
    retryable: bool = False
    details: dict[str, JsonValue] = Field(default_factory=dict)
    required_permission: PermissionLevel | None = None
    confirmation_token: str | None = None


class ToolResult[DataT](SchemaModel):
    """Common result envelope returned by all ProbeMCP tools."""

    ok: bool
    session_id: str | None = None
    target_state: TargetState = TargetState.UNKNOWN
    data: DataT | None = None
    warnings: list[str] = Field(default_factory=list)
    audit_id: str | None = None
    error: DebugError | None = None

    @model_validator(mode="after")
    def validate_result_shape(self) -> Self:
        """Keep success and failure envelopes unambiguous."""

        if self.ok and self.error is not None:
            raise ValueError("successful tool results must not include error")
        if not self.ok and self.error is None:
            raise ValueError("failed tool results must include error")
        return self


class SessionRequest(SchemaModel):
    """Base request for tools that operate on an existing debug session."""

    session_id: str = Field(min_length=1)


class TimeoutRequest(SchemaModel):
    """Mixin-like base for bounded operations."""

    timeout_ms: int = Field(default=3000, ge=1, le=120_000)


class ConnectTargetRequest(TimeoutRequest):
    """Request for connect_target."""

    backend: BackendKind
    gdb_path: str = Field(default="arm-none-eabi-gdb", min_length=1)
    elf_path: str | None = None
    endpoint: str | None = None
    profile: str = Field(default="cortex-m", min_length=1)
    timeout_ms: int = Field(default=30_000, ge=1, le=120_000)


class ConnectTargetData(SchemaModel):
    """Connection result metadata."""

    session_id: str
    backend: BackendKind
    architecture: str | None = None
    profile: str
    state: TargetState


class DisconnectTargetRequest(SessionRequest, TimeoutRequest):
    """Request for disconnect_target."""

    kill_backend: bool = False
    timeout_ms: int = Field(default=5000, ge=1, le=120_000)


class HaltRequest(SessionRequest, TimeoutRequest):
    """Request for halt."""

    timeout_ms: int = Field(default=2000, ge=1, le=120_000)


class HaltData(SchemaModel):
    """Halt result."""

    stop_reason: str | None = None
    pc: str | None = None


class ResumeRequest(SessionRequest):
    """Request for bounded resume."""

    max_run_ms: int = Field(ge=1, le=120_000)
    auto_interrupt: bool = True


class ResumeData(SchemaModel):
    """Resume result."""

    stop_reason: str | None = None
    interrupted: bool = False
    pc: str | None = None


class StepInstructionRequest(SessionRequest, TimeoutRequest):
    """Request for step_instruction."""

    count: int = Field(default=1, ge=1, le=100)
    timeout_ms: int = Field(default=5000, ge=1, le=120_000)


class StepInstructionData(SchemaModel):
    """Step result."""

    pc: str | None = None
    changed_registers: dict[str, str] = Field(default_factory=dict)


class ResetTargetRequest(SessionRequest, TimeoutRequest):
    """Request for reset_target."""

    mode: ResetMode = ResetMode.HALT
    timeout_ms: int = Field(default=10_000, ge=1, le=120_000)


class ResetTargetData(SchemaModel):
    """Reset result."""

    mode: ResetMode
    state: TargetState


class ReadRegistersRequest(SessionRequest):
    """Request for read_registers."""

    group: RegisterGroup = RegisterGroup.CORE


class ReadRegistersData(SchemaModel):
    """Register values keyed by canonical register name."""

    registers: dict[str, str]


class ReadMemoryRequest(SessionRequest, TimeoutRequest):
    """Request for read_memory."""

    address: str = Field(min_length=1)
    length: int = Field(ge=1, le=4096)
    width: int = Field(default=1, ge=1, le=8)
    timeout_ms: int = Field(default=3000, ge=1, le=120_000)


class ReadMemoryData(SchemaModel):
    """Memory bytes returned as hex."""

    address: str
    length: int
    width: int
    data_hex: str


class WriteMemoryRequest(SessionRequest, TimeoutRequest):
    """Request for write_memory.

    This schema is defined for contract stability, but the operation should
    remain disabled by default in v0.1 safety policy.
    """

    address: str = Field(min_length=1)
    data_hex: str = Field(min_length=2)
    expected_old_hex: str | None = None
    timeout_ms: int = Field(default=3000, ge=1, le=120_000)


class WriteMemoryData(SchemaModel):
    """Memory write result."""

    address: str
    bytes_written: int = Field(ge=0)


class BreakpointLocation(SchemaModel):
    """Structured breakpoint location."""

    kind: Literal["symbol", "address", "file-line"]
    value: str = Field(min_length=1)


class SetBreakpointRequest(SessionRequest, TimeoutRequest):
    """Request for set_breakpoint."""

    location: BreakpointLocation
    type: BreakpointType = BreakpointType.HARDWARE
    temporary: bool = False
    timeout_ms: int = Field(default=3000, ge=1, le=120_000)


class BreakpointData(SchemaModel):
    """Breakpoint metadata."""

    breakpoint_id: str
    location: BreakpointLocation
    type: BreakpointType
    temporary: bool = False


class ClearBreakpointRequest(SessionRequest, TimeoutRequest):
    """Request for clear_breakpoint."""

    breakpoint_id: str = Field(min_length=1)
    timeout_ms: int = Field(default=3000, ge=1, le=120_000)


class ClearBreakpointData(SchemaModel):
    """Clear breakpoint result."""

    breakpoint_id: str
    removed: bool


class DebugSnapshotRequest(SessionRequest):
    """Request for debug_snapshot."""

    halt_policy: HaltPolicy = HaltPolicy.REQUIRE_ALREADY_HALTED
    include_core_registers: bool = True
    include_fault_registers: bool = True
    include_stack: bool = False
    stack_bytes: int = Field(default=128, ge=0, le=4096)


class DebugSnapshotData(SchemaModel):
    """Snapshot creation result."""

    snapshot_id: str
    state: TargetState
    summary: str


class AnalyzeFaultRequest(SchemaModel):
    """Request for analyze_fault."""

    session_id: str | None = None
    snapshot_id: str | None = None

    @model_validator(mode="after")
    def require_session_or_snapshot(self) -> Self:
        """Fault analysis needs either a live session or an existing snapshot."""

        if self.session_id is None and self.snapshot_id is None:
            raise ValueError("session_id or snapshot_id is required")
        return self


class FaultAnalysisData(SchemaModel):
    """Cortex-M fault analysis result."""

    fault_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    decoded_registers: dict[str, JsonValue] = Field(default_factory=dict)


class CompareSnapshotsRequest(SchemaModel):
    """Request for compare_snapshots."""

    before_snapshot_id: str
    after_snapshot_id: str
    include_memory_diffs: bool = False


class SnapshotDiffData(SchemaModel):
    """Snapshot comparison result."""

    register_diffs: dict[str, tuple[str | None, str | None]] = Field(default_factory=dict)
    memory_diffs: list[dict[str, JsonValue]] = Field(default_factory=list)
    summary: str


class ExplainCurrentStateRequest(SchemaModel):
    """Request for explain_current_state."""

    session_id: str | None = None
    snapshot_id: str | None = None
    detail_level: DetailLevel = DetailLevel.NORMAL

    @model_validator(mode="after")
    def require_session_or_snapshot(self) -> Self:
        """State explanation needs either a live session or an existing snapshot."""

        if self.session_id is None and self.snapshot_id is None:
            raise ValueError("session_id or snapshot_id is required")
        return self


class ExplainCurrentStateData(SchemaModel):
    """Natural-language state explanation with structured evidence."""

    summary: str
    evidence: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SuggestNextDebugStepsRequest(SchemaModel):
    """Request for suggest_next_debug_steps."""

    session_id: str | None = None
    snapshot_id: str | None = None
    goal: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_session_or_snapshot(self) -> Self:
        """Suggestions need either a live session or an existing snapshot."""

        if self.session_id is None and self.snapshot_id is None:
            raise ValueError("session_id or snapshot_id is required")
        return self


class SuggestedDebugAction(SchemaModel):
    """A safe next debugging action."""

    title: str
    rationale: str
    tool_name: str | None = None
    risk: Literal["low", "medium", "high"]
    required_permission: PermissionLevel


class SuggestNextDebugStepsData(SchemaModel):
    """Ranked next-step suggestions."""

    actions: list[SuggestedDebugAction]

from pydantic import ValidationError

from probemcp.mcp_server.schemas import (
    AnalyzeFaultRequest,
    BackendKind,
    ConnectTargetRequest,
    DebugError,
    ErrorCategory,
    PermissionLevel,
    ReadMemoryRequest,
    RegisterGroup,
    TargetState,
    ToolResult,
)


def test_success_tool_result_serializes_to_json_contract() -> None:
    result = ToolResult[dict[str, str]](
        ok=True,
        session_id="session_01",
        target_state=TargetState.HALTED,
        audit_id="audit_01",
        data={"pc": "0x08001234"},
    )

    assert result.model_dump(mode="json") == {
        "ok": True,
        "session_id": "session_01",
        "target_state": "halted",
        "data": {"pc": "0x08001234"},
        "warnings": [],
        "audit_id": "audit_01",
        "error": None,
    }


def test_failed_tool_result_requires_structured_error() -> None:
    error = DebugError(
        code="TARGET_RUNNING_REQUIRES_HALT",
        message="The target must be halted before reading core registers.",
        category=ErrorCategory.TARGET,
        retryable=True,
        required_permission=PermissionLevel.CONFIRM_REQUIRED,
    )

    result = ToolResult[None](
        ok=False,
        session_id="session_01",
        target_state=TargetState.RUNNING,
        error=error,
    )

    dumped = result.model_dump(mode="json")
    assert dumped["error"] == {
        "code": "TARGET_RUNNING_REQUIRES_HALT",
        "message": "The target must be halted before reading core registers.",
        "category": "target",
        "retryable": True,
        "details": {},
        "required_permission": "confirm-required",
        "confirmation_token": None,
    }


def test_tool_result_rejects_ambiguous_success_and_failure_shapes() -> None:
    error = DebugError(
        code="UNEXPECTED",
        message="Unexpected error.",
        category=ErrorCategory.INTERNAL,
    )

    try:
        ToolResult[None](ok=True, error=error)
    except ValidationError as exc:
        assert "successful tool results must not include error" in str(exc)
    else:
        raise AssertionError("expected success envelope with error to fail validation")

    try:
        ToolResult[None](ok=False)
    except ValidationError as exc:
        assert "failed tool results must include error" in str(exc)
    else:
        raise AssertionError("expected failure envelope without error to fail validation")


def test_connect_target_request_defaults_and_json_contract() -> None:
    request = ConnectTargetRequest(backend=BackendKind.QEMU)

    assert request.model_dump(mode="json") == {
        "timeout_ms": 30000,
        "backend": "qemu",
        "gdb_path": "arm-none-eabi-gdb",
        "elf_path": None,
        "endpoint": None,
        "profile": "cortex-m",
    }


def test_read_memory_request_bounds_length() -> None:
    request = ReadMemoryRequest(session_id="session_01", address="0x20000000", length=64)
    assert request.width == 1
    assert request.timeout_ms == 3000

    try:
        ReadMemoryRequest(session_id="session_01", address="0x20000000", length=4097)
    except ValidationError as exc:
        assert "less than or equal to 4096" in str(exc)
    else:
        raise AssertionError("expected oversized memory read to fail validation")


def test_analyze_fault_requires_session_or_snapshot() -> None:
    assert AnalyzeFaultRequest(snapshot_id="snapshot_01").snapshot_id == "snapshot_01"

    try:
        AnalyzeFaultRequest()
    except ValidationError as exc:
        assert "session_id or snapshot_id is required" in str(exc)
    else:
        raise AssertionError("expected missing analysis source to fail validation")


def test_register_group_serializes_as_tool_contract_value() -> None:
    payload = {"session_id": "session_01", "group": RegisterGroup.FAULT}

    assert payload["group"] == "fault"

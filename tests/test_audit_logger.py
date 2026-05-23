from pathlib import Path

from probemcp.audit.logger import AuditEvent, AuditOutcome, JsonlAuditWriter
from probemcp.mcp_server.schemas import DebugError, ErrorCategory, PermissionLevel, TargetState


def test_jsonl_audit_writer_appends_and_reads_events(tmp_path: Path) -> None:
    path = tmp_path / "audit" / "events.jsonl"
    writer = JsonlAuditWriter(path)

    event = AuditEvent(
        session_id="session_01",
        tool_name="read_registers",
        permission_mode=PermissionLevel.READONLY,
        target_state_before=TargetState.HALTED,
        target_state_after=TargetState.HALTED,
        outcome=AuditOutcome.SUCCESS,
        request_summary={"group": "core"},
        result_summary={"register_count": 16},
    )

    writer.append(event)

    assert path.read_text(encoding="utf-8").count("\n") == 1
    assert writer.read_events() == [event]


def test_jsonl_audit_writer_preserves_structured_errors(tmp_path: Path) -> None:
    writer = JsonlAuditWriter(tmp_path / "events.jsonl")
    error = DebugError(
        code="PERMISSION_DENIED",
        message="Memory writes are disabled by default.",
        category=ErrorCategory.PERMISSION,
        required_permission=PermissionLevel.FULL_CONTROL,
    )

    writer.append(
        AuditEvent(
            tool_name="write_memory",
            permission_mode=PermissionLevel.FULL_CONTROL,
            outcome=AuditOutcome.ERROR,
            error=error,
        )
    )

    [event] = writer.read_events()
    assert event.error == error
    assert event.outcome == AuditOutcome.ERROR

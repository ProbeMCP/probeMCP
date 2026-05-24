import pytest

from probemcp.errors import ErrorCode, make_error
from probemcp.mcp_server.schemas import ErrorCategory, HaltRequest, PermissionLevel
from probemcp.privacy import redact_mapping
from probemcp.safety.confirmation import ConfirmationError, ConfirmationTokenStore
from probemcp.safety.policy import DebugOperation


def test_confirmation_token_is_one_time_and_request_bound() -> None:
    clock = 1000.0
    store = ConfirmationTokenStore(ttl_seconds=10, clock=lambda: clock)
    request = HaltRequest(session_id="session_01")

    token = store.issue(DebugOperation.HALT, request)
    store.verify(token, DebugOperation.HALT, request)

    with pytest.raises(ConfirmationError, match="not found"):
        store.verify(token, DebugOperation.HALT, request)


def test_confirmation_token_rejects_mismatch_and_expiry() -> None:
    now = 1000.0
    store = ConfirmationTokenStore(ttl_seconds=1, clock=lambda: now)
    request = HaltRequest(session_id="session_01")

    mismatch = store.issue(DebugOperation.HALT, request)
    with pytest.raises(ConfirmationError, match="operation mismatch"):
        store.verify(mismatch, DebugOperation.RESUME, request)

    now = 2000.0
    expired = store.issue(DebugOperation.HALT, request)
    now = 2002.0
    with pytest.raises(ConfirmationError, match="expired"):
        store.verify(expired, DebugOperation.HALT, request)


def test_redaction_masks_paths_tokens_and_large_hex() -> None:
    redacted = redact_mapping(
        {
            "elf_path": "/Users/chamnp/private/build/firmware.elf",
            "confirmation_token": "secret-token",
            "data_hex": "aa" * 40,
            "nested": {"password": "pw"},
        }
    )

    assert redacted["elf_path"] == "<redacted-path:firmware.elf>"
    assert redacted["confirmation_token"] == "<redacted>"
    assert str(redacted["data_hex"]).startswith("aaaaaaaa")
    assert redacted["nested"] == {"password": "<redacted>"}


def test_make_error_uses_public_error_code() -> None:
    error = make_error(
        ErrorCode.PERMISSION_DENIED,
        "blocked",
        ErrorCategory.PERMISSION,
        required_permission=PermissionLevel.FULL_CONTROL,
    )

    assert error.code == "PERMISSION_DENIED"
    assert error.required_permission == PermissionLevel.FULL_CONTROL

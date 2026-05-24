"""Privacy-preserving redaction helpers for logs and diagnostics."""

from __future__ import annotations

from pathlib import PurePath
from typing import Any

SENSITIVE_KEY_FRAGMENTS = ("path", "token", "secret", "password", "key")
HEX_DUMP_KEYS = {"data_hex", "stack_data_hex", "contents"}


def redact_mapping(value: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow redacted copy of a mapping."""

    return {key: redact_value(key, item) for key, item in value.items()}


def redact_value(key: str, value: Any) -> Any:
    """Redact values that commonly contain local paths, secrets, or large dumps."""

    lowered = key.lower()
    if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
        if value is None:
            return None
        if "path" in lowered and isinstance(value, str):
            return f"<redacted-path:{PurePath(value).name}>"
        return "<redacted>"

    if lowered in HEX_DUMP_KEYS and isinstance(value, str) and len(value) > 32:
        return f"{value[:32]}...<redacted {len(value) - 32} chars>"

    if isinstance(value, dict):
        return redact_mapping(value)
    if isinstance(value, list):
        return [redact_value(key, item) for item in value]
    return value

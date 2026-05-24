"""Confirmation token management for target-changing tool calls."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from probemcp.safety.policy import DebugOperation


class ConfirmationError(RuntimeError):
    """Raised when a confirmation token cannot authorize an operation."""


@dataclass(frozen=True, slots=True)
class ConfirmationRecord:
    """Stored confirmation-token authorization."""

    operation: DebugOperation
    fingerprint: str
    expires_at: float


class ConfirmationTokenStore:
    """Issue and verify short-lived one-time confirmation tokens."""

    def __init__(self, *, ttl_seconds: int = 300, clock: Callable[[], float] = time.time) -> None:
        self.ttl_seconds = ttl_seconds
        self._clock = clock
        self._records: dict[str, ConfirmationRecord] = {}

    def issue(self, operation: DebugOperation, request: BaseModel) -> str:
        """Issue a one-time token bound to an operation and request body."""

        token = secrets.token_urlsafe(24)
        self._records[token] = ConfirmationRecord(
            operation=operation,
            fingerprint=fingerprint_request(request),
            expires_at=self._clock() + self.ttl_seconds,
        )
        return token

    def verify(self, token: str, operation: DebugOperation, request: BaseModel) -> None:
        """Consume a token if it matches the requested operation."""

        record = self._records.pop(token, None)
        if record is None:
            raise ConfirmationError("confirmation token was not found or was already used")
        if record.expires_at < self._clock():
            raise ConfirmationError("confirmation token expired")
        if record.operation != operation:
            raise ConfirmationError("confirmation token operation mismatch")
        if record.fingerprint != fingerprint_request(request):
            raise ConfirmationError("confirmation token request mismatch")


def fingerprint_request(request: BaseModel) -> str:
    """Return a deterministic fingerprint for a public request model."""

    encoded = json.dumps(
        request.model_dump(mode="json", exclude_none=True),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

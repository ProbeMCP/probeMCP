"""GDB/MI record models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

type MIValue = str | list["MIValue"] | dict[str, "MIValue"]


class MIRecordKind(StrEnum):
    """Top-level GDB/MI record kind."""

    RESULT = "result"
    EXEC_ASYNC = "exec-async"
    STATUS_ASYNC = "status-async"
    NOTIFY_ASYNC = "notify-async"
    CONSOLE_STREAM = "console-stream"
    TARGET_STREAM = "target-stream"
    LOG_STREAM = "log-stream"
    PROMPT = "prompt"


@dataclass(frozen=True, slots=True)
class MIRecord:
    """Parsed result or async record."""

    kind: MIRecordKind
    record_class: str
    results: dict[str, MIValue]
    raw: str
    token: int | None = None


@dataclass(frozen=True, slots=True)
class MIStreamRecord:
    """Parsed stream record."""

    kind: MIRecordKind
    text: str
    raw: str
    token: int | None = None

"""GDB/MI parser errors."""

from __future__ import annotations


class MIParseError(ValueError):
    """Raised when a GDB/MI line cannot be parsed."""

    def __init__(self, message: str, line: str, position: int = 0) -> None:
        self.line = line
        self.position = position
        super().__init__(f"{message} at position {position}: {line!r}")

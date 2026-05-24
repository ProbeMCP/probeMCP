"""Interfaces for future lab adapters."""

from __future__ import annotations

from typing import Protocol


class SerialCapture(Protocol):
    """Serial log capture adapter interface."""

    async def start(self) -> None:
        """Start capture."""

    async def stop(self) -> None:
        """Stop capture."""

    async def read_lines(self) -> list[str]:
        """Read captured lines."""


class PowerController(Protocol):
    """Power-control adapter interface."""

    async def power_on(self) -> None:
        """Power on the target."""

    async def power_off(self) -> None:
        """Power off the target."""

    async def power_cycle(self) -> None:
        """Power-cycle the target."""


class InMemorySerialCapture:
    """Test-friendly serial capture implementation."""

    def __init__(self) -> None:
        self.started = False
        self._lines: list[str] = []

    async def start(self) -> None:
        """Start capture."""

        self.started = True

    async def stop(self) -> None:
        """Stop capture."""

        self.started = False

    async def read_lines(self) -> list[str]:
        """Read captured lines."""

        return list(self._lines)

    def append_line(self, line: str) -> None:
        """Append one captured line."""

        self._lines.append(line)


class NoopPowerController:
    """Test-friendly power controller that records requested operations."""

    def __init__(self) -> None:
        self.actions: list[str] = []

    async def power_on(self) -> None:
        """Power on the target."""

        self.actions.append("on")

    async def power_off(self) -> None:
        """Power off the target."""

        self.actions.append("off")

    async def power_cycle(self) -> None:
        """Power-cycle the target."""

        self.actions.append("cycle")

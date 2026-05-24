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

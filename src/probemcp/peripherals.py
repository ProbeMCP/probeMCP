"""Peripheral snapshot diffing and simple misconfiguration heuristics."""

from __future__ import annotations

from pydantic import Field

from probemcp.mcp_server.schemas import PeripheralRegisterData, SchemaModel


class PeripheralDiff(SchemaModel):
    """One decoded peripheral register difference."""

    register: str
    before: str | None = None
    after: str | None = None
    changed_fields: dict[str, tuple[int | None, int | None]] = Field(default_factory=dict)


class PeripheralHeuristic(SchemaModel):
    """Evidence-linked peripheral advisory."""

    title: str
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


def diff_peripheral_registers(
    before: list[PeripheralRegisterData],
    after: list[PeripheralRegisterData],
) -> list[PeripheralDiff]:
    """Diff decoded peripheral register lists by register name."""

    before_by_name = {register.name: register for register in before}
    after_by_name = {register.name: register for register in after}
    diffs: list[PeripheralDiff] = []
    for name in sorted(set(before_by_name) | set(after_by_name)):
        before_register = before_by_name.get(name)
        after_register = after_by_name.get(name)
        before_value = before_register.value if before_register else None
        after_value = after_register.value if after_register else None
        changed_fields = _diff_fields(
            before_register.fields if before_register else {},
            after_register.fields if after_register else {},
        )
        if before_value != after_value or changed_fields:
            diffs.append(
                PeripheralDiff(
                    register=name,
                    before=before_value,
                    after=after_value,
                    changed_fields=changed_fields,
                )
            )
    return diffs


def detect_common_misconfigurations(
    peripheral: str,
    registers: list[PeripheralRegisterData],
) -> list[PeripheralHeuristic]:
    """Return conservative advisories for common decoded peripheral states."""

    advisories: list[PeripheralHeuristic] = []
    by_name = {register.name.upper(): register for register in registers}
    if peripheral.upper().startswith("GPIO"):
        moder = by_name.get("MODER")
        if moder and all(value == 0 for value in moder.fields.values()):
            advisories.append(
                PeripheralHeuristic(
                    title="GPIO pins appear to be in reset/input mode",
                    evidence=["MODER decoded fields are all zero."],
                    confidence=0.65,
                )
            )
    if peripheral.upper().startswith(("USART", "UART")):
        cr1 = by_name.get("CR1")
        if cr1 and cr1.fields.get("UE") == 0:
            advisories.append(
                PeripheralHeuristic(
                    title="UART peripheral is disabled",
                    evidence=["CR1.UE is 0."],
                    confidence=0.8,
                )
            )
    return advisories


def _diff_fields(
    before: dict[str, int],
    after: dict[str, int],
) -> dict[str, tuple[int | None, int | None]]:
    return {
        name: (before.get(name), after.get(name))
        for name in sorted(set(before) | set(after))
        if before.get(name) != after.get(name)
    }

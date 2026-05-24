"""Minimal FreeRTOS task-state models."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from probemcp.mcp_server.schemas import SchemaModel


class FreeRTOSTaskState(StrEnum):
    """Common FreeRTOS task states."""

    RUNNING = "running"
    READY = "ready"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"
    DELETED = "deleted"
    UNKNOWN = "unknown"


class FreeRTOSTask(SchemaModel):
    """Analyzer-friendly FreeRTOS task summary."""

    name: str
    state: FreeRTOSTaskState = FreeRTOSTaskState.UNKNOWN
    priority: int = Field(ge=0)
    stack_pointer: str | None = None
    stack_high_water_mark: int | None = Field(default=None, ge=0)
    current: bool = False


def summarize_tasks(tasks: list[FreeRTOSTask]) -> dict[str, object]:
    """Summarize a decoded FreeRTOS task list."""

    current = next((task for task in tasks if task.current), None)
    return {
        "task_count": len(tasks),
        "current_task": current.name if current else None,
        "states": {
            state.value: sum(1 for task in tasks if task.state == state)
            for state in FreeRTOSTaskState
            if any(task.state == state for task in tasks)
        },
        "low_stack_tasks": [
            task.name
            for task in tasks
            if task.stack_high_water_mark is not None and task.stack_high_water_mark < 32
        ],
    }


def decode_task_records(
    records: list[dict[str, object]],
    *,
    current_tcb: str | None = None,
) -> list[FreeRTOSTask]:
    """Decode sanitized FreeRTOS task records from fixture or debugger data."""

    tasks: list[FreeRTOSTask] = []
    for record in records:
        tcb = str(record.get("tcb", ""))
        tasks.append(
            FreeRTOSTask(
                name=str(record.get("name", "<unnamed>")),
                state=FreeRTOSTaskState(str(record.get("state", FreeRTOSTaskState.UNKNOWN))),
                priority=_int_value(record.get("priority"), default=0),
                stack_pointer=(
                    str(record["stack_pointer"])
                    if record.get("stack_pointer") is not None
                    else None
                ),
                stack_high_water_mark=(
                    _int_value(record.get("stack_high_water_mark"), default=0)
                    if record.get("stack_high_water_mark") is not None
                    else None
                ),
                current=bool(current_tcb and tcb == current_tcb),
            )
        )
    return tasks


def _int_value(value: object, *, default: int) -> int:
    if value is None:
        return default
    return int(str(value), 0)

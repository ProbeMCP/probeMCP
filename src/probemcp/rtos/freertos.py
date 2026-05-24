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

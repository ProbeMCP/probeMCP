"""Explicit debug session state machine."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field

from probemcp.mcp_server.schemas import SchemaModel, TargetState


class StateTransitionError(ValueError):
    """Raised when a requested session state transition is not legal."""


class StateTransition(SchemaModel):
    """A recorded session state transition."""

    from_state: TargetState
    to_state: TargetState
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


LEGAL_TRANSITIONS: dict[TargetState, frozenset[TargetState]] = {
    TargetState.DISCONNECTED: frozenset({TargetState.CONNECTING}),
    TargetState.CONNECTING: frozenset(
        {
            TargetState.HALTED,
            TargetState.RUNNING,
            TargetState.UNKNOWN,
            TargetState.DEGRADED,
            TargetState.DISCONNECTED,
        }
    ),
    TargetState.HALTED: frozenset(
        {
            TargetState.RUNNING,
            TargetState.UNKNOWN,
            TargetState.DEGRADED,
            TargetState.DISCONNECTED,
        }
    ),
    TargetState.RUNNING: frozenset(
        {
            TargetState.HALTED,
            TargetState.UNKNOWN,
            TargetState.DEGRADED,
            TargetState.DISCONNECTED,
        }
    ),
    TargetState.UNKNOWN: frozenset(
        {
            TargetState.CONNECTING,
            TargetState.HALTED,
            TargetState.RUNNING,
            TargetState.DEGRADED,
            TargetState.DISCONNECTED,
        }
    ),
    TargetState.DEGRADED: frozenset(
        {
            TargetState.CONNECTING,
            TargetState.UNKNOWN,
            TargetState.DISCONNECTED,
        }
    ),
}


class DebugSessionStateMachine:
    """Small state machine for one debug session."""

    def __init__(self, initial_state: TargetState = TargetState.DISCONNECTED) -> None:
        self._state = initial_state
        self._history: list[StateTransition] = []

    @property
    def state(self) -> TargetState:
        """Return the current session state."""

        return self._state

    @property
    def history(self) -> tuple[StateTransition, ...]:
        """Return transition history."""

        return tuple(self._history)

    def can_transition(self, to_state: TargetState) -> bool:
        """Return true if the requested transition is legal."""

        if to_state == self._state:
            return True
        return to_state in LEGAL_TRANSITIONS[self._state]

    def transition(self, to_state: TargetState, reason: str) -> StateTransition:
        """Move to a new state or raise if the transition is invalid."""

        if not self.can_transition(to_state):
            message = f"invalid transition from {self._state.value} to {to_state.value}"
            raise StateTransitionError(message)

        transition = StateTransition(
            from_state=self._state,
            to_state=to_state,
            reason=reason,
        )
        self._state = to_state
        self._history.append(transition)
        return transition

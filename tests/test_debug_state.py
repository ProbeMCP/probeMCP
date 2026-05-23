import pytest

from probemcp.debug.state import DebugSessionStateMachine, StateTransitionError
from probemcp.mcp_server.schemas import TargetState


def test_session_state_machine_records_legal_transitions() -> None:
    machine = DebugSessionStateMachine()

    first = machine.transition(TargetState.CONNECTING, "connect requested")
    second = machine.transition(TargetState.HALTED, "target stopped")
    third = machine.transition(TargetState.RUNNING, "resume requested")

    assert first.from_state == TargetState.DISCONNECTED
    assert second.to_state == TargetState.HALTED
    assert third.from_state == TargetState.HALTED
    assert machine.state == TargetState.RUNNING
    assert len(machine.history) == 3


def test_session_state_machine_rejects_invalid_transition() -> None:
    machine = DebugSessionStateMachine()

    with pytest.raises(StateTransitionError, match="invalid transition"):
        machine.transition(TargetState.RUNNING, "cannot run before connecting")


def test_unknown_state_can_recover_or_disconnect() -> None:
    machine = DebugSessionStateMachine(TargetState.UNKNOWN)

    assert machine.can_transition(TargetState.CONNECTING)
    assert machine.can_transition(TargetState.DISCONNECTED)

    machine.transition(TargetState.DISCONNECTED, "user reconnect required")
    assert machine.state == TargetState.DISCONNECTED

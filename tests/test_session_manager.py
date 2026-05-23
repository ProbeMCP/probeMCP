from typing import cast

import pytest

from probemcp.backends.generic_remote import GenericRemoteBackend
from probemcp.debug.session import DebugSession
from probemcp.mi.controller import MIController
from probemcp.sessions.manager import SessionManager, SessionNotFoundError


class DummyController:
    pass


def make_session(session_id: str) -> DebugSession:
    return DebugSession(
        controller=cast(MIController, DummyController()),
        backend=GenericRemoteBackend(),
        session_id=session_id,
    )


def test_session_manager_add_get_list_and_remove() -> None:
    manager = SessionManager()
    session = make_session("session_01")

    manager.add(session)

    assert manager.get("session_01") is session
    assert manager.list_ids() == ["session_01"]
    assert manager.remove("session_01") is session
    assert manager.list_ids() == []


def test_session_manager_raises_for_missing_session() -> None:
    manager = SessionManager()

    with pytest.raises(SessionNotFoundError):
        manager.get("missing")

    with pytest.raises(SessionNotFoundError):
        manager.remove("missing")

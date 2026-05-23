"""In-memory debug session manager."""

from __future__ import annotations

from dataclasses import dataclass, field

from probemcp.debug.session import DebugSession


class SessionNotFoundError(KeyError):
    """Raised when a session id does not exist."""


@dataclass(slots=True)
class SessionManager:
    """Own active debug sessions for the local MCP server."""

    _sessions: dict[str, DebugSession] = field(default_factory=dict)

    def add(self, session: DebugSession) -> None:
        """Register a session."""

        self._sessions[session.session_id] = session

    def get(self, session_id: str) -> DebugSession:
        """Return a session or raise."""

        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc

    def remove(self, session_id: str) -> DebugSession:
        """Remove and return a session."""

        try:
            return self._sessions.pop(session_id)
        except KeyError as exc:
            raise SessionNotFoundError(session_id) from exc

    def list_ids(self) -> list[str]:
        """List active session ids."""

        return sorted(self._sessions)

"""Local target inventory and session locking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pydantic import Field

from probemcp.mcp_server.schemas import BackendKind, SchemaModel
from probemcp.safety.policy import TargetClass


class LabTarget(SchemaModel):
    """One locally configured board or emulator."""

    target_id: str
    backend: BackendKind
    endpoint: str
    profile: str = "cortex-m"
    target_class: TargetClass = TargetClass.UNKNOWN


class TargetLock(SchemaModel):
    """A lease that grants temporary ownership of a target."""

    lock_id: str = Field(default_factory=lambda: f"lock_{uuid4().hex}")
    target_id: str
    owner: str
    expires_at: datetime

    def expired(self, now: datetime | None = None) -> bool:
        """Return true when the lock lease has expired."""

        return (now or datetime.now(UTC)) >= self.expires_at


class TargetInventory:
    """In-memory local target inventory with expiring locks."""

    def __init__(self, targets: list[LabTarget] | None = None) -> None:
        self._targets = {target.target_id: target for target in targets or []}
        self._locks: dict[str, TargetLock] = {}

    def add(self, target: LabTarget) -> None:
        """Add or replace a target."""

        self._targets[target.target_id] = target

    def list_targets(self) -> list[LabTarget]:
        """List targets sorted by ID."""

        return [self._targets[target_id] for target_id in sorted(self._targets)]

    def acquire(self, target_id: str, *, owner: str, ttl_seconds: int = 300) -> TargetLock:
        """Acquire a lock for a target."""

        if target_id not in self._targets:
            raise KeyError(f"target not found: {target_id}")

        existing = self._locks.get(target_id)
        if existing is not None and not existing.expired():
            raise RuntimeError(f"target is already locked by {existing.owner}")

        lock = TargetLock(
            target_id=target_id,
            owner=owner,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )
        self._locks[target_id] = lock
        return lock

    def release(self, lock_id: str) -> None:
        """Release a lock by ID."""

        for target_id, lock in list(self._locks.items()):
            if lock.lock_id == lock_id:
                del self._locks[target_id]
                return
        raise KeyError(f"lock not found: {lock_id}")

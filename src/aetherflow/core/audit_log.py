"""Audit log helpers for admin actions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """Single audit log entry."""

    action: str
    actor: str
    target: str


@dataclass(slots=True)
class AuditLog:
    """In-memory audit log."""

    entries: list[AuditEntry] = field(default_factory=list)

    def record(self, action: str, actor: str, target: str) -> None:
        """Record an audit event."""
        self.entries.append(AuditEntry(action=action, actor=actor, target=target))

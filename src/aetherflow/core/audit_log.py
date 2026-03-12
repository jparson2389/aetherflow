"""Audit log helpers for admin actions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

from loguru import logger


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """Single audit log entry."""

    action: str
    actor: str
    target: str
    timestamp_utc: datetime
    metadata: dict[str, object] = field(default_factory=dict)

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-serializable audit entry payload.

        Returns:
            A dictionary payload suitable for diagnostics exports.

        """
        return {
            'action': self.action,
            'actor': self.actor,
            'target': self.target,
            'timestamp_utc': self.timestamp_utc.isoformat(),
            'metadata': dict(self.metadata),
        }


@dataclass(slots=True)
class AuditLog:
    """In-memory audit log."""

    entries: list[AuditEntry] = field(default_factory=list)

    def record(
        self,
        action: str,
        actor: str,
        target: str,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        """Record an audit event.

        Args:
            action: Admin action identifier.
            actor: Actor identifier (user or service).
            target: Target identifier for the action.
            metadata: Optional metadata payload for the event.

        """
        entry = AuditEntry(
            action=action,
            actor=actor,
            target=target,
            timestamp_utc=datetime.now(UTC),
            metadata=dict(metadata or {}),
        )
        logger.debug('Audit log event recorded: {}', entry.action)
        self.entries.append(entry)

    def export_payload(self) -> list[dict[str, object]]:
        """Export audit entries for diagnostics payloads.

        Returns:
            List of audit entry payloads in recorded order.

        """
        return [entry.to_payload() for entry in self.entries]

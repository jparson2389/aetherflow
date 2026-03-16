"""Audit log helpers for admin actions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from aetherflow.core.settings import AetherflowSettings
from aetherflow.security.redaction import redact_sensitive_mapping


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
    """Append-only audit log."""

    entries: list[AuditEntry] = field(default_factory=list)
    storage_path: Path | None = None

    def __post_init__(self) -> None:
        """Initialize persistent storage and hydrate prior entries."""
        if self.storage_path is None:
            self.storage_path = AetherflowSettings().admin_audit_log_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.touch()
            return
        existing_entries: list[AuditEntry] = []
        for line in self.storage_path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            existing_entries.append(
                AuditEntry(
                    action=str(payload['action']),
                    actor=str(payload['actor']),
                    target=str(payload['target']),
                    timestamp_utc=datetime.fromisoformat(payload['timestamp_utc']),
                    metadata=dict(payload.get('metadata', {})),
                )
            )
        self.entries = existing_entries

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
            metadata=redact_sensitive_mapping(dict(metadata or {})),
        )
        logger.debug('Audit log event recorded: {}', entry.action)
        self.entries.append(entry)
        payload = json.dumps(entry.to_payload(), separators=(',', ':'))
        if self.storage_path:
            with self.storage_path.open('a', encoding='utf-8') as handle:
                handle.write(payload + '\n')

    def export_payload(self) -> list[dict[str, object]]:
        """Export audit entries for diagnostics payloads.

        Returns:
            List of audit entry payloads in recorded order.

        """
        return [entry.to_payload() for entry in self.entries]

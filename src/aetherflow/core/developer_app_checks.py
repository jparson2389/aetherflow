"""Persistence helpers for developer app-check alerts."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from loguru import logger

from aetherflow.core.verification_report import VerificationResult


@dataclass(slots=True)
class PendingAppCheck:
    """Represent one pending developer app-check alert.

    Attributes:
        item_id: Stable work-item identifier.
        message: Developer-facing alert message.
        app_surface: GUI or startup surface to check.

    """

    item_id: str
    message: str
    app_surface: str


@dataclass(slots=True)
class PendingAppCheckStore:
    """Manage pending developer alerts for newly verified app-testable items."""

    pending_path: Path
    snapshot_path: Path

    def sync_results(self, results: list[VerificationResult]) -> None:
        """Sync pending alerts from verification results.

        Args:
            results: Current verification results.

        """
        current_snapshot = {result.item_id: result.status for result in results}
        self._ensure_parent_dirs()

        if not self.snapshot_path.exists():
            self._write_snapshot(current_snapshot)
            self._write_pending([])
            logger.info(
                'Initialized app-check snapshot baseline with {} items.', len(results)
            )
            return

        previous_snapshot = self._read_snapshot()
        pending = {alert.item_id: alert for alert in self.pending_alerts()}

        for result in results:
            previous_status = previous_snapshot.get(result.item_id)
            if (
                result.app_testable
                and result.status == 'verified'
                and previous_status != 'verified'
                and result.developer_alert
                and result.app_surface
            ):
                pending[result.item_id] = PendingAppCheck(
                    item_id=result.item_id,
                    message=result.developer_alert,
                    app_surface=result.app_surface,
                )

        self._write_pending(list(pending.values()))
        self._write_snapshot(current_snapshot)

    def pending_alerts(self) -> list[PendingAppCheck]:
        """Return all pending alerts."""
        if not self.pending_path.exists():
            return []
        payload = json.loads(self.pending_path.read_text(encoding='utf-8'))
        return [
            PendingAppCheck(
                item_id=item['item_id'],
                message=item['message'],
                app_surface=item['app_surface'],
            )
            for item in payload.get('pending', [])
        ]

    def acknowledge(self, item_id: str) -> bool:
        """Acknowledge and remove one pending alert.

        Args:
            item_id: Stable work-item identifier.

        Returns:
            ``True`` when a pending alert with the given ``item_id`` was found
            and removed; ``False`` when no such alert exists.

        """
        pending = self.pending_alerts()
        remaining = [alert for alert in pending if alert.item_id != item_id]
        if len(remaining) == len(pending):
            return False
        self._write_pending(remaining)
        return True

    def _ensure_parent_dirs(self) -> None:
        """Create parent directories for store files."""
        self.pending_path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_snapshot(self) -> dict[str, str]:
        """Read the last-known verification snapshot."""
        if not self.snapshot_path.exists():
            return {}
        payload = json.loads(self.snapshot_path.read_text(encoding='utf-8'))
        return {key: str(value) for key, value in payload.get('items', {}).items()}

    def _write_snapshot(self, snapshot: dict[str, str]) -> None:
        """Write the last-known verification snapshot."""
        self.snapshot_path.write_text(
            json.dumps({'items': snapshot}, indent=2) + '\n',
            encoding='utf-8',
        )

    def _write_pending(self, pending: list[PendingAppCheck]) -> None:
        """Write the pending-alert payload."""
        self.pending_path.write_text(
            json.dumps(
                {'pending': [asdict(alert) for alert in pending]},
                indent=2,
            )
            + '\n',
            encoding='utf-8',
        )

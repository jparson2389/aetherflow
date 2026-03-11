"""Runtime state enumeration for host and UI surfaces."""

from __future__ import annotations

from enum import StrEnum


class RuntimeState(StrEnum):
    """User-visible runtime states."""

    RUNNING = 'RUNNING'
    DEGRADED = 'DEGRADED'
    RECOVERING = 'RECOVERING'
    FAILED = 'FAILED'
    LOCKED = 'LOCKED'
    GRACE = 'GRACE'

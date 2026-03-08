"""Device masking state helpers."""

from __future__ import annotations

from enum import Enum


class DeviceMaskState(str, Enum):
    """Device masking states."""

    ENABLED = "ENABLED"
    DISABLED = "DISABLED"


class DeviceMaskingService:
    """Track whether device masking is enabled."""

    def __init__(self) -> None:
        """Initialize the masking service in the disabled state."""
        self._state = DeviceMaskState.DISABLED

    def enable(self) -> None:
        """Enable masking."""
        self._state = DeviceMaskState.ENABLED

    def disable(self) -> None:
        """Disable masking."""
        self._state = DeviceMaskState.DISABLED

    @property
    def state(self) -> DeviceMaskState:
        """Return current masking state."""
        return self._state

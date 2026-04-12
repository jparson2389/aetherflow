"""Device masking state helpers."""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum


class DeviceMaskingError(RuntimeError):
    """Raised when a masking transition fails."""


class DeviceMaskState(StrEnum):
    """Device masking states."""

    ENABLED = 'ENABLED'
    DISABLED = 'DISABLED'


class DeviceMaskingService:
    """Track whether device masking is enabled."""

    def __init__(
        self,
        *,
        apply_state: Callable[[DeviceMaskState], None] | None = None,
    ) -> None:
        """Initialize the masking service in the disabled state."""
        self._state = DeviceMaskState.DISABLED
        self._apply_state = apply_state
        self._last_error: str | None = None

    def enable(self) -> None:
        """Enable masking."""
        self._transition(DeviceMaskState.ENABLED)

    def disable(self) -> None:
        """Disable masking."""
        self._transition(DeviceMaskState.DISABLED)

    def repair(self) -> None:
        """Clear the last masking error after remediation."""
        self._last_error = None

    @property
    def state(self) -> DeviceMaskState:
        """Return current masking state."""
        return self._state

    @property
    def last_error(self) -> str | None:
        """Return the last masking transition error."""
        return self._last_error

    def _transition(self, target: DeviceMaskState) -> None:
        """Apply a masking transition while preserving reversibility.

        Args:
            target: Desired masking state.

        Raises:
            DeviceMaskingError: If the transition fails.

        """
        previous = self._state
        try:
            if self._apply_state is not None:
                self._apply_state(target)
        except Exception as exc:
            self._state = previous
            self._last_error = str(exc)
            raise DeviceMaskingError(str(exc)) from exc
        self._state = target
        self._last_error = None

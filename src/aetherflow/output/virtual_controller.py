"""Virtual controller service state."""

from __future__ import annotations

from aetherflow.core.runtime_state import RuntimeState
from aetherflow.output.device_masking import DeviceMaskingService


class VirtualControllerService:
    """Represent the virtual output driver state."""

    def __init__(self, *, masking_service: DeviceMaskingService) -> None:
        """Create a virtual controller service.

        Args:
            masking_service: Device masking state provider.

        """
        self._masking_service = masking_service
        self._runtime_state = RuntimeState.RUNNING
        self._failure_reason: str | None = None

    def status(self) -> dict[str, object]:
        """Return an output-driver status snapshot."""
        return {
            'masking_state': self._masking_service.state,
            'signed_driver_required': True,
            'runtime_state': self._runtime_state,
            'failure_reason': self._failure_reason,
        }

    def mark_failed(self, reason: str) -> None:
        """Mark the output driver as failed without crashing the host."""
        self._runtime_state = RuntimeState.FAILED
        self._failure_reason = reason

    def mark_recovered(self) -> None:
        """Reset the output driver status after recovery."""
        self._runtime_state = RuntimeState.RUNNING
        self._failure_reason = None

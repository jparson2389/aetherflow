"""Virtual controller service state."""

from __future__ import annotations

from aetherflow.output.device_masking import DeviceMaskingService


class VirtualControllerService:
    """Represent the virtual output driver state."""

    def __init__(self, *, masking_service: DeviceMaskingService) -> None:
        """Create a virtual controller service.

        Args:
            masking_service: Device masking state provider.
        """
        self._masking_service = masking_service

    def status(self) -> dict[str, object]:
        """Return an output-driver status snapshot."""
        return {
            "masking_state": self._masking_service.state,
            "signed_driver_required": True,
        }

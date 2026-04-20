"""Virtual controller service state."""

from __future__ import annotations

from collections import deque

from aetherflow.core.runtime_state import RuntimeState
from aetherflow.output.device_masking import DeviceMaskingError, DeviceMaskingService


class VirtualControllerService:
    """Represent the virtual output driver state."""

    def __init__(self, *, masking_service: DeviceMaskingService) -> None:
        """Create a virtual controller service.

        Args:
            masking_service: Device masking state provider.

        """
        self._masking_service = masking_service
        self._driver_installed = False
        self._runtime_state = RuntimeState.RUNNING
        self._failure_reason: str | None = None
        self._diagnostics: deque[str] = deque(maxlen=20)

    def status(self) -> dict[str, object]:
        """Return an output-driver status snapshot."""
        return {
            'driver_installed': self._driver_installed,
            'masking_state': self._masking_service.state,
            'signed_driver_required': True,
            'runtime_state': self._runtime_state,
            'failure_reason': self._failure_reason,
            'diagnostics_retained': bool(self._diagnostics),
        }

    def install_driver(self) -> None:
        """Install the virtual controller driver."""
        self._driver_installed = True
        self._runtime_state = RuntimeState.RUNNING
        self._failure_reason = None
        self._record_diagnostic('driver-installed')

    def repair_driver(self) -> None:
        """Repair the driver and reset failure state."""
        self._driver_installed = True
        self._masking_service.repair()
        self.mark_recovered()
        self._record_diagnostic('driver-repaired')

    def enable_masking(self) -> bool:
        """Enable device masking without destabilizing the host.

        Returns:
            True when masking was enabled successfully.

        """
        return self._set_masking(enabled=True)

    def disable_masking(self) -> bool:
        """Disable device masking without destabilizing the host.

        Returns:
            True when masking was disabled successfully.

        """
        return self._set_masking(enabled=False)

    def mark_failed(self, reason: str) -> None:
        """Mark the output driver as failed without crashing the host."""
        self._runtime_state = RuntimeState.FAILED
        self._failure_reason = reason
        self._record_diagnostic(f'failure:{reason}')

    def mark_recovered(self) -> None:
        """Reset the output driver status after recovery."""
        self._runtime_state = RuntimeState.RUNNING
        self._failure_reason = None

    def copy_diagnostics(self) -> tuple[str, ...]:
        """Return retained diagnostics entries for failure analysis."""
        return tuple(self._diagnostics)

    def _set_masking(self, *, enabled: bool) -> bool:
        """Apply a masking transition and degrade only the output surface."""
        if not self._driver_installed:
            self.mark_failed('driver-not-installed')
            return False
        try:
            if enabled:
                self._masking_service.enable()
            else:
                self._masking_service.disable()
        except DeviceMaskingError as exc:
            self._runtime_state = RuntimeState.DEGRADED
            self._failure_reason = str(exc)
            self._record_diagnostic(f'masking-transition-failed:{exc}')
            return False
        self._runtime_state = RuntimeState.RUNNING
        self._failure_reason = None
        self._record_diagnostic('masking-enabled' if enabled else 'masking-disabled')
        return True

    def _record_diagnostic(self, message: str) -> None:
        """Retain a bounded diagnostics breadcrumb trail."""
        self._diagnostics.append(message)

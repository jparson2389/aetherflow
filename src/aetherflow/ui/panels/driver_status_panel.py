"""Driver status panel model and widget."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.runtime_state import RuntimeState
from aetherflow.output.device_masking import DeviceMaskState
from aetherflow.output.virtual_controller import VirtualControllerService


@dataclass(frozen=True, slots=True)
class DriverStatusPanelModel:
    """Driver installation and masking status."""

    installed: bool
    masking_enabled: bool
    actions: list[str]
    message: str
    runtime_state: RuntimeState = RuntimeState.RUNNING
    failure_reason: str | None = None
    diagnostics_available: bool = False

    @classmethod
    def from_service(cls, service: VirtualControllerService) -> DriverStatusPanelModel:
        """Build the panel state from the virtual controller service."""
        status = service.status()
        installed = bool(status['driver_installed'])
        masking_enabled = status['masking_state'] is DeviceMaskState.ENABLED
        runtime_state = status['runtime_state']
        failure_reason = status['failure_reason']
        diagnostics_available = bool(status['diagnostics_retained'])

        if runtime_state is RuntimeState.FAILED:
            return cls(
                installed=installed,
                masking_enabled=masking_enabled,
                actions=['install_driver', 'repair', 'retry', 'copy_diagnostics'],
                message='Driver failed; output disabled until recovery.',
                runtime_state=runtime_state,
                failure_reason=failure_reason,
                diagnostics_available=diagnostics_available,
            )
        if runtime_state is RuntimeState.DEGRADED:
            return cls(
                installed=installed,
                masking_enabled=masking_enabled,
                actions=['repair', 'retry_masking', 'copy_diagnostics'],
                message='Driver degraded; masking failure surfaced on the output panel.',
                runtime_state=runtime_state,
                failure_reason=failure_reason,
                diagnostics_available=diagnostics_available,
            )
        if installed:
            return cls(
                installed=True,
                masking_enabled=masking_enabled,
                actions=[
                    'repair',
                    'disable_masking' if masking_enabled else 'enable_masking',
                ],
                message='Driver installed; reversible masking actions available.',
                runtime_state=runtime_state,
                failure_reason=failure_reason,
                diagnostics_available=diagnostics_available,
            )
        return cls(
            installed=False,
            masking_enabled=False,
            actions=['install_driver'],
            message='Driver not installed; install before enabling masking.',
            runtime_state=runtime_state,
            failure_reason=failure_reason,
            diagnostics_available=diagnostics_available,
        )

    @classmethod
    def for_installed_driver(cls) -> DriverStatusPanelModel:
        """Return the installed-driver state."""
        return cls(
            installed=True,
            masking_enabled=True,
            actions=['repair', 'disable_masking'],
            message='Driver installed; reversible masking actions available.',
            runtime_state=RuntimeState.RUNNING,
        )

    @classmethod
    def for_failed_driver(cls) -> DriverStatusPanelModel:
        """Return the failed-driver state."""
        return cls(
            installed=False,
            masking_enabled=False,
            actions=['install_driver', 'repair', 'retry', 'copy_diagnostics'],
            message='Driver failed; output disabled until recovery.',
            runtime_state=RuntimeState.FAILED,
            diagnostics_available=True,
        )

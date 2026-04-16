"""Always-visible status HUD model."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.entitlements import EntitlementState
from aetherflow.core.runtime_state import RuntimeState


@dataclass(frozen=True, slots=True)
class StatusHUDModel:
    """UI status HUD view model."""

    input_plugin: str
    output_plugin: str
    capture_plugin: str
    display_plugin: str
    measured_fps: float
    jitter_ms: float
    worker_health: RuntimeState
    entitlement_state: EntitlementState
    runtime_state: RuntimeState
    show_expiry_modal: bool = False

    @property
    def show_grace_badge(self) -> bool:
        """Return whether the HUD should show the grace badge."""
        return self.entitlement_state is EntitlementState.GRACE

    @property
    def show_degraded_indicator(self) -> bool:
        """Return whether the HUD should show degraded or blocked runtime UX."""
        return self.runtime_state in {
            RuntimeState.DEGRADED,
            RuntimeState.RECOVERING,
            RuntimeState.FAILED,
        }

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-serializable HUD payload."""
        return {
            'plugins': {
                'input': self.input_plugin,
                'output': self.output_plugin,
                'capture': self.capture_plugin,
                'display': self.display_plugin,
            },
            'telemetry': {
                'measured_fps': self.measured_fps,
                'jitter_ms': self.jitter_ms,
            },
            'workers': {'health': self.worker_health.value},
            'entitlements': {
                'state': self.entitlement_state.value,
                'show_grace_badge': self.show_grace_badge,
            },
            'hud': {
                'show_degraded_indicator': self.show_degraded_indicator,
                'show_expiry_modal': self.show_expiry_modal,
            },
            'runtime_state': self.runtime_state.value,
        }

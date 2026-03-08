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

    def to_payload(self) -> dict[str, object]:
        """Return a JSON-serializable HUD payload."""
        return {
            "plugins": {
                "input": self.input_plugin,
                "output": self.output_plugin,
                "capture": self.capture_plugin,
                "display": self.display_plugin,
            },
            "telemetry": {
                "measured_fps": self.measured_fps,
                "jitter_ms": self.jitter_ms,
            },
            "workers": {"health": self.worker_health.value},
            "entitlements": {"state": self.entitlement_state.value},
            "runtime_state": self.runtime_state.value,
        }

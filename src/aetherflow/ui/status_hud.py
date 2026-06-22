"""Always-visible status HUD model."""

from __future__ import annotations

from dataclasses import dataclass

from aetherflow.core.entitlements import EntitlementState
from aetherflow.core.runtime_state import RuntimeState
from aetherflow.core.worker_supervisor import WorkerHealth, WorkerStateView


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

    @classmethod
    def from_host_state(
        cls,
        *,
        input_plugin: str,
        output_plugin: str,
        capture_plugin: str,
        display_plugin: str,
        measured_fps: float,
        jitter_ms: float,
        entitlement_state: EntitlementState,
        worker_state: WorkerStateView,
    ) -> StatusHUDModel:
        """Build a HUD model from host-reported worker state.

        Args:
            input_plugin: Active input plugin id.
            output_plugin: Active output plugin id.
            capture_plugin: Active capture plugin id.
            display_plugin: Active display plugin id.
            measured_fps: Measured frame rate.
            jitter_ms: Measured jitter in milliseconds.
            entitlement_state: Current entitlement state.
            worker_state: Host-reported worker state view.

        Returns:
            HUD model reflecting host-authored worker health.

        """
        worker_health = _runtime_state_from_worker_health(
            [snapshot.health for snapshot in worker_state.snapshot()]
        )
        return cls(
            input_plugin=input_plugin,
            output_plugin=output_plugin,
            capture_plugin=capture_plugin,
            display_plugin=display_plugin,
            measured_fps=measured_fps,
            jitter_ms=jitter_ms,
            worker_health=worker_health,
            entitlement_state=entitlement_state,
            runtime_state=worker_health,
        )

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
            'entitlements': {'state': self.entitlement_state.value},
            'runtime_state': self.runtime_state.value,
        }


def _runtime_state_from_worker_health(states: list[WorkerHealth]) -> RuntimeState:
    """Map host-reported worker health to the HUD runtime state.

    Args:
        states: Worker health states from host snapshots.

    Returns:
        Aggregate runtime state for the HUD.

    """
    if WorkerHealth.FAILED in states:
        return RuntimeState.FAILED
    if WorkerHealth.DEGRADED in states or WorkerHealth.RECOVERING in states:
        return RuntimeState.DEGRADED
    return RuntimeState.RUNNING

from aetherflow.core.entitlements import EntitlementState
from aetherflow.core.runtime_state import RuntimeState
from aetherflow.core.worker_supervisor import WorkerHealth, WorkerStateView
from aetherflow.ui.status_hud import StatusHUDModel


def test_status_hud_exposes_core_runtime_state() -> None:
    hud = StatusHUDModel(
        input_plugin='xinput',
        output_plugin='vigem',
        capture_plugin='capture.opencv',
        display_plugin='render.cpu',
        measured_fps=120.0,
        jitter_ms=1.4,
        worker_health=RuntimeState.RUNNING,
        entitlement_state=EntitlementState.GRACE,
        runtime_state=RuntimeState.DEGRADED,
    )

    payload = hud.to_payload()

    assert payload['plugins']['capture'] == 'capture.opencv'
    assert payload['telemetry']['measured_fps'] == 120.0
    assert payload['entitlements']['state'] == 'GRACE'
    assert payload['runtime_state'] == 'DEGRADED'


def test_status_hud_builds_worker_health_from_host_state_view() -> None:
    state_view = WorkerStateView()
    state_view.register('vision-worker')
    state_view.apply_crash_result(
        'vision-worker',
        health=WorkerHealth.FAILED,
        restart_count=3,
        restart_attempts_in_window=3,
    )

    hud = StatusHUDModel.from_host_state(
        input_plugin='xinput',
        output_plugin='vigem',
        capture_plugin='capture.opencv',
        display_plugin='render.cpu',
        measured_fps=0.0,
        jitter_ms=0.0,
        entitlement_state=EntitlementState.LOADED,
        worker_state=state_view,
    )

    payload = hud.to_payload()
    assert payload['workers']['health'] == 'FAILED'
    assert payload['runtime_state'] == 'FAILED'

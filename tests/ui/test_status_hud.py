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
    assert payload['entitlements']['show_grace_badge'] is True
    assert payload['hud']['show_degraded_indicator'] is True
    assert payload['hud']['show_expiry_modal'] is False
    assert payload['runtime_state'] == 'DEGRADED'


def test_status_hud_marks_locked_expiry_modal_state() -> None:
    hud = StatusHUDModel(
        input_plugin='xinput',
        output_plugin='vigem',
        capture_plugin='capture.mf',
        display_plugin='render.cpu',
        measured_fps=58.0,
        jitter_ms=3.2,
        worker_health=RuntimeState.RECOVERING,
        entitlement_state=EntitlementState.LOCKED,
        runtime_state=RuntimeState.DEGRADED,
        show_expiry_modal=True,
    )

    payload = hud.to_payload()

    assert payload['entitlements']['state'] == 'LOCKED'
    assert payload['entitlements']['show_grace_badge'] is False
    assert payload['hud']['show_degraded_indicator'] is True
    assert payload['hud']['show_expiry_modal'] is True


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


def test_status_hud_starting_worker_is_not_reported_running() -> None:
    state_view = WorkerStateView()
    state_view.register('vision-worker')  # defaults to STARTING, no heartbeat yet

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

    assert hud.to_payload()['runtime_state'] == 'DEGRADED'


def test_status_hud_empty_worker_set_is_not_reported_running() -> None:
    hud = StatusHUDModel.from_host_state(
        input_plugin='xinput',
        output_plugin='vigem',
        capture_plugin='capture.opencv',
        display_plugin='render.cpu',
        measured_fps=0.0,
        jitter_ms=0.0,
        entitlement_state=EntitlementState.LOADED,
        worker_state=WorkerStateView(),
    )

    assert hud.to_payload()['runtime_state'] == 'DEGRADED'

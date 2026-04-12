from aetherflow.core.entitlements import EntitlementState
from aetherflow.core.runtime_state import RuntimeState
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

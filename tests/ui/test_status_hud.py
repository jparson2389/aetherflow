from aetherflow.core.entitlements import EntitlementState
from aetherflow.ui.status_hud import StatusHUDModel


def test_status_hud_exposes_core_runtime_state() -> None:
    hud = StatusHUDModel(
        input_plugin="xinput",
        output_plugin="vigem",
        capture_plugin="capture.opencv",
        display_plugin="render.cpu",
        measured_fps=120.0,
        jitter_ms=1.4,
        worker_health="RUNNING",
        entitlement_state=EntitlementState.GRACE,
    )

    payload = hud.to_payload()

    assert payload["plugins"]["capture"] == "capture.opencv"
    assert payload["telemetry"]["measured_fps"] == 120.0
    assert payload["entitlements"]["state"] == "GRACE"

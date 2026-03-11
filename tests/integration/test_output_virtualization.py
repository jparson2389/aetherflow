from aetherflow.core.runtime_state import RuntimeState
from aetherflow.output.device_masking import DeviceMaskingService, DeviceMaskState
from aetherflow.output.virtual_controller import VirtualControllerService


def test_output_virtualization_reports_masking_state() -> None:
    masking = DeviceMaskingService()
    output = VirtualControllerService(masking_service=masking)

    masking.enable()
    status = output.status()

    assert status['masking_state'] is DeviceMaskState.ENABLED
    assert status['signed_driver_required'] is True


def test_output_failure_reports_degraded_state() -> None:
    masking = DeviceMaskingService()
    output = VirtualControllerService(masking_service=masking)

    output.mark_failed('driver-crash')
    status = output.status()

    assert status['runtime_state'] == RuntimeState.FAILED
    assert status['failure_reason'] == 'driver-crash'

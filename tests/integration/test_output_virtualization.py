from aetherflow.output.device_masking import DeviceMaskState, DeviceMaskingService
from aetherflow.output.virtual_controller import VirtualControllerService


def test_output_virtualization_reports_masking_state() -> None:
    masking = DeviceMaskingService()
    output = VirtualControllerService(masking_service=masking)

    masking.enable()
    status = output.status()

    assert status["masking_state"] is DeviceMaskState.ENABLED
    assert status["signed_driver_required"] is True

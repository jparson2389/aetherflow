from aetherflow.core.runtime_state import RuntimeState
from aetherflow.output.device_masking import DeviceMaskingService, DeviceMaskState
from aetherflow.output.virtual_controller import VirtualControllerService


def test_output_virtualization_reports_masking_state() -> None:
    masking = DeviceMaskingService()
    output = VirtualControllerService(masking_service=masking)

    output.install_driver()
    assert output.enable_masking() is True
    status = output.status()

    assert status['driver_installed'] is True
    assert status['masking_state'] is DeviceMaskState.ENABLED
    assert status['signed_driver_required'] is True
    assert status['runtime_state'] == RuntimeState.RUNNING


def test_output_masking_failure_is_reversible_and_retains_diagnostics() -> None:
    should_fail = {'value': True}

    def apply_state(target: DeviceMaskState) -> None:
        if should_fail['value'] and target is DeviceMaskState.ENABLED:
            raise RuntimeError('masking-driver-failure')

    masking = DeviceMaskingService(apply_state=apply_state)
    output = VirtualControllerService(masking_service=masking)
    output.install_driver()

    assert output.enable_masking() is False
    status = output.status()

    assert status['runtime_state'] == RuntimeState.DEGRADED
    assert status['failure_reason'] == 'masking-driver-failure'
    assert status['masking_state'] is DeviceMaskState.DISABLED
    assert status['diagnostics_retained'] is True
    assert any(
        'masking-transition-failed' in item for item in output.copy_diagnostics()
    )

    should_fail['value'] = False
    output.repair_driver()
    assert output.enable_masking() is True
    recovered = output.status()

    assert recovered['runtime_state'] == RuntimeState.RUNNING
    assert recovered['masking_state'] is DeviceMaskState.ENABLED


def test_output_failure_without_driver_install_disables_only_output_service() -> None:
    masking = DeviceMaskingService()
    output = VirtualControllerService(masking_service=masking)

    assert output.enable_masking() is False
    status = output.status()

    assert status['runtime_state'] == RuntimeState.FAILED
    assert status['failure_reason'] == 'driver-not-installed'
    assert output.copy_diagnostics()[-1] == 'failure:driver-not-installed'

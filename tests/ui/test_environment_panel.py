from aetherflow.core.env_manager import EnvironmentManager, GpuProbeStatus
from aetherflow.ui.panels.environment_panel import EnvironmentPanelModel


def test_environment_panel_builds_from_manager() -> None:
    """Build environment panel summaries from manager state."""
    manager = EnvironmentManager()
    manager.create('vision-env', python_version='3.12')
    manager.validate(
        'vision-env',
        required_imports={'numpy': True, 'torch': False},
        dependency_count=42,
        python_version='3.12',
        gpu_probe_status=GpuProbeStatus.UNSUPPORTED,
    )

    panel = EnvironmentPanelModel.from_manager(manager)

    assert panel.failed_count == 1
    assert panel.environments[0].name == 'vision-env'
    assert 'torch' in panel.environments[0].missing_imports

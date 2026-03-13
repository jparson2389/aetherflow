from aetherflow.core.worker_supervisor import WorkerHealth, WorkerSupervisor
from aetherflow.ui.panels.worker_health_panel import WorkerHealthPanelModel


def test_worker_health_panel_builds_from_supervisor() -> None:
    """Build worker health panel models from supervisor snapshots."""
    supervisor = WorkerSupervisor()
    supervisor.start('vision-worker')

    panels = WorkerHealthPanelModel.list_from_supervisor(supervisor)

    assert panels[0].worker_id == 'vision-worker'
    assert panels[0].health is WorkerHealth.RUNNING
    assert panels[0].to_payload()['restart_count'] == 0

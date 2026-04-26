from aetherflow.core.worker_supervisor import WorkerHealth, WorkerStateView
from aetherflow.ui.panels.worker_health_panel import WorkerHealthPanelModel


def test_worker_health_panel_builds_from_supervisor() -> None:
    """Build worker health panel models from supervisor snapshots."""
    supervisor = WorkerStateView()
    supervisor.register('vision-worker')
    supervisor.apply_heartbeat(
        'vision-worker', health=WorkerHealth.RUNNING, missed_heartbeats=0
    )

    panels = WorkerHealthPanelModel.list_from_supervisor(supervisor)

    assert panels[0].worker_id == 'vision-worker'
    assert panels[0].health is WorkerHealth.RUNNING
    assert panels[0].to_payload()['restart_count'] == 0

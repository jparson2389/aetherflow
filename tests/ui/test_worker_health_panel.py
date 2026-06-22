from aetherflow.core.worker_supervisor import WorkerHealth, WorkerStateView
from aetherflow.ui.panels.worker_health_panel import WorkerHealthPanelModel


def test_worker_health_panel_builds_from_host_state_view() -> None:
    """Build worker health panel models from host-reported snapshots."""
    state_view = WorkerStateView()
    state_view.register('vision-worker')
    state_view.apply_heartbeat(
        'vision-worker', health=WorkerHealth.RUNNING, missed_heartbeats=0
    )

    panels = WorkerHealthPanelModel.list_from_state_view(state_view)

    assert panels[0].worker_id == 'vision-worker'
    assert panels[0].health is WorkerHealth.RUNNING
    assert panels[0].to_payload()['restart_count'] == 0

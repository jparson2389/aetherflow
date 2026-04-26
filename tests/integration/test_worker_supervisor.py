"""Integration tests for WorkerStateView — the Python-side host state mirror.

These tests verify that WorkerStateView correctly applies host-reported state
and surfaces it to shell consumers.  Supervision decisions (restart budget,
state transitions) are made by the host C++ supervisor and are not re-tested
here.
"""

from aetherflow.core.worker_supervisor import WorkerHealth, WorkerStateView


def test_apply_heartbeat_stores_host_reported_health() -> None:
    view = WorkerStateView()
    view.register('vision-worker')

    view.apply_heartbeat(
        'vision-worker', health=WorkerHealth.RUNNING, missed_heartbeats=0
    )

    assert view.status('vision-worker') is WorkerHealth.RUNNING


def test_apply_heartbeat_reflects_degraded_from_host() -> None:
    view = WorkerStateView()
    view.register('vision-worker')

    view.apply_heartbeat(
        'vision-worker', health=WorkerHealth.DEGRADED, missed_heartbeats=2
    )

    assert view.status('vision-worker') is WorkerHealth.DEGRADED


def test_apply_crash_result_reflects_recovering_from_host() -> None:
    view = WorkerStateView()
    view.register('vision-worker')

    view.apply_crash_result(
        'vision-worker',
        health=WorkerHealth.RECOVERING,
        restart_count=1,
        restart_attempts_in_window=1,
    )

    assert view.status('vision-worker') is WorkerHealth.RECOVERING


def test_apply_heartbeat_after_recovery_clears_to_running() -> None:
    view = WorkerStateView()
    view.register('vision-worker')

    view.apply_crash_result(
        'vision-worker',
        health=WorkerHealth.RECOVERING,
        restart_count=1,
        restart_attempts_in_window=1,
    )
    view.apply_heartbeat(
        'vision-worker', health=WorkerHealth.RUNNING, missed_heartbeats=0
    )

    assert view.status('vision-worker') is WorkerHealth.RUNNING


def test_snapshot_reflects_host_reported_state() -> None:
    view = WorkerStateView()
    view.register('input-worker')

    view.apply_crash_result(
        'input-worker',
        health=WorkerHealth.RECOVERING,
        restart_count=2,
        restart_attempts_in_window=2,
    )

    snaps = view.snapshot()
    assert len(snaps) == 1
    snap = snaps[0]
    assert snap.worker_id == 'input-worker'
    assert snap.health is WorkerHealth.RECOVERING
    assert snap.restart_count == 2
    assert snap.restart_attempts_in_window == 2

"""Stress tests for WorkerStateView under repeated host-reported crash cycles.

These tests confirm that the view correctly stores budget-exhaustion state
reported by the C++ host supervisor across repeated crash signals.
"""

from aetherflow.core.worker_supervisor import WorkerHealth, WorkerStateView


def test_host_reported_failed_state_is_stored() -> None:
    """Host-reported FAILED (budget exhausted) is stored without modification."""
    view = WorkerStateView()
    view.register('vision-worker')

    view.apply_crash_result(
        'vision-worker',
        health=WorkerHealth.FAILED,
        restart_count=4,
        restart_attempts_in_window=4,
    )

    assert view.status('vision-worker') is WorkerHealth.FAILED


def test_repeated_crash_cycle_stores_final_host_state() -> None:
    """Repeated host crash reports leave the view in the last reported state."""
    view = WorkerStateView()
    view.register('cv-worker')

    view.apply_crash_result(
        'cv-worker',
        health=WorkerHealth.RECOVERING,
        restart_count=1,
        restart_attempts_in_window=1,
    )
    view.apply_crash_result(
        'cv-worker',
        health=WorkerHealth.RECOVERING,
        restart_count=2,
        restart_attempts_in_window=2,
    )
    view.apply_crash_result(
        'cv-worker',
        health=WorkerHealth.FAILED,
        restart_count=3,
        restart_attempts_in_window=3,
    )

    assert view.status('cv-worker') is WorkerHealth.FAILED


def test_snapshot_captures_restart_budget_counters() -> None:
    """Snapshot carries host-reported budget counters for shell HUD display."""
    view = WorkerStateView()
    view.register('output-worker')

    view.apply_crash_result(
        'output-worker',
        health=WorkerHealth.RECOVERING,
        restart_count=2,
        restart_attempts_in_window=2,
    )

    snaps = view.snapshot()
    assert snaps[0].restart_count == 2
    assert snaps[0].restart_attempts_in_window == 2

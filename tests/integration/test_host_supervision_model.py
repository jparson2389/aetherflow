"""Integration tests for the host supervision model's failure-isolation guarantees.

Tests 3.9.1-3.9.4: verify that the supervision model's core isolation,
budget-exhaustion, and recovery properties are correctly represented in the
Python state view.

The C++ host supervisor (WorkerSupervisorImpl) enforces these guarantees at
the native layer.  These tests confirm that WorkerStateView faithfully
mirrors them so that the PySide6 shell and plugin catalog reflect the correct
per-unit state.

Corresponds to PRD §9.1 (isolated worker lifetimes), §9.7 (shell durability),
and §10.1 (targeted restart).
"""

from aetherflow.core.worker_supervisor import WorkerHealth, WorkerStateView


def test_plugin_crash_does_not_affect_unrelated_unit() -> None:
    """3.9.1: A crash reported for unit A must not change the state of unit B.

    The shell (unit B) must remain STARTING (unregistered for transition) while
    a plugin unit (unit A) enters RECOVERING via a host crash report.
    """
    view = WorkerStateView()
    view.register('plugin-a')
    view.register('shell')

    view.apply_crash_result(
        'plugin-a',
        health=WorkerHealth.RECOVERING,
        restart_count=1,
        restart_attempts_in_window=1,
    )

    assert view.status('shell') is WorkerHealth.STARTING
    assert view.status('plugin-a') is WorkerHealth.RECOVERING


def test_running_unit_stays_running_after_isolated_failure() -> None:
    """3.9.2: Active unit B stays at RUNNING after unit A reports FAILED.

    Budget exhaustion for one unit (vision-worker) must not propagate
    to an unrelated unit (input-worker) that the host reports as healthy.
    """
    view = WorkerStateView()
    view.register('vision-worker')
    view.register('input-worker')

    view.apply_heartbeat(
        'input-worker', health=WorkerHealth.RUNNING, missed_heartbeats=0
    )

    view.apply_crash_result(
        'vision-worker',
        health=WorkerHealth.FAILED,
        restart_count=4,
        restart_attempts_in_window=4,
    )

    assert view.status('input-worker') is WorkerHealth.RUNNING
    assert view.status('vision-worker') is WorkerHealth.FAILED


def test_budget_exhaustion_stores_failed_not_recovering() -> None:
    """3.9.3: When the host reports FAILED (budget exhausted), state is FAILED.

    Budget exhaustion in the host results in a FAILED report; the view must
    store FAILED and not silently flip it to RECOVERING.
    """
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
        health=WorkerHealth.FAILED,
        restart_count=3,
        restart_attempts_in_window=3,
    )

    assert view.status('cv-worker') is WorkerHealth.FAILED


def test_successful_reload_restores_only_affected_unit() -> None:
    """3.9.4: A crash→RECOVERING→RUNNING cycle affects only the crashing unit.

    After unit A crashes and the host successfully reloads it, unit B's
    state must remain exactly as the host last reported it (RUNNING).
    """
    view = WorkerStateView()
    view.register('capture-worker')
    view.register('output-worker')

    view.apply_heartbeat(
        'output-worker', health=WorkerHealth.RUNNING, missed_heartbeats=0
    )

    view.apply_crash_result(
        'capture-worker',
        health=WorkerHealth.RECOVERING,
        restart_count=1,
        restart_attempts_in_window=1,
    )
    view.apply_heartbeat(
        'capture-worker', health=WorkerHealth.RUNNING, missed_heartbeats=0
    )

    assert view.status('capture-worker') is WorkerHealth.RUNNING
    assert view.status('output-worker') is WorkerHealth.RUNNING


def test_host_report_for_unregistered_worker_does_not_crash_view() -> None:
    """A host report for an unseen worker auto-registers instead of raising.

    Shell durability (PRD §9.7): a state report from the authoritative host
    for a worker the view has not registered must not crash the shell.
    """
    view = WorkerStateView()

    view.apply_heartbeat(
        'late-worker', health=WorkerHealth.RUNNING, missed_heartbeats=0
    )

    assert view.status('late-worker') is WorkerHealth.RUNNING

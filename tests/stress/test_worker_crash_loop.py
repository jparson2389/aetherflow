from aetherflow.core.worker_supervisor import WorkerHealth, WorkerSupervisor


class FakeClock:
    def __init__(self) -> None:
        self._now = 0.0

    def __call__(self) -> float:
        return self._now


def test_worker_supervisor_marks_failed_after_restart_budget_exhausted() -> None:
    clock = FakeClock()
    supervisor = WorkerSupervisor(max_restarts=2, restart_window_s=60.0, clock=clock)

    supervisor.start('vision-worker')
    supervisor.record_crash('vision-worker')
    supervisor.record_crash('vision-worker')
    supervisor.record_crash('vision-worker')

    assert supervisor.status('vision-worker') is WorkerHealth.FAILED

from aetherflow.core.worker_supervisor import WorkerHealth, WorkerSupervisor


class FakeClock:
    def __init__(self) -> None:
        self._now = 0.0

    def advance(self, seconds: float) -> None:
        self._now += seconds

    def __call__(self) -> float:
        return self._now


def test_worker_supervisor_recovers_after_retryable_failure() -> None:
    clock = FakeClock()
    supervisor = WorkerSupervisor(max_restarts=3, restart_window_s=60.0, clock=clock)

    supervisor.start("vision-worker")
    supervisor.record_missed_heartbeat("vision-worker")
    supervisor.record_missed_heartbeat("vision-worker")
    supervisor.record_missed_heartbeat("vision-worker")

    assert supervisor.status("vision-worker") is WorkerHealth.RECOVERING


def test_worker_supervisor_degrades_after_two_missed_heartbeats() -> None:
    supervisor = WorkerSupervisor(max_restarts=3)

    supervisor.start("vision-worker")
    supervisor.record_missed_heartbeat("vision-worker")
    supervisor.record_missed_heartbeat("vision-worker")

    assert supervisor.status("vision-worker") is WorkerHealth.DEGRADED

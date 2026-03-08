from aetherflow.core.worker_supervisor import WorkerHealth, WorkerSupervisor


def test_worker_supervisor_recovers_after_retryable_failure() -> None:
    supervisor = WorkerSupervisor(max_restarts=3)

    supervisor.start("vision-worker")
    supervisor.record_missed_heartbeat("vision-worker")
    supervisor.record_missed_heartbeat("vision-worker")
    supervisor.record_missed_heartbeat("vision-worker")

    assert supervisor.status("vision-worker") is WorkerHealth.RECOVERING

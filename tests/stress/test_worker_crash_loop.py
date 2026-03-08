from aetherflow.core.worker_supervisor import WorkerHealth, WorkerSupervisor


def test_worker_supervisor_marks_failed_after_restart_budget_exhausted() -> None:
    supervisor = WorkerSupervisor(max_restarts=2)

    supervisor.start("vision-worker")
    supervisor.record_crash("vision-worker")
    supervisor.record_crash("vision-worker")
    supervisor.record_crash("vision-worker")

    assert supervisor.status("vision-worker") is WorkerHealth.FAILED

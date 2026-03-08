from aetherflow.core.env_manager import EnvironmentManager, GpuProbeStatus


def test_environment_manager_creates_and_validates_env_metadata() -> None:
    manager = EnvironmentManager()
    record = manager.create("vision-cpu", python_version="3.12")

    assert record.name == "vision-cpu"
    assert record.validation_status == "pending"
    assert manager.summary(record.name)["python_version"] == "3.12"


def test_environment_manager_reports_missing_imports_and_gpu_probe() -> None:
    manager = EnvironmentManager()
    manager.create("vision-cpu", python_version="3.12")

    report = manager.validate(
        "vision-cpu",
        required_imports={"numpy": True, "torch": False},
        dependency_count=12,
        python_version="3.12",
        gpu_probe_status=GpuProbeStatus.UNSUPPORTED,
    )

    assert report["validation_status"] == "failed"
    assert report["missing_imports"] == ["torch"]
    assert report["gpu_probe_status"] == "unsupported"


def test_environment_manager_deletes_env_records() -> None:
    manager = EnvironmentManager()
    manager.create("vision-cpu", python_version="3.12")

    manager.delete("vision-cpu")

    assert manager.list_names() == []

from aetherflow.core.env_manager import EnvironmentManager


def test_environment_manager_creates_and_validates_env_metadata() -> None:
    manager = EnvironmentManager()
    record = manager.create("vision-cpu", python_version="3.12")

    assert record.name == "vision-cpu"
    assert record.validation_status == "pending"
    assert manager.summary(record.name)["python_version"] == "3.12"

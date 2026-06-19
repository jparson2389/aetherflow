from aetherflow.core.env_manager import EnvironmentManager, GpuProbeStatus


def test_environment_manager_creates_and_validates_env_metadata() -> None:
    manager = EnvironmentManager()
    record = manager.create('vision-cpu', python_version='3.12')

    assert record.name == 'vision-cpu'
    assert record.validation_status == 'pending'
    assert manager.summary(record.name)['python_version'] == '3.12'


def test_environment_manager_reports_missing_imports_and_gpu_probe() -> None:
    manager = EnvironmentManager()
    manager.create('vision-cpu', python_version='3.12')

    report = manager.validate(
        'vision-cpu',
        required_imports={'numpy': True, 'torch': False},
        dependency_count=12,
        python_version='3.12',
        gpu_probe_status=GpuProbeStatus.UNSUPPORTED,
    )

    assert report['validation_status'] == 'failed'
    assert report['missing_imports'] == ['torch']
    assert report['gpu_probe_status'] == 'unsupported'


def test_environment_manager_deletes_env_records() -> None:
    manager = EnvironmentManager()
    manager.create('vision-cpu', python_version='3.12')

    manager.delete('vision-cpu')

    assert manager.list_names() == []


def test_environment_manager_creates_runtime_environment_files(tmp_path) -> None:
    manager = EnvironmentManager(runtime_root=tmp_path)

    record = manager.create(
        'vision-cpu',
        python_version='3.12',
        requirements=['numpy==2.4.3', 'opencv-python==4.13.0.92'],
    )

    assert record.environment_path == tmp_path / 'vision-cpu'
    assert record.requirements_path == tmp_path / 'vision-cpu' / 'requirements.txt'
    assert record.environment_path.is_dir()
    assert record.requirements_path.read_text(encoding='utf-8') == (
        'numpy==2.4.3\nopencv-python==4.13.0.92\n'
    )


def test_environment_manager_deletes_runtime_environment_files(tmp_path) -> None:
    manager = EnvironmentManager(runtime_root=tmp_path)
    record = manager.create('vision-cpu', python_version='3.12')
    (record.environment_path / 'artifact.txt').write_text('payload', encoding='utf-8')

    manager.delete('vision-cpu')

    assert manager.list_names() == []
    assert not (tmp_path / 'vision-cpu').exists()


def test_environment_manager_validation_measures_disk_usage(tmp_path) -> None:
    manager = EnvironmentManager(runtime_root=tmp_path)
    record = manager.create('vision-cpu', python_version='3.12')
    (record.environment_path / 'artifact.bin').write_bytes(b'x' * 1024 * 1024)

    report = manager.validate(
        'vision-cpu',
        required_imports={'numpy': True},
        dependency_count=1,
        python_version='3.12',
        gpu_probe_status=GpuProbeStatus.SUPPORTED,
    )

    assert report['disk_usage_mb'] == 1

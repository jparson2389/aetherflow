from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_frozen_contract_files_exist() -> None:
    assert (PROJECT_ROOT / 'include' / 'plugin_system.hpp').is_file()
    assert (PROJECT_ROOT / 'proto' / 'capture.proto').is_file()
    assert (
        PROJECT_ROOT / 'src' / 'aetherflow' / 'core' / 'shared_memory_layout.py'
    ).is_file()


def test_breaking_change_logs_exist_for_frozen_contracts() -> None:
    assert (PROJECT_ROOT / 'docs' / 'breaking-changes' / 'abi.md').is_file()
    assert (PROJECT_ROOT / 'docs' / 'breaking-changes' / 'proto.md').is_file()
    assert (PROJECT_ROOT / 'docs' / 'breaking-changes' / 'shmem.md').is_file()
    assert (PROJECT_ROOT / 'docs' / 'breaking-changes' / 'entitlements.md').is_file()


def test_build_script_declares_windows_native_harness() -> None:
    build_script = (PROJECT_ROOT / 'scripts' / 'build-native.ps1').read_text(
        encoding='utf-8'
    )
    assert 'plugin_system.hpp' in build_script
    assert 'capture.proto' in build_script

from __future__ import annotations

from pathlib import Path

from src.aetherflow.core.plugin_system import Plugin, RuntimeState

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_frozen_contract_files_exist() -> None:
    assert (PROJECT_ROOT / 'include' / 'plugin_system.hpp').is_file()
    assert (PROJECT_ROOT / 'proto' / 'capture.proto').is_file()
    assert (
        PROJECT_ROOT / 'src' / 'aetherflow' / 'core' / 'shared_memory_layout.py'
    ).is_file()
    assert (PROJECT_ROOT / 'src' / 'aetherflow' / 'core' / 'plugin_system.py').is_file()


def test_breaking_change_logs_exist_for_frozen_contracts() -> None:
    abi_text = (PROJECT_ROOT / 'docs' / 'breaking-changes' / 'abi.md').read_text(
        encoding='utf-8'
    )
    proto_text = (PROJECT_ROOT / 'docs' / 'breaking-changes' / 'proto.md').read_text(
        encoding='utf-8'
    )
    shmem_text = (PROJECT_ROOT / 'docs' / 'breaking-changes' / 'shmem.md').read_text(
        encoding='utf-8'
    )
    entitlements_text = (
        PROJECT_ROOT / 'docs' / 'breaking-changes' / 'entitlements.md'
    ).read_text(encoding='utf-8')

    assert 'Freeze checkpoint:' in abi_text
    assert 'include/plugin_system.hpp' in abi_text
    assert 'Freeze checkpoint:' in proto_text
    assert 'proto/capture.proto' in proto_text
    assert 'Freeze checkpoint:' in shmem_text
    assert 'src/aetherflow/core/shared_memory_layout.py' in shmem_text
    assert 'entitlements.py' in entitlements_text


def test_python_abi_mirror_exports_frozen_contract_types() -> None:
    plugin = Plugin(
        plugin_id='frozen-plugin',
        name='Frozen Plugin',
        version='1.0.0',
        api_version='1.0',
        plugin_type='capture',
        required_entitlements=[],
        requires_drivers=[],
        requires_worker=False,
    )

    assert plugin.plugin_id == 'frozen-plugin'
    assert RuntimeState.LOCKED.value == 'LOCKED'
    assert RuntimeState.GRACE.value == 'GRACE'


def test_build_script_declares_windows_native_harness() -> None:
    build_script = (PROJECT_ROOT / 'scripts' / 'build-native.ps1').read_text(
        encoding='utf-8'
    )
    assert 'plugin_system.hpp' in build_script
    assert 'capture.proto' in build_script

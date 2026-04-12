from __future__ import annotations

from pathlib import Path

from src.aetherflow.core.plugin_system import Plugin, RuntimeState

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _extract_sign_off_entry(text: str) -> list[str]:
    """Return the bullet lines that belong to the sign-off entry section."""
    lines = text.splitlines()
    try:
        start_index = lines.index('Sign-off entry:') + 1
    except ValueError as error:
        raise AssertionError('Missing sign-off entry block.') from error

    entry_lines: list[str] = []
    current_line = ''
    for line in lines[start_index:]:
        if not line.strip():
            if entry_lines:
                break
            continue
        if line.startswith('- '):
            if current_line:
                entry_lines.append(current_line)
            current_line = line.strip()
            continue
        if current_line and line.startswith('  '):
            current_line = f'{current_line} {line.strip()}'
            continue
        if entry_lines or current_line:
            break

    if current_line:
        entry_lines.append(current_line)

    assert entry_lines, 'Missing sign-off entry block.'
    return entry_lines


def _assert_sign_off_entry(
    *,
    text: str,
    contract_path: str,
    scope: str,
    policy_fragment: str,
) -> None:
    """Assert that a frozen-contract log includes a structured sign-off entry."""
    entry_lines = _extract_sign_off_entry(text)

    assert '- Date: 2026-03-08' in entry_lines
    assert '- Approver: qa.lead' in entry_lines
    assert f'- Scope: {scope}' in entry_lines
    assert '- Change Class: freeze checkpoint' in entry_lines
    assert f'- Contract Path: {contract_path}' in entry_lines
    assert any(
        line.startswith('- Policy: Future changes require explicit human sign-off')
        and policy_fragment in line
        for line in entry_lines
    ), 'Structured sign-off policy line is missing required language.'


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
    assert 'Authenticode' in abi_text
    assert 'SHA-256' in abi_text
    assert 'RSA-3072' in abi_text
    assert 'No ABI breaking changes have been logged yet.' not in abi_text
    assert 'Freeze checkpoint:' in proto_text
    assert 'proto/capture.proto' in proto_text
    assert 'CaptureControl' in proto_text
    assert 'retry_budget_remaining' in proto_text
    assert 'No proto breaking changes have been logged yet.' not in proto_text
    assert 'Freeze checkpoint:' in shmem_text
    assert 'src/aetherflow/core/shared_memory_layout.py' in shmem_text
    assert 'DROP_OLDEST' in shmem_text
    assert 'BGR24' in shmem_text
    assert 'No shared-memory breaking changes have been logged yet.' not in shmem_text
    assert 'entitlements.py' in entitlements_text
    _assert_sign_off_entry(
        text=abi_text,
        contract_path='include/plugin_system.hpp',
        scope='Phase 0 ABI freeze published.',
        policy_fragment='breaking-change log entry before merge.',
    )
    _assert_sign_off_entry(
        text=proto_text,
        contract_path='proto/capture.proto',
        scope='Phase 0 proto freeze published.',
        policy_fragment='breaking-change entry before merge.',
    )
    _assert_sign_off_entry(
        text=shmem_text,
        contract_path='src/aetherflow/core/shared_memory_layout.py',
        scope='Phase 0 shared-memory freeze published.',
        policy_fragment='breaking-change entry before merge.',
    )


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


def test_native_header_publishes_frozen_signing_baseline() -> None:
    header_text = (PROJECT_ROOT / 'include' / 'plugin_system.hpp').read_text(
        encoding='utf-8'
    )

    assert 'kRequiredSignatureScheme = "Authenticode"' in header_text
    assert 'kRequiredDigestAlgorithm = "SHA-256"' in header_text
    assert 'kRequiredRsaKeyBits = 3072' in header_text
    for state_name in (
        'kRunning',
        'kDegraded',
        'kRecovering',
        'kFailed',
        'kLocked',
        'kGrace',
    ):
        assert state_name in header_text


def test_build_script_declares_windows_native_harness() -> None:
    build_script = (PROJECT_ROOT / 'scripts' / 'build-native.ps1').read_text(
        encoding='utf-8'
    )
    assert 'plugin_system.hpp' in build_script
    assert 'capture.proto' in build_script

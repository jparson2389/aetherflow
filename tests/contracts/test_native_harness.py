from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.shell_utils import resolve_powershell_executable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_RUNTIME_STATES = [
    'RUNNING',
    'DEGRADED',
    'RECOVERING',
    'FAILED',
    'LOCKED',
    'GRACE',
]


def _run_build_script() -> subprocess.CompletedProcess[str]:
    script_path = PROJECT_ROOT / 'scripts' / 'build-native.ps1'
    assert script_path.exists()

    return subprocess.run(
        [
            resolve_powershell_executable(),
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            str(script_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows-only: requires MSVC')
def test_build_native_harness_creates_executable_and_report() -> None:
    build_path = PROJECT_ROOT / 'build' / 'native_harness.exe'
    report_path = PROJECT_ROOT / 'build' / 'native_harness_report.json'
    if build_path.exists():
        build_path.unlink()
    if report_path.exists():
        report_path.unlink()

    result = _run_build_script()

    assert result.returncode == 0, result.stdout + result.stderr
    assert build_path.exists()
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding='utf-8'))

    assert report['header']['signature_scheme'] == 'Authenticode'
    assert report['header']['digest_algorithm'] == 'SHA-256'
    assert report['header']['rsa_key_bits'] == 3072
    assert report['header']['runtime_states'] == EXPECTED_RUNTIME_STATES
    assert report['proto']['service_name'] == 'CaptureControl'
    assert report['proto']['rpc_count'] == 6
    assert report['boundary']['src_native_files'] == []


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows-only: requires MSVC')
def test_native_harness_rejects_cpp_sources_inside_src(tmp_path: Path) -> None:
    result = _run_build_script()
    assert result.returncode == 0, result.stdout + result.stderr

    repo_root = tmp_path / 'repo'
    (repo_root / 'src').mkdir(parents=True)
    (repo_root / 'include').mkdir()
    (repo_root / 'proto').mkdir()

    header_path = repo_root / 'include' / 'plugin_system.hpp'
    proto_path = repo_root / 'proto' / 'capture.proto'
    output_path = repo_root / 'native_harness_report.json'

    header_path.write_text(
        (PROJECT_ROOT / 'include' / 'plugin_system.hpp').read_text(encoding='utf-8'),
        encoding='utf-8',
    )
    proto_path.write_text(
        (PROJECT_ROOT / 'proto' / 'capture.proto').read_text(encoding='utf-8'),
        encoding='utf-8',
    )
    (repo_root / 'src' / 'engine.cpp').write_text('int leaked_native = 1;\n')

    harness_result = subprocess.run(
        [
            str(PROJECT_ROOT / 'build' / 'native_harness.exe'),
            '--repo-root',
            str(repo_root),
            '--header',
            str(header_path),
            '--proto',
            str(proto_path),
            '--output',
            str(output_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert harness_result.returncode != 0
    assert 'Native source files are not allowed under src/' in (
        harness_result.stdout + harness_result.stderr
    )

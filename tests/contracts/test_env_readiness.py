from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_verify_env_generates_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, 'platform', 'win32')

    project_root = tmp_path
    report_path = project_root / 'logs' / 'env_report.json'
    script_path = project_root / 'scripts' / 'verify-env.ps1'
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text('# mocked verify-env script', encoding='utf-8')

    assert script_path.exists()

    expected_report = {
        'uv': {'available': True},
        'python': {'available': True},
        'powershell': {'available': True},
        'cl': {'available': True},
    }

    fake_powershell = '/usr/bin/fake-powershell'

    def _fake_subprocess_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command == [
            fake_powershell,
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            str(script_path),
        ]
        assert cwd == project_root
        assert check is False
        assert capture_output is True
        assert text is True
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(expected_report), encoding='utf-8')
        return subprocess.CompletedProcess(command, 0, stdout='ok', stderr='')

    monkeypatch.setattr(subprocess, 'run', _fake_subprocess_run)

    result = subprocess.run(
        [
            fake_powershell,
            '-ExecutionPolicy',
            'Bypass',
            '-File',
            str(script_path),
        ],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding='utf-8'))
    assert report['uv']['available'] is True
    assert report['python']['available'] is True
    assert report['powershell']['available'] is True
    assert report['cl']['available'] is True

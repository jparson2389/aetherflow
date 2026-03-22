from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools import check_quality


def test_scoped_python_targets_only_include_existing_python_files(tmp_path: Path) -> None:
    python_path = tmp_path / 'src' / 'feature.py'
    python_path.parent.mkdir(parents=True)
    python_path.write_text('print("ok")\n', encoding='utf-8')
    ignored_text = tmp_path / 'README.md'
    ignored_text.write_text('docs\n', encoding='utf-8')

    targets = check_quality.scoped_python_targets(
        tmp_path,
        ['src/feature.py', 'README.md', 'missing.py', '', 'src/feature.py'],
    )

    assert targets == ['src/feature.py']


def test_run_quality_gate_scoped_runs_ruff_and_pytest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    python_path = tmp_path / 'src' / 'feature.py'
    python_path.parent.mkdir(parents=True)
    python_path.write_text('print("ok")\n', encoding='utf-8')

    calls: list[list[str]] = []

    def fake_run(
        command: list[str], *, cwd: Path, capture_output: bool, text: bool, check: bool
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert cwd == tmp_path
        assert capture_output is True
        assert text is True
        assert check is False
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr(check_quality.subprocess, 'run', fake_run)

    rc = check_quality.run_quality_gate(tmp_path, ['src/feature.py'])

    assert rc == 0
    assert calls == [
        ['uv', 'run', 'ruff', 'check', '--fix', '--', 'src/feature.py'],
        ['uv', 'run', 'ruff', 'format', '--', 'src/feature.py'],
        ['uv', 'run', 'python', '-m', 'pytest'],
    ]


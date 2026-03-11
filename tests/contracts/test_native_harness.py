from __future__ import annotations

import subprocess
from pathlib import Path

from tools.shell_utils import resolve_powershell_executable

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_build_native_harness_creates_executable() -> None:
    build_path = PROJECT_ROOT / 'build' / 'native_harness.exe'
    if build_path.exists():
        build_path.unlink()

    script_path = PROJECT_ROOT / 'scripts' / 'build-native.ps1'
    assert script_path.exists()

    result = subprocess.run(
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

    assert result.returncode == 0, result.stdout + result.stderr
    assert build_path.exists()

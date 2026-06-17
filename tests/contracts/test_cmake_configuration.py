from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_default_cmake_configuration_does_not_require_grpc_toolchain(
    tmp_path: Path,
) -> None:
    cmake = shutil.which('cmake')
    if cmake is None:
        pytest.skip('CMake not available')

    build_dir = tmp_path / 'build'
    result = subprocess.run(
        [
            cmake,
            '-S',
            str(PROJECT_ROOT),
            '-B',
            str(build_dir),
            '-G',
            'Unix Makefiles',
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr

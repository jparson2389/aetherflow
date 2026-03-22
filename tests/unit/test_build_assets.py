from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools import build_assets


def test_compile_proto_assets_runs_protoc_and_creates_package_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    proto_dir = tmp_path / 'proto'
    proto_dir.mkdir()
    capture_proto = proto_dir / 'capture.proto'
    capture_proto.write_text('syntax = "proto3";\n', encoding='utf-8')

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

    monkeypatch.setattr(build_assets.subprocess, 'run', fake_run)

    build_assets.compile_proto_assets(tmp_path)

    out_dir = tmp_path / 'src' / 'aetherflow' / 'proto'
    assert (out_dir / '__init__.py').read_text(encoding='utf-8') == (
        '"""Generated protobuf and gRPC modules."""\n'
    )
    assert calls == [
        [
            'uv',
            'run',
            'python',
            '-m',
            'grpc_tools.protoc',
            f'-I{proto_dir}',
            f'--python_out={out_dir}',
            f'--grpc_python_out={out_dir}',
            str(capture_proto),
        ]
    ]


def test_compile_ui_assets_runs_pyside6_uic_for_each_ui_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ui_dir = tmp_path / 'assets' / 'ui'
    ui_dir.mkdir(parents=True)
    main_window = ui_dir / 'main_window.ui'
    main_window.write_text('<ui/>', encoding='utf-8')

    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        assert cwd == tmp_path
        assert capture_output is True
        assert text is True
        assert check is False
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr(build_assets.subprocess, 'run', fake_run)

    build_assets.compile_ui_assets(tmp_path)

    assert calls == [
        [
            'uv',
            'run',
            'pyside6-uic',
            str(main_window),
            '-o',
            str(tmp_path / 'src' / 'aetherflow' / 'ui_main_window.py'),
        ]
    ]

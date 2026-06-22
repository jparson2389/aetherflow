from __future__ import annotations

import os
import selectors
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from aetherflow.core.ipc import CaptureControlClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _prepend_env_path(env: dict[str, str], key: str, value: Path) -> None:
    existing = env.get(key)
    env[key] = str(value) if not existing else f'{value}{os.pathsep}{existing}'


def _native_build_env() -> dict[str, str] | None:
    env = os.environ.copy()
    deps_root_raw = env.get('AETHERFLOW_NATIVE_DEPS_ROOT')
    if deps_root_raw:
        deps_root = Path(deps_root_raw)
        _prepend_env_path(env, 'PATH', deps_root / 'usr' / 'bin')
        _prepend_env_path(
            env,
            'LD_LIBRARY_PATH',
            deps_root / 'usr' / 'lib' / 'x86_64-linux-gnu',
        )
        _prepend_env_path(
            env,
            'PKG_CONFIG_PATH',
            deps_root / 'usr' / 'lib' / 'x86_64-linux-gnu' / 'pkgconfig',
        )
        _prepend_env_path(
            env,
            'CMAKE_LIBRARY_PATH',
            deps_root / 'usr' / 'lib' / 'x86_64-linux-gnu',
        )
        _prepend_env_path(env, 'CMAKE_INCLUDE_PATH', deps_root / 'usr' / 'include')

    path = env.get('PATH')
    if (
        shutil.which('cmake', path=path) is None
        or shutil.which('protoc', path=path) is None
        or shutil.which('grpc_cpp_plugin', path=path) is None
    ):
        return None
    return env


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _wait_for_ready(process: subprocess.Popen[str]) -> None:
    assert process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stderr, selectors.EVENT_READ)
    deadline = time.monotonic() + 10.0
    lines: list[str] = []

    while time.monotonic() < deadline:
        if process.poll() is not None:
            remaining = process.stderr.read()
            if remaining:
                lines.append(remaining)
            raise AssertionError('native server exited early:\n' + ''.join(lines))

        events = selector.select(timeout=0.1)
        for key, _event in events:
            line = key.fileobj.readline()
            if line:
                lines.append(line)
                if line.startswith('AETHERFLOW_CAPTURE_CONTROL_LISTENING '):
                    return

    raise AssertionError('native server did not become ready:\n' + ''.join(lines))


def test_python_client_talks_to_native_capture_control_grpc_service(
    tmp_path: Path,
) -> None:
    """Build and exercise the native host CaptureControl gRPC endpoint."""
    if sys.platform == 'win32':
        pytest.skip('Uses POSIX /bin/true launch spec in the integration test')

    env = _native_build_env()
    if env is None:
        pytest.skip('Native gRPC build toolchain is not available')

    launcher = Path('/bin/true')
    if not launcher.exists():
        pytest.skip('/bin/true is not available for native launch spec')

    build_dir = tmp_path / 'native-build'
    configure = subprocess.run(
        [
            'cmake',
            '-S',
            str(PROJECT_ROOT),
            '-B',
            str(build_dir),
            '-DAETHERFLOW_BUILD_GRPC_SERVICE=ON',
        ],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert configure.returncode == 0, configure.stdout + configure.stderr

    build = subprocess.run(
        [
            'cmake',
            '--build',
            str(build_dir),
            '--target',
            'aetherflow_capture_control_server',
            '-j2',
        ],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stdout + build.stderr

    server_binary = build_dir / 'aetherflow_capture_control_server'
    port = _free_tcp_port()
    address = f'127.0.0.1:{port}'
    process = subprocess.Popen(
        [
            str(server_binary),
            '--listen',
            address,
            '--launch-spec',
            f'opencv-capture={launcher}',
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        _wait_for_ready(process)
        client = CaptureControlClient.connect(address)

        status = client.start_capture(
            capture_plugin_id='opencv-capture',
            device_id='camera-0',
            width=640,
            height=480,
            target_fps=60,
            pixel_format='BGR24',
            stride_bytes=1920,
            timeout_ms=500,
        )
        log_status = client.forward_worker_log(
            worker_id='opencv-capture',
            level='INFO',
            message='native endpoint reached',
            timestamp_ns=1,
        )
        diagnostics = client.export_diagnostics(
            include_sections=['workers'],
            include_recent_logs=True,
        )

        assert status.ok is True
        assert status.runtime_state == 'RUNNING'
        assert log_status.ok is True
        assert diagnostics.artifact_path == 'aetherflow-diagnostics.zip'
        assert 'worker_logs=1' in diagnostics.summary
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

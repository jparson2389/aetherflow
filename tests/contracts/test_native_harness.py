from __future__ import annotations

import json
import shutil
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


def test_native_supervisor_factory_exposes_host_owned_state_machine(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'supervisor_contract.cpp'
    test_binary = tmp_path / 'supervisor_contract'
    test_source.write_text(
        """
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::plugins::RuntimeState;
    using aetherflow::supervisor::CreateWorkerSupervisor;
    using aetherflow::supervisor::ExitStatus;
    using aetherflow::supervisor::kInvalidUnitId;

    std::unique_ptr<aetherflow::supervisor::IWorkerSupervisor> supervisor =
        CreateWorkerSupervisor(1U, std::chrono::seconds{60});

    if (supervisor->StartUnit("missing-launcher", "", "") != kInvalidUnitId) {
        return 1;
    }

    const auto crashing_unit = supervisor->StartUnit("vision-worker", "/bin/true", "");
    const auto unrelated_unit = supervisor->StartUnit("input-worker", "/bin/true", "");
    if (crashing_unit == kInvalidUnitId || unrelated_unit == kInvalidUnitId) {
        return 2;
    }

    supervisor->RecordCrash(crashing_unit, ExitStatus{1, true});
    if (supervisor->GetState(crashing_unit) != RuntimeState::kRecovering) {
        return 3;
    }
    if (supervisor->GetState(unrelated_unit) != RuntimeState::kRunning) {
        return 4;
    }

    supervisor->RecordCrash(crashing_unit, ExitStatus{1, true});
    const auto snapshot = supervisor->GetSnapshot(crashing_unit);
    if (snapshot.state != RuntimeState::kFailed) {
        return 5;
    }
    if (snapshot.restart_count != 2U || snapshot.restarts_in_window != 2U) {
        return 6;
    }
    if (supervisor->GetState(unrelated_unit) != RuntimeState::kRunning) {
        return 7;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_supervisor_rejects_missing_posix_launcher_synchronously(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'supervisor_missing_launcher_contract.cpp'
    test_binary = tmp_path / 'supervisor_missing_launcher_contract'
    test_source.write_text(
        """
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::supervisor::CreateWorkerSupervisor;
    using aetherflow::supervisor::kInvalidUnitId;

    std::unique_ptr<aetherflow::supervisor::IWorkerSupervisor> supervisor =
        CreateWorkerSupervisor(2U, std::chrono::seconds{60});

    const auto unit_id = supervisor->StartUnit(
        "missing-worker",
        "/tmp/aetherflow-definitely-missing-launcher",
        "--flag value"
    );
    if (unit_id != kInvalidUnitId) {
        return 1;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_supervisor_degrades_only_direct_dependents(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'supervisor_dependency_contract.cpp'
    test_binary = tmp_path / 'supervisor_dependency_contract'
    test_source.write_text(
        """
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::plugins::RuntimeState;
    using aetherflow::supervisor::CreateWorkerSupervisor;
    using aetherflow::supervisor::ExitStatus;
    using aetherflow::supervisor::kInvalidUnitId;

    std::unique_ptr<aetherflow::supervisor::IWorkerSupervisor> supervisor =
        CreateWorkerSupervisor(3U, std::chrono::seconds{60});

    const auto capture_plugin = supervisor->StartUnit("capture-plugin", "/bin/true", "");
    const auto capture_surface = supervisor->StartUnit("capture-surface", "/bin/true", "");
    const auto input_plugin = supervisor->StartUnit("input-plugin", "/bin/true", "");
    if (
        capture_plugin == kInvalidUnitId ||
        capture_surface == kInvalidUnitId ||
        input_plugin == kInvalidUnitId
    ) {
        return 1;
    }

    supervisor->RegisterDependency(capture_surface, capture_plugin);

    supervisor->RecordCrash(capture_plugin, ExitStatus{1, true});

    if (supervisor->GetState(capture_plugin) != RuntimeState::kRecovering) {
        return 2;
    }
    if (supervisor->GetState(capture_surface) != RuntimeState::kDegraded) {
        return 3;
    }
    if (supervisor->GetState(input_plugin) != RuntimeState::kRunning) {
        return 4;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_supervisor_restarts_only_target_unit(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'supervisor_restart_contract.cpp'
    test_binary = tmp_path / 'supervisor_restart_contract'
    test_source.write_text(
        """
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::plugins::RuntimeState;
    using aetherflow::supervisor::CreateWorkerSupervisor;
    using aetherflow::supervisor::ExitStatus;
    using aetherflow::supervisor::kInvalidUnitId;

    std::unique_ptr<aetherflow::supervisor::IWorkerSupervisor> supervisor =
        CreateWorkerSupervisor(2U, std::chrono::seconds{60});

    const auto capture_plugin = supervisor->StartUnit("capture-plugin", "/bin/true", "");
    const auto input_plugin = supervisor->StartUnit("input-plugin", "/bin/true", "");
    if (capture_plugin == kInvalidUnitId || input_plugin == kInvalidUnitId) {
        return 1;
    }

    supervisor->RecordCrash(capture_plugin, ExitStatus{1, true});
    if (!supervisor->RestartUnit(capture_plugin)) {
        return 2;
    }
    if (supervisor->GetState(capture_plugin) != RuntimeState::kRunning) {
        return 3;
    }
    if (supervisor->GetState(input_plugin) != RuntimeState::kRunning) {
        return 4;
    }

    supervisor->RecordCrash(capture_plugin, ExitStatus{1, true});
    supervisor->RecordCrash(capture_plugin, ExitStatus{1, true});
    if (supervisor->RestartUnit(capture_plugin)) {
        return 5;
    }
    if (supervisor->GetState(capture_plugin) != RuntimeState::kFailed) {
        return 6;
    }
    if (supervisor->GetState(input_plugin) != RuntimeState::kRunning) {
        return 7;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_supervisor_exposes_authoritative_runtime_snapshots(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'supervisor_snapshots_contract.cpp'
    test_binary = tmp_path / 'supervisor_snapshots_contract'
    test_source.write_text(
        """
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::plugins::RuntimeState;
    using aetherflow::supervisor::CreateWorkerSupervisor;
    using aetherflow::supervisor::ExitStatus;
    using aetherflow::supervisor::kInvalidUnitId;

    std::unique_ptr<aetherflow::supervisor::IWorkerSupervisor> supervisor =
        CreateWorkerSupervisor(2U, std::chrono::seconds{60});

    const auto capture_plugin = supervisor->StartUnit("capture-plugin", "/bin/true", "");
    const auto input_plugin = supervisor->StartUnit("input-plugin", "/bin/true", "");
    if (capture_plugin == kInvalidUnitId || input_plugin == kInvalidUnitId) {
        return 1;
    }

    supervisor->RecordCrash(capture_plugin, ExitStatus{1, true});

    const auto snapshots = supervisor->GetSnapshots();
    if (snapshots.size() != 2U) {
        return 2;
    }

    bool saw_capture_recovering = false;
    bool saw_input_running = false;
    for (const auto& snapshot : snapshots) {
        if (snapshot.id == capture_plugin && snapshot.state == RuntimeState::kRecovering) {
            saw_capture_recovering = true;
        }
        if (snapshot.id == input_plugin && snapshot.state == RuntimeState::kRunning) {
            saw_input_running = true;
        }
    }

    if (!saw_capture_recovering || !saw_input_running) {
        return 3;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_endpoint_starts_supervised_capture(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_contract.cpp'
    test_binary = tmp_path / 'capture_control_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::CaptureMode;
    using aetherflow::capture::CaptureStartRequest;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(2U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);
    endpoint.RegisterLaunchSpec("opencv-capture", "/bin/true", "");

    const auto status = endpoint.StartCapture(CaptureStartRequest{
        "opencv-capture",
        "camera-0",
        CaptureMode{1920U, 1080U, 120U, "BGR24", 5760U},
        500U,
    });

    if (!status.ok) {
        return 1;
    }
    if (status.runtime_state != "RUNNING") {
        return 2;
    }
    if (endpoint.GetUnitId("opencv-capture") == 0U) {
        return 3;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_endpoint_stops_supervised_capture(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_stop_contract.cpp'
    test_binary = tmp_path / 'capture_control_stop_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::CaptureMode;
    using aetherflow::capture::CaptureStartRequest;
    using aetherflow::capture::CaptureStopRequest;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(2U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);
    endpoint.RegisterLaunchSpec("opencv-capture", "/bin/sleep", "10");

    const auto start_status = endpoint.StartCapture(CaptureStartRequest{
        "opencv-capture",
        "camera-0",
        CaptureMode{1920U, 1080U, 120U, "BGR24", 5760U},
        500U,
    });
    if (!start_status.ok) {
        return 1;
    }

    const auto stop_status = endpoint.StopCapture(CaptureStopRequest{
        "opencv-capture",
        "camera-0",
        "user-request",
    });

    if (!stop_status.ok) {
        return 2;
    }
    if (stop_status.runtime_state != "FAILED") {
        return 3;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_endpoint_records_worker_heartbeat(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_heartbeat_contract.cpp'
    test_binary = tmp_path / 'capture_control_heartbeat_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::CaptureMode;
    using aetherflow::capture::CaptureStartRequest;
    using aetherflow::capture::WorkerHeartbeat;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(2U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);
    endpoint.RegisterLaunchSpec("vision-worker", "/bin/true", "");
    const auto start_status = endpoint.StartCapture(CaptureStartRequest{
        "vision-worker",
        "camera-0",
        CaptureMode{640U, 480U, 60U, "BGR24", 1920U},
        500U,
    });
    if (!start_status.ok) {
        return 1;
    }

    const auto heartbeat_status = endpoint.ReportHeartbeat(WorkerHeartbeat{
        "vision-worker",
        "RUNNING",
        0U,
        123456789ULL,
    });

    if (!heartbeat_status.ok) {
        return 2;
    }
    if (heartbeat_status.runtime_state != "RUNNING") {
        return 3;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_endpoint_records_worker_log(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_log_contract.cpp'
    test_binary = tmp_path / 'capture_control_log_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::WorkerLog;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(2U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);

    const auto status = endpoint.ForwardWorkerLog(WorkerLog{
        "vision-worker",
        "INFO",
        "frame ready",
        123456789ULL,
    });

    if (!status.ok) {
        return 1;
    }
    if (endpoint.GetWorkerLogs().size() != 1U) {
        return 2;
    }
    if (endpoint.GetWorkerLogs()[0].message != "frame ready") {
        return 3;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_endpoint_records_plugin_load_result(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_plugin_result_contract.cpp'
    test_binary = tmp_path / 'capture_control_plugin_result_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::PluginLoadResult;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(2U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);

    const auto status = endpoint.ReportPluginLoadResult(PluginLoadResult{
        "capture-plugin",
        false,
        "FAILED",
        "signature-denied",
        "signature failed",
    });

    if (!status.ok) {
        return 1;
    }
    if (endpoint.GetPluginLoadResults().size() != 1U) {
        return 2;
    }
    if (endpoint.GetPluginLoadResults()[0].error_code != "signature-denied") {
        return 3;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_endpoint_exports_diagnostics_summary(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_diagnostics_contract.cpp'
    test_binary = tmp_path / 'capture_control_diagnostics_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::DiagnosticsExportRequest;
    using aetherflow::capture::WorkerLog;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(2U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);
    endpoint.ForwardWorkerLog(WorkerLog{
        "vision-worker",
        "INFO",
        "frame ready",
        123456789ULL,
    });

    const auto response = endpoint.ExportDiagnostics(DiagnosticsExportRequest{
        {"workers", "plugins"},
        true,
    });

    if (response.artifact_path.empty()) {
        return 1;
    }
    if (response.summary.find("worker_logs=1") == std::string::npos) {
        return 2;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_endpoint_wires_missed_heartbeats(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_missed_heartbeat_contract.cpp'
    test_binary = tmp_path / 'capture_control_missed_heartbeat_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::CaptureMode;
    using aetherflow::capture::CaptureStartRequest;
    using aetherflow::capture::WorkerHeartbeat;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(2U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);
    endpoint.RegisterLaunchSpec("vision-worker", "/bin/true", "");
    const auto start_status = endpoint.StartCapture(CaptureStartRequest{
        "vision-worker",
        "camera-0",
        CaptureMode{640U, 480U, 60U, "BGR24", 1920U},
        500U,
    });
    if (!start_status.ok) {
        return 1;
    }

    // A worker reporting two missed heartbeats must drive the host
    // missed-heartbeat escalation path, not just echo RUNNING.
    const auto degraded_status = endpoint.ReportHeartbeat(WorkerHeartbeat{
        "vision-worker",
        "DEGRADED",
        2U,
        123456789ULL,
    });
    if (!degraded_status.ok) {
        return 2;
    }
    if (degraded_status.runtime_state != "DEGRADED") {
        return 3;
    }

    // A clean heartbeat (missed_heartbeats == 0) recovers the unit to RUNNING.
    const auto recovered_status = endpoint.ReportHeartbeat(WorkerHeartbeat{
        "vision-worker",
        "RUNNING",
        0U,
        123456790ULL,
    });
    if (recovered_status.runtime_state != "RUNNING") {
        return 4;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_endpoint_populates_retry_budget(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_retry_budget_contract.cpp'
    test_binary = tmp_path / 'capture_control_retry_budget_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::CaptureMode;
    using aetherflow::capture::CaptureStartRequest;
    using aetherflow::capture::WorkerHeartbeat;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(3U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);
    endpoint.RegisterLaunchSpec("vision-worker", "/bin/true", "");
    const auto start_status = endpoint.StartCapture(CaptureStartRequest{
        "vision-worker",
        "camera-0",
        CaptureMode{640U, 480U, 60U, "BGR24", 1920U},
        500U,
    });
    if (!start_status.ok) {
        return 1;
    }
    // Fresh unit: full budget of 3 restarts remaining.
    if (start_status.retry_budget_remaining != 3U) {
        return 2;
    }

    // Three missed heartbeats consume one restart-budget attempt.
    const auto status = endpoint.ReportHeartbeat(WorkerHeartbeat{
        "vision-worker",
        "RECOVERING",
        3U,
        123456789ULL,
    });
    if (!status.ok) {
        return 3;
    }
    if (status.runtime_state != "RECOVERING") {
        return 4;
    }
    // One attempt consumed: 3 - 1 = 2 remaining.
    if (status.retry_budget_remaining != 2U) {
        return 5;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_heartbeat_uses_worker_alias(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_worker_alias_contract.cpp'
    test_binary = tmp_path / 'capture_control_worker_alias_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::CaptureMode;
    using aetherflow::capture::CaptureStartRequest;
    using aetherflow::capture::WorkerHeartbeat;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(3U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);
    endpoint.RegisterLaunchSpec(
        "opencv-capture",
        "/bin/true",
        "",
        "vision-worker");

    const auto start_status = endpoint.StartCapture(CaptureStartRequest{
        "opencv-capture",
        "camera-0",
        CaptureMode{640U, 480U, 60U, "BGR24", 1920U},
        500U,
    });
    if (!start_status.ok) {
        return 1;
    }

    const auto heartbeat_status = endpoint.ReportHeartbeat(WorkerHeartbeat{
        "vision-worker",
        "RUNNING",
        0U,
        123456789ULL,
    });
    if (!heartbeat_status.ok) {
        return 2;
    }
    if (heartbeat_status.runtime_state != "RUNNING") {
        return 3;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_separates_runtime_and_worker_lookup_domains(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_lookup_domains_contract.cpp'
    test_binary = tmp_path / 'capture_control_lookup_domains_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::CaptureMode;
    using aetherflow::capture::CaptureStartRequest;
    using aetherflow::capture::WorkerHeartbeat;
    using aetherflow::plugins::RuntimeState;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(3U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);
    endpoint.RegisterLaunchSpec("camera-runtime", "/bin/true", "", "shared-id");
    endpoint.RegisterLaunchSpec("shared-id", "/bin/true", "", "other-worker");

    if (!endpoint.StartCapture(CaptureStartRequest{
            "camera-runtime",
            "camera-0",
            CaptureMode{640U, 480U, 60U, "BGR24", 1920U},
            500U,
        }).ok) {
        return 1;
    }
    if (!endpoint.StartCapture(CaptureStartRequest{
            "shared-id",
            "camera-1",
            CaptureMode{640U, 480U, 60U, "BGR24", 1920U},
            500U,
        }).ok) {
        return 2;
    }

    const auto status = endpoint.ReportHeartbeat(WorkerHeartbeat{
        "shared-id",
        "RECOVERING",
        3U,
        123456789ULL,
    });
    if (!status.ok || status.runtime_state != "RECOVERING") {
        return 3;
    }

    const auto runtime_unit = endpoint.GetUnitId("shared-id");
    if (supervisor->GetState(runtime_unit) != RuntimeState::kRunning) {
        return 4;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_bounds_worker_log_buffer(tmp_path: Path) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_log_buffer_contract.cpp'
    test_binary = tmp_path / 'capture_control_log_buffer_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>
#include <string>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::WorkerLog;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(3U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);

    for (std::uint32_t index = 0; index < 1030U; ++index) {
        endpoint.ForwardWorkerLog(WorkerLog{
            "vision-worker",
            "INFO",
            "log-" + std::to_string(index),
            index,
        });
    }

    const auto logs = endpoint.GetWorkerLogs();
    if (logs.size() != 1024U) {
        return 1;
    }
    if (logs.front().message != "log-6") {
        return 2;
    }
    if (logs.back().message != "log-1029") {
        return 3;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_heartbeat_replay_guards_recovering_state(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_replay_guard_contract.cpp'
    test_binary = tmp_path / 'capture_control_replay_guard_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::CaptureMode;
    using aetherflow::capture::CaptureStartRequest;
    using aetherflow::capture::WorkerHeartbeat;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(2U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);
    endpoint.RegisterLaunchSpec("vision-worker", "/bin/true", "");
    const auto start_status = endpoint.StartCapture(CaptureStartRequest{
        "vision-worker",
        "camera-0",
        CaptureMode{640U, 480U, 60U, "BGR24", 1920U},
        500U,
    });
    if (!start_status.ok || start_status.retry_budget_remaining != 2U) {
        return 1;
    }

    const auto recovering_status = endpoint.ReportHeartbeat(WorkerHeartbeat{
        "vision-worker",
        "RECOVERING",
        3U,
        100000000ULL,
    });
    if (!recovering_status.ok) {
        return 2;
    }
    if (recovering_status.runtime_state != "RECOVERING") {
        return 3;
    }
    if (recovering_status.retry_budget_remaining != 1U) {
        return 4;
    }

    const auto stale4_status = endpoint.ReportHeartbeat(WorkerHeartbeat{
        "vision-worker",
        "RECOVERING",
        4U,
        200000000ULL,
    });
    if (!stale4_status.ok || stale4_status.runtime_state != "RECOVERING") {
        return 5;
    }
    if (stale4_status.retry_budget_remaining != 1U) {
        return 6;
    }

    const auto stale5_status = endpoint.ReportHeartbeat(WorkerHeartbeat{
        "vision-worker",
        "RECOVERING",
        5U,
        300000000ULL,
    });
    if (!stale5_status.ok || stale5_status.runtime_state != "RECOVERING") {
        return 7;
    }
    if (stale5_status.retry_budget_remaining != 1U) {
        return 8;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_stop_unit_terminates_failed_unit_process(tmp_path: Path) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'failed_unit_stop_contract.cpp'
    test_binary = tmp_path / 'failed_unit_stop_contract'
    test_source.write_text(
        """
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::plugins::RuntimeState;
    using aetherflow::supervisor::CreateWorkerSupervisor;
    using aetherflow::supervisor::kInvalidUnitId;

    auto supervisor = CreateWorkerSupervisor(0U, std::chrono::seconds{60});
    const auto unit = supervisor->StartUnit("hung-worker", "/bin/sleep", "30");
    if (unit == kInvalidUnitId) {
        return 1;
    }

    supervisor->RecordMissedHeartbeat(unit);
    supervisor->RecordMissedHeartbeat(unit);
    supervisor->RecordMissedHeartbeat(unit);
    if (supervisor->GetState(unit) != RuntimeState::kFailed) {
        return 2;
    }
    if (!supervisor->GetSnapshot(unit).process_alive) {
        return 3;
    }

    supervisor->StopUnit(unit, std::chrono::milliseconds{250});
    if (supervisor->GetSnapshot(unit).process_alive) {
        return 4;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
            '-pthread',
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_watchdog_detects_exited_process_and_transitions(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'watchdog_contract.cpp'
    test_binary = tmp_path / 'watchdog_contract'
    test_source.write_text(
        """
#include "supervisor.hpp"

#include <chrono>
#include <ctime>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::plugins::RuntimeState;
    using aetherflow::supervisor::CreateWorkerSupervisor;
    using aetherflow::supervisor::kInvalidUnitId;
    using aetherflow::supervisor::WorkerWatchdog;

    auto supervisor = CreateWorkerSupervisor(3U, std::chrono::seconds{60});

    // /bin/true exits immediately; /bin/sleep stays alive.
    const auto dying = supervisor->StartUnit("dying-worker", "/bin/true", "");
    const auto living = supervisor->StartUnit("living-worker", "/bin/sleep", "30");
    if (dying == kInvalidUnitId || living == kInvalidUnitId) {
        return 1;
    }

    // Give the short-lived child time to exit and be reaped.
    struct timespec ts{0, 200'000'000};  // 200 ms
    ::nanosleep(&ts, nullptr);

    WorkerWatchdog watchdog(*supervisor);
    const std::uint32_t transitioned = watchdog.PollOnce();
    if (transitioned != 1U) {
        return 2;
    }
    // Dead process -> authoritative crash -> recovering (within budget).
    if (supervisor->GetState(dying) != RuntimeState::kRecovering) {
        return 3;
    }
    // Live process is untouched.
    if (supervisor->GetState(living) != RuntimeState::kRunning) {
        return 4;
    }

    // Idempotent: a second sweep does not re-crash the already-transitioned unit.
    if (watchdog.PollOnce() != 0U) {
        return 5;
    }

    supervisor->StopUnit(living, std::chrono::milliseconds{250});

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
            '-pthread',
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_supervisor_rejects_threaded_in_process_units(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'process_isolation_contract.cpp'
    test_binary = tmp_path / 'process_isolation_contract'
    test_source.write_text(
        """
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::supervisor::CreateWorkerSupervisor;
    using aetherflow::supervisor::kInvalidUnitId;

    auto supervisor = CreateWorkerSupervisor(3U, std::chrono::seconds{60});

    // A launcher-less unit is an in-process/thread-only target: rejected so the
    // host only ever supervises isolated OS processes.
    if (supervisor->StartUnit("thread-only", "", "") != kInvalidUnitId) {
        return 1;
    }
    if (supervisor->StartUnit("thread-only-args", "", "--inproc") != kInvalidUnitId) {
        return 2;
    }
    // A real process launcher is accepted.
    if (supervisor->StartUnit("real-process", "/bin/true", "") == kInvalidUnitId) {
        return 3;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
            '-pthread',
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr


def test_native_capture_control_registers_dependency_from_manifest(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        pytest.skip('C++ compiler not available')

    test_source = tmp_path / 'capture_control_dependency_contract.cpp'
    test_binary = tmp_path / 'capture_control_dependency_contract'
    test_source.write_text(
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <memory>

int main() {
#ifdef _WIN32
    return 0;
#else
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::CaptureMode;
    using aetherflow::capture::CaptureStartRequest;
    using aetherflow::plugins::RuntimeState;
    using aetherflow::supervisor::CreateWorkerSupervisor;

    auto supervisor = CreateWorkerSupervisor(3U, std::chrono::seconds{60});
    CaptureControlEndpoint endpoint(*supervisor);

    // Static unit manifest: the capture surface depends on the capture plugin;
    // the input plugin (shell-equivalent root) is unrelated.
    endpoint.RegisterLaunchSpec("capture-plugin", "/bin/true", "");
    endpoint.RegisterLaunchSpec("capture-surface", "/bin/true", "");
    endpoint.RegisterLaunchSpec("input-plugin", "/bin/true", "");
    endpoint.RegisterDependencySpec("capture-surface", "capture-plugin");

    const CaptureMode mode{640U, 480U, 60U, "BGR24", 1920U};
    if (!endpoint.StartCapture(CaptureStartRequest{
            "capture-plugin", "camera-0", mode, 500U}).ok) {
        return 1;
    }
    if (!endpoint.StartCapture(CaptureStartRequest{
            "capture-surface", "camera-0", mode, 500U}).ok) {
        return 2;
    }
    if (!endpoint.StartCapture(CaptureStartRequest{
            "input-plugin", "device-0", mode, 500U}).ok) {
        return 3;
    }

    // Manifest dependency wiring happens at unit start; declaring it returns true.
    if (!endpoint.ApplyDependencyManifest()) {
        return 4;
    }

    const auto plugin_id = endpoint.GetUnitId("capture-plugin");
    const auto surface_id = endpoint.GetUnitId("capture-surface");
    const auto input_id = endpoint.GetUnitId("input-plugin");

    supervisor->RecordCrash(plugin_id, aetherflow::supervisor::ExitStatus{1, true});

    // Failed plugin degrades ONLY its direct dependent.
    if (supervisor->GetState(plugin_id) != RuntimeState::kRecovering) {
        return 5;
    }
    if (supervisor->GetState(surface_id) != RuntimeState::kDegraded) {
        return 6;
    }
    // Unrelated root stays RUNNING.
    if (supervisor->GetState(input_id) != RuntimeState::kRunning) {
        return 7;
    }

    return 0;
#endif
}
""",
        encoding='utf-8',
    )

    compile_result = subprocess.run(
        [
            compiler,
            '-std=c++20',
            '-I',
            str(PROJECT_ROOT / 'include'),
            str(PROJECT_ROOT / 'host' / 'supervisor.cpp'),
            str(PROJECT_ROOT / 'host' / 'capture_control.cpp'),
            str(test_source),
            '-o',
            str(test_binary),
            '-pthread',
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert compile_result.returncode == 0, compile_result.stdout + compile_result.stderr

    run_result = subprocess.run(
        [str(test_binary)],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run_result.returncode == 0, run_result.stdout + run_result.stderr

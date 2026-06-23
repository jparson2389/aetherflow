"""Contract tests for the canonical C++/Python boundary native harness.

The native harness is the single source of truth for boundary/token compliance.
These tests build it (and the host libraries the behavioral checks link) through
the project's CMake build system and run on the host platform, gated only on C++
toolchain availability — never on the host OS — so the authoritative validator
and the behavioral coverage contribute signal on Linux CI and Windows alike.

Behavioral supervisor/capture-control tests compile their snippets against the
shared CMake library targets rather than re-listing host sources in per-test
compiler command lines, so the boundary is declared in exactly one place.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from tools.native_build import NativeBuild

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_RUNTIME_STATES = [
    'RUNNING',
    'DEGRADED',
    'RECOVERING',
    'FAILED',
    'LOCKED',
    'GRACE',
]

# Shared CMake library targets, in dependency-first link order. Host sources are
# declared once in CMakeLists.txt; behavioral tests link these archives.
SUPERVISOR_LIB = ('aetherflow_supervisor',)
CAPTURE_CONTROL_LIB = ('aetherflow_capture_control', 'aetherflow_supervisor')

# A public supervisor-contract token the canonical validator requires. Named
# here only so the drift test can remove it from a throwaway copy of the header;
# the authoritative required-token set lives in host/native_harness.cpp.
SUPERVISOR_CONTRACT_SYMBOL = 'RestartUnit'


@pytest.fixture(scope='session')
def native_harness(native_build: NativeBuild) -> Path:
    """Build the canonical native harness once via the shared CMake build."""
    return native_build.build_target('native_harness')


@pytest.fixture(scope='session')
def native_contract_build(native_build: NativeBuild) -> NativeBuild:
    """Provide the shared build, skipping when no snippet compiler is present."""
    from tools.native_build import find_gcc_style_compiler

    if find_gcc_style_compiler() is None:
        pytest.skip('C++ compiler not available')
    return native_build


def _run_harness(
    binary: Path, repo_root: Path, output_path: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(binary),
            '--repo-root',
            str(repo_root),
            '--output',
            str(output_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _materialize_contract_tree(dest: Path) -> None:
    """Copy the public contract inputs into an isolated repo-shaped tree."""
    (dest / 'src').mkdir(parents=True)
    (dest / 'include').mkdir()
    (dest / 'proto').mkdir()
    for relative in (
        'include/plugin_system.hpp',
        'include/supervisor.hpp',
        'proto/capture.proto',
    ):
        (dest / relative).write_text(
            (PROJECT_ROOT / relative).read_text(encoding='utf-8'),
            encoding='utf-8',
        )


def test_native_harness_reports_real_tree_contract_valid(
    native_harness: Path, tmp_path: Path
) -> None:
    """The canonical validator runs on the host platform and passes the real tree."""
    report_path = tmp_path / 'native_harness_report.json'

    result = _run_harness(native_harness, PROJECT_ROOT, report_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding='utf-8'))

    assert report['status'] == 'ok'
    assert report['header']['signature_scheme'] == 'Authenticode'
    assert report['header']['digest_algorithm'] == 'SHA-256'
    assert report['header']['rsa_key_bits'] == 3072
    assert report['header']['runtime_states'] == EXPECTED_RUNTIME_STATES
    assert report['proto']['service_name'] == 'CaptureControl'
    assert report['proto']['rpc_count'] == 6
    assert report['boundary']['src_native_files'] == []
    assert report['errors'] == []


def test_native_harness_fails_when_supervisor_contract_symbol_removed(
    native_harness: Path, tmp_path: Path
) -> None:
    """Dropping a public supervisor-contract symbol fails the validator report.

    Drift detection: the validator owns the supervisor contract, so a renamed or
    deleted public symbol must surface as a failing report (and therefore fail
    CI), not slip through undetected.
    """
    repo_root = tmp_path / 'repo'
    _materialize_contract_tree(repo_root)

    supervisor_header = repo_root / 'include' / 'supervisor.hpp'
    mutated = supervisor_header.read_text(encoding='utf-8').replace(
        SUPERVISOR_CONTRACT_SYMBOL, 'Relaunch'
    )
    assert SUPERVISOR_CONTRACT_SYMBOL not in mutated, 'mutation did not remove token'
    supervisor_header.write_text(mutated, encoding='utf-8')

    report_path = repo_root / 'native_harness_report.json'
    result = _run_harness(native_harness, repo_root, report_path)

    assert result.returncode != 0
    report = json.loads(report_path.read_text(encoding='utf-8'))
    assert report['status'] == 'failed'
    assert any(SUPERVISOR_CONTRACT_SYMBOL in error for error in report['errors']), (
        report['errors']
    )


def test_native_harness_rejects_cpp_sources_inside_src(
    native_harness: Path, tmp_path: Path
) -> None:
    """A native source file under src/ is a boundary violation the validator fails."""
    repo_root = tmp_path / 'repo'
    _materialize_contract_tree(repo_root)
    (repo_root / 'src' / 'engine.cpp').write_text(
        'int leaked_native = 1;\n', encoding='utf-8'
    )

    report_path = repo_root / 'native_harness_report.json'
    result = _run_harness(native_harness, repo_root, report_path)

    assert result.returncode != 0
    assert 'Native source files are not allowed under src/' in (
        result.stdout + result.stderr
    )
    report = json.loads(report_path.read_text(encoding='utf-8'))
    assert report['status'] == 'failed'
    assert 'src/engine.cpp' in report['boundary']['src_native_files']


def test_native_supervisor_factory_exposes_host_owned_state_machine(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'supervisor_contract',
        SUPERVISOR_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_supervisor_rejects_missing_posix_launcher_synchronously(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'supervisor_missing_launcher_contract',
        SUPERVISOR_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_supervisor_degrades_only_direct_dependents(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'supervisor_dependency_contract',
        SUPERVISOR_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_supervisor_restarts_only_target_unit(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'supervisor_restart_contract',
        SUPERVISOR_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_supervisor_exposes_authoritative_runtime_snapshots(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'supervisor_snapshots_contract',
        SUPERVISOR_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_endpoint_starts_supervised_capture(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_endpoint_stops_supervised_capture(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_stop_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_endpoint_releases_lock_before_stop_unit(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_stop_lock_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
        """
#include "capture_control.hpp"
#include "supervisor.hpp"

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <thread>
#include <vector>

class BlockingSupervisor final : public aetherflow::supervisor::IWorkerSupervisor {
public:
    aetherflow::supervisor::UnitId StartUnit(
        std::string_view,
        std::string_view,
        std::string_view) override {
        return unit_id_;
    }

    bool RegisterDependency(
        aetherflow::supervisor::UnitId,
        aetherflow::supervisor::UnitId) override {
        return true;
    }

    bool RestartUnit(aetherflow::supervisor::UnitId) override {
        return true;
    }

    void StopUnit(
        aetherflow::supervisor::UnitId,
        std::chrono::milliseconds) override {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            stop_entered_ = true;
        }
        cv_.notify_all();
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [this] { return allow_stop_; });
        state_ = aetherflow::supervisor::RuntimeState::kFailed;
    }

    void RecordHeartbeat(aetherflow::supervisor::UnitId) override {}

    void RecordMissedHeartbeat(aetherflow::supervisor::UnitId) override {}

    void RecordCrash(
        aetherflow::supervisor::UnitId,
        aetherflow::supervisor::ExitStatus) override {}

    aetherflow::supervisor::RuntimeState EnforceRestartBudget(
        aetherflow::supervisor::UnitId) override {
        return state_;
    }

    aetherflow::supervisor::UnitSnapshot GetSnapshot(
        aetherflow::supervisor::UnitId id) const override {
        return aetherflow::supervisor::UnitSnapshot{
            id,
            state_,
            0U,
            0U,
            0U,
            aetherflow::supervisor::kDefaultMaxRestarts,
            false,
        };
    }

    std::vector<aetherflow::supervisor::UnitSnapshot> GetSnapshots()
        const override {
        return {GetSnapshot(unit_id_)};
    }

    aetherflow::supervisor::RuntimeState GetState(
        aetherflow::supervisor::UnitId) const override {
        return state_;
    }

    std::uint32_t PollProcessLiveness() override {
        return 0U;
    }

    bool WaitForStopEntered(std::chrono::milliseconds timeout) {
        std::unique_lock<std::mutex> lock(mutex_);
        return cv_.wait_for(lock, timeout, [this] { return stop_entered_; });
    }

    void AllowStop() {
        {
            std::lock_guard<std::mutex> lock(mutex_);
            allow_stop_ = true;
        }
        cv_.notify_all();
    }

private:
    static constexpr aetherflow::supervisor::UnitId unit_id_{1U};
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    bool stop_entered_{false};
    bool allow_stop_{false};
    aetherflow::supervisor::RuntimeState state_{
        aetherflow::supervisor::RuntimeState::kRunning};
};

int main() {
    using aetherflow::capture::CaptureControlEndpoint;
    using aetherflow::capture::CaptureMode;
    using aetherflow::capture::CaptureStartRequest;
    using aetherflow::capture::CaptureStopRequest;
    using aetherflow::capture::WorkerLog;

    BlockingSupervisor supervisor;
    CaptureControlEndpoint endpoint(supervisor);
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

    std::thread stop_thread([&endpoint] {
        endpoint.StopCapture(CaptureStopRequest{
            "opencv-capture",
            "camera-0",
            "user-request",
        });
    });
    if (!supervisor.WaitForStopEntered(std::chrono::seconds{1})) {
        supervisor.AllowStop();
        stop_thread.join();
        return 2;
    }

    std::atomic<bool> log_recorded{false};
    std::thread log_thread([&endpoint, &log_recorded] {
        const auto status = endpoint.ForwardWorkerLog(WorkerLog{
            "worker-0",
            "INFO",
            "still responsive",
            1U,
        });
        log_recorded.store(status.ok);
    });

    const auto deadline =
        std::chrono::steady_clock::now() + std::chrono::milliseconds{250};
    while (!log_recorded.load() && std::chrono::steady_clock::now() < deadline) {
        std::this_thread::sleep_for(std::chrono::milliseconds{5});
    }
    if (!log_recorded.load()) {
        supervisor.AllowStop();
        stop_thread.join();
        log_thread.join();
        return 3;
    }

    supervisor.AllowStop();
    stop_thread.join();
    log_thread.join();
    return 0;
}
""",
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_endpoint_records_worker_heartbeat(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_heartbeat_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_endpoint_records_worker_log(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_log_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_endpoint_records_plugin_load_result(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_plugin_result_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_endpoint_exports_diagnostics_summary(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_diagnostics_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_endpoint_wires_missed_heartbeats(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_missed_heartbeat_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_endpoint_populates_retry_budget(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_retry_budget_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_heartbeat_uses_worker_alias(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_worker_alias_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_separates_runtime_and_worker_lookup_domains(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_lookup_domains_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_bounds_worker_log_buffer(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_log_buffer_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_heartbeat_replay_guards_recovering_state(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_replay_guard_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_stop_unit_terminates_failed_unit_process(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'failed_unit_stop_contract',
        SUPERVISOR_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_watchdog_detects_exited_process_and_transitions(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'watchdog_contract',
        SUPERVISOR_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_supervisor_rejects_threaded_in_process_units(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'process_isolation_contract',
        SUPERVISOR_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_native_capture_control_registers_dependency_from_manifest(
    native_contract_build: NativeBuild,
    tmp_path: Path,
) -> None:
    result = native_contract_build.compile_and_run(
        'capture_control_dependency_contract',
        CAPTURE_CONTROL_LIB,
        tmp_path,
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
    )
    assert result.returncode == 0, result.stdout + result.stderr

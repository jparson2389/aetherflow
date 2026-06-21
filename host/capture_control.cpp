#include "capture_control.hpp"

#include <algorithm>
#include <cstddef>
#include <mutex>
#include <sstream>
#include <string>

namespace aetherflow::capture {

namespace {

// Maximum missed-heartbeat ticks replayed into the supervisor for a single
// client report. Bounds the request-thread loop (a client cannot force an
// arbitrarily long replay) and, combined with breaking on escalation, ensures
// one continuous outage costs at most one restart-budget transition.
constexpr std::uint32_t kMaxMissedHeartbeatReplay = 3U;
constexpr std::size_t kMaxBufferedWorkerLogs = 1024U;
constexpr std::size_t kMaxBufferedPluginLoadResults = 256U;

std::uint32_t RetryBudgetRemaining(const supervisor::UnitSnapshot& snapshot)
{
    // Host-owned budget accounting: remaining attempts are the per-unit
    // ceiling minus the restarts already consumed in the current window.
    // Python consumers must render this value, never recompute it.
    if (snapshot.restarts_in_window >= snapshot.max_restarts) {
        return 0U;
    }
    return snapshot.max_restarts - snapshot.restarts_in_window;
}

std::string RuntimeStateText(supervisor::RuntimeState state)
{
    switch (state) {
    case supervisor::RuntimeState::kRunning:
        return "RUNNING";
    case supervisor::RuntimeState::kDegraded:
        return "DEGRADED";
    case supervisor::RuntimeState::kRecovering:
        return "RECOVERING";
    case supervisor::RuntimeState::kFailed:
        return "FAILED";
    case supervisor::RuntimeState::kLocked:
        return "LOCKED";
    case supervisor::RuntimeState::kGrace:
        return "GRACE";
    }
    return "FAILED";
}

}  // namespace

CaptureControlEndpoint::CaptureControlEndpoint(
    supervisor::IWorkerSupervisor& supervisor)
    : supervisor_(supervisor)
{
}

void CaptureControlEndpoint::RegisterLaunchSpec(
    std::string_view runtime_id,
    std::string_view launcher_path,
    std::string_view args,
    std::string_view worker_id)
{
    std::lock_guard<std::mutex> lock(mutex_);
    launch_specs_[std::string(runtime_id)] = LaunchSpec{
        std::string(launcher_path),
        std::string(args),
        worker_id.empty() ? std::string(runtime_id) : std::string(worker_id),
    };
}

void CaptureControlEndpoint::RegisterDependencySpec(
    std::string_view dependent_runtime_id,
    std::string_view dependency_runtime_id)
{
    std::lock_guard<std::mutex> lock(mutex_);
    dependency_specs_.push_back(DependencySpec{
        std::string(dependent_runtime_id),
        std::string(dependency_runtime_id),
        false,
    });
}

bool CaptureControlEndpoint::ApplyDependencyManifest()
{
    std::lock_guard<std::mutex> lock(mutex_);
    bool all_applied = true;
    for (auto& spec : dependency_specs_) {
        if (spec.applied) {
            continue;
        }
        const auto dependent_it =
            runtime_unit_ids_.find(spec.dependent_runtime_id);
        const auto dependency_it =
            runtime_unit_ids_.find(spec.dependency_runtime_id);
        // Skip edges whose units are not both started yet; a later re-apply
        // (after their StartCapture) will bind them.
        if (dependent_it == runtime_unit_ids_.end() ||
            dependency_it == runtime_unit_ids_.end()) {
            continue;
        }
        if (supervisor_.RegisterDependency(
                dependent_it->second, dependency_it->second)) {
            spec.applied = true;
        } else {
            all_applied = false;
        }
    }
    return all_applied;
}

OperationStatus CaptureControlEndpoint::StartCapture(
    const CaptureStartRequest& request)
{
    std::lock_guard<std::mutex> lock(mutex_);
    const auto spec_it = launch_specs_.find(request.capture_plugin_id);
    if (spec_it == launch_specs_.end()) {
        return OperationStatus{
            false,
            "FAILED",
            "missing launch spec",
            0U,
        };
    }

    // Idempotent duplicate start: if a live unit already backs this runtime id,
    // a retried StartCapture — e.g. one whose deadline fired after the host had
    // already launched the worker — must report the running unit rather than a
    // spurious failure. A failed unit falls through so reload spawns afresh.
    const auto existing_it = runtime_unit_ids_.find(request.capture_plugin_id);
    if (existing_it != runtime_unit_ids_.end()) {
        const supervisor::RuntimeState existing_state =
            supervisor_.GetState(existing_it->second);
        if (existing_state != supervisor::RuntimeState::kFailed) {
            return OperationStatus{
                true,
                RuntimeStateText(existing_state),
                "capture already running",
                RetryBudgetRemaining(
                    supervisor_.GetSnapshot(existing_it->second)),
            };
        }
    }

    const supervisor::UnitId unit_id = supervisor_.StartUnit(
        request.capture_plugin_id,
        spec_it->second.launcher_path,
        spec_it->second.args);
    if (unit_id == supervisor::kInvalidUnitId) {
        return OperationStatus{
            false,
            "FAILED",
            "capture start failed",
            0U,
        };
    }

    const bool replaced =
        runtime_unit_ids_.count(request.capture_plugin_id) > 0;
    runtime_unit_ids_[request.capture_plugin_id] = unit_id;
    worker_unit_ids_[spec_it->second.worker_id] = unit_id;
    // When reloading a runtime whose UnitId changes, reset dependency edges so
    // ApplyDependencyManifest re-registers them against the new UnitId.
    if (replaced) {
        for (auto& spec : dependency_specs_) {
            if (spec.dependent_runtime_id == request.capture_plugin_id ||
                spec.dependency_runtime_id == request.capture_plugin_id) {
                spec.applied = false;
            }
        }
    }
    return OperationStatus{
        true,
        RuntimeStateText(supervisor_.GetState(unit_id)),
        "capture started",
        RetryBudgetRemaining(supervisor_.GetSnapshot(unit_id)),
    };
}

OperationStatus CaptureControlEndpoint::StopCapture(
    const CaptureStopRequest& request)
{
    std::lock_guard<std::mutex> lock(mutex_);
    const auto unit_it = runtime_unit_ids_.find(request.capture_plugin_id);
    if (unit_it == runtime_unit_ids_.end()) {
        return OperationStatus{
            false,
            "FAILED",
            "unknown capture unit",
            0U,
        };
    }

    supervisor_.StopUnit(unit_it->second, std::chrono::milliseconds{250});
    return OperationStatus{
        true,
        RuntimeStateText(supervisor_.GetState(unit_it->second)),
        "capture stopped",
        RetryBudgetRemaining(supervisor_.GetSnapshot(unit_it->second)),
    };
}

OperationStatus CaptureControlEndpoint::ReportHeartbeat(
    const WorkerHeartbeat& request)
{
    std::lock_guard<std::mutex> lock(mutex_);
    const auto unit_it = worker_unit_ids_.find(request.worker_id);
    if (unit_it == worker_unit_ids_.end()) {
        return OperationStatus{
            false,
            "FAILED",
            "unknown worker unit",
            0U,
        };
    }

    // The host supervisor — not the worker's self-report — decides the
    // resulting state. A worker reporting missed ticks drives the native
    // missed-heartbeat escalation path; a clean report (zero missed ticks)
    // records a live heartbeat. The host owns the resulting transition.
    if (request.missed_heartbeats > 0U) {
        const supervisor::UnitSnapshot before =
            supervisor_.GetSnapshot(unit_it->second);
        if (before.state == supervisor::RuntimeState::kRecovering ||
            before.state == supervisor::RuntimeState::kFailed) {
            return OperationStatus{
                true,
                RuntimeStateText(before.state),
                "heartbeat ignored: unit already recovering or failed",
                RetryBudgetRemaining(before),
            };
        }
        // Bound the replay so a large client-supplied count cannot block the
        // request thread, and stop at the first escalation so one outage costs
        // at most one restart-budget transition rather than draining it.
        const std::uint32_t target = std::min(
            request.missed_heartbeats,
            before.missed_heartbeats + kMaxMissedHeartbeatReplay);
        for (std::uint32_t tick = before.missed_heartbeats; tick < target;
             ++tick) {
            supervisor_.RecordMissedHeartbeat(unit_it->second);
            const supervisor::RuntimeState state =
                supervisor_.GetState(unit_it->second);
            if (state == supervisor::RuntimeState::kRecovering ||
                state == supervisor::RuntimeState::kFailed) {
                break;
            }
        }
    } else {
        supervisor_.RecordHeartbeat(unit_it->second);
    }
    return OperationStatus{
        true,
        RuntimeStateText(supervisor_.GetState(unit_it->second)),
        "heartbeat recorded",
        RetryBudgetRemaining(supervisor_.GetSnapshot(unit_it->second)),
    };
}

OperationStatus CaptureControlEndpoint::ForwardWorkerLog(
    const WorkerLog& request)
{
    std::lock_guard<std::mutex> lock(mutex_);
    worker_logs_.push_back(request);
    if (worker_logs_.size() > kMaxBufferedWorkerLogs) {
        worker_logs_.erase(
            worker_logs_.begin(),
            worker_logs_.begin() +
                static_cast<std::ptrdiff_t>(
                    worker_logs_.size() - kMaxBufferedWorkerLogs));
    }
    return OperationStatus{
        true,
        "RUNNING",
        "worker log recorded",
        0U,
    };
}

OperationStatus CaptureControlEndpoint::ReportPluginLoadResult(
    const PluginLoadResult& request)
{
    std::lock_guard<std::mutex> lock(mutex_);
    plugin_load_results_.push_back(request);
    if (plugin_load_results_.size() > kMaxBufferedPluginLoadResults) {
        plugin_load_results_.erase(
            plugin_load_results_.begin(),
            plugin_load_results_.begin() +
                static_cast<std::ptrdiff_t>(
                    plugin_load_results_.size() -
                    kMaxBufferedPluginLoadResults));
    }
    return OperationStatus{
        true,
        request.runtime_state,
        "plugin load result recorded",
        0U,
    };
}

std::vector<WorkerLog> CaptureControlEndpoint::GetWorkerLogs() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return worker_logs_;
}

std::vector<PluginLoadResult> CaptureControlEndpoint::GetPluginLoadResults()
    const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return plugin_load_results_;
}

DiagnosticsExportResponse CaptureControlEndpoint::ExportDiagnostics(
    const DiagnosticsExportRequest& request) const
{
    std::lock_guard<std::mutex> lock(mutex_);
    std::ostringstream summary;
    summary << "sections=" << request.include_sections.size()
            << ";worker_logs=" << worker_logs_.size()
            << ";plugin_load_results=" << plugin_load_results_.size();
    return DiagnosticsExportResponse{
        "aetherflow-diagnostics.zip",
        summary.str(),
    };
}

supervisor::UnitId CaptureControlEndpoint::GetUnitId(
    std::string_view runtime_id) const
{
    std::lock_guard<std::mutex> lock(mutex_);
    const auto unit_it = runtime_unit_ids_.find(std::string(runtime_id));
    if (unit_it == runtime_unit_ids_.end()) {
        return supervisor::kInvalidUnitId;
    }
    return unit_it->second;
}

}  // namespace aetherflow::capture

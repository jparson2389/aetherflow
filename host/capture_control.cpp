#include "capture_control.hpp"

#include <sstream>
#include <string>

namespace aetherflow::capture {

namespace {

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
    std::string_view args)
{
    launch_specs_[std::string(runtime_id)] = LaunchSpec{
        std::string(launcher_path),
        std::string(args),
    };
}

OperationStatus CaptureControlEndpoint::StartCapture(
    const CaptureStartRequest& request)
{
    const auto spec_it = launch_specs_.find(request.capture_plugin_id);
    if (spec_it == launch_specs_.end()) {
        return OperationStatus{
            false,
            "FAILED",
            "missing launch spec",
            0U,
        };
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

    unit_ids_[request.capture_plugin_id] = unit_id;
    return OperationStatus{
        true,
        RuntimeStateText(supervisor_.GetState(unit_id)),
        "capture started",
        0U,
    };
}

OperationStatus CaptureControlEndpoint::StopCapture(
    const CaptureStopRequest& request)
{
    const auto unit_it = unit_ids_.find(request.capture_plugin_id);
    if (unit_it == unit_ids_.end()) {
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
        0U,
    };
}

OperationStatus CaptureControlEndpoint::ReportHeartbeat(
    const WorkerHeartbeat& request)
{
    const auto unit_it = unit_ids_.find(request.worker_id);
    if (unit_it == unit_ids_.end()) {
        return OperationStatus{
            false,
            "FAILED",
            "unknown worker unit",
            0U,
        };
    }

    supervisor_.RecordHeartbeat(unit_it->second);
    return OperationStatus{
        true,
        RuntimeStateText(supervisor_.GetState(unit_it->second)),
        "heartbeat recorded",
        0U,
    };
}

OperationStatus CaptureControlEndpoint::ForwardWorkerLog(
    const WorkerLog& request)
{
    worker_logs_.push_back(request);
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
    plugin_load_results_.push_back(request);
    return OperationStatus{
        true,
        request.runtime_state,
        "plugin load result recorded",
        0U,
    };
}

const std::vector<WorkerLog>& CaptureControlEndpoint::GetWorkerLogs() const
{
    return worker_logs_;
}

const std::vector<PluginLoadResult>&
CaptureControlEndpoint::GetPluginLoadResults() const
{
    return plugin_load_results_;
}

DiagnosticsExportResponse CaptureControlEndpoint::ExportDiagnostics(
    const DiagnosticsExportRequest& request) const
{
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
    const auto unit_it = unit_ids_.find(std::string(runtime_id));
    if (unit_it == unit_ids_.end()) {
        return supervisor::kInvalidUnitId;
    }
    return unit_it->second;
}

}  // namespace aetherflow::capture

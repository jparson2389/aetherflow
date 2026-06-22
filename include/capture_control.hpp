#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "supervisor.hpp"

namespace aetherflow::capture {

struct CaptureMode {
    std::uint32_t width{0};
    std::uint32_t height{0};
    std::uint32_t target_fps{0};
    std::string pixel_format;
    std::uint32_t stride_bytes{0};
};

struct CaptureStartRequest {
    std::string capture_plugin_id;
    std::string device_id;
    CaptureMode mode;
    std::uint32_t timeout_ms{0};
};

struct CaptureStopRequest {
    std::string capture_plugin_id;
    std::string device_id;
    std::string reason;
};

struct OperationStatus {
    bool ok{false};
    std::string runtime_state;
    std::string message;
    std::uint32_t retry_budget_remaining{0};
};

struct WorkerHeartbeat {
    std::string worker_id;
    std::string health;
    std::uint32_t missed_heartbeats{0};
    std::uint64_t timestamp_ns{0};
};

struct WorkerLog {
    std::string worker_id;
    std::string level;
    std::string message;
    std::uint64_t timestamp_ns{0};
};

struct PluginLoadResult {
    std::string plugin_id;
    bool loaded{false};
    std::string runtime_state;
    std::string error_code;
    std::string error_message;
};

struct DiagnosticsExportRequest {
    std::vector<std::string> include_sections;
    bool include_recent_logs{false};
};

struct DiagnosticsExportResponse {
    std::string artifact_path;
    std::string summary;
};

class CaptureControlEndpoint {
public:
    explicit CaptureControlEndpoint(supervisor::IWorkerSupervisor& supervisor);

    void RegisterLaunchSpec(
        std::string_view runtime_id,
        std::string_view launcher_path,
        std::string_view args);

    [[nodiscard]] OperationStatus StartCapture(
        const CaptureStartRequest& request);

    [[nodiscard]] OperationStatus StopCapture(
        const CaptureStopRequest& request);

    [[nodiscard]] OperationStatus ReportHeartbeat(
        const WorkerHeartbeat& request);

    [[nodiscard]] OperationStatus ForwardWorkerLog(
        const WorkerLog& request);

    [[nodiscard]] OperationStatus ReportPluginLoadResult(
        const PluginLoadResult& request);

    [[nodiscard]] const std::vector<WorkerLog>& GetWorkerLogs() const;

    [[nodiscard]] const std::vector<PluginLoadResult>&
    GetPluginLoadResults() const;

    [[nodiscard]] DiagnosticsExportResponse ExportDiagnostics(
        const DiagnosticsExportRequest& request) const;

    [[nodiscard]] supervisor::UnitId GetUnitId(
        std::string_view runtime_id) const;

private:
    struct LaunchSpec {
        std::string launcher_path;
        std::string args;
    };

    supervisor::IWorkerSupervisor& supervisor_;
    std::unordered_map<std::string, LaunchSpec> launch_specs_;
    std::unordered_map<std::string, supervisor::UnitId> unit_ids_;
    std::vector<WorkerLog> worker_logs_;
    std::vector<PluginLoadResult> plugin_load_results_;
};

}  // namespace aetherflow::capture

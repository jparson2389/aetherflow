#pragma once

#include <cstdint>
#include <mutex>
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
        std::string_view args,
        std::string_view worker_id = {});

    // Declare a host-side dependency edge from the static unit manifest:
    // dependent_runtime_id directly depends on dependency_runtime_id. This is
    // the non-proto path for expressing a plugin's dependency graph; the frozen
    // CaptureControl service carries no dependency-registration RPC. Specs are
    // recorded by runtime id and bound to live UnitIds by ApplyDependencyManifest.
    void RegisterDependencySpec(
        std::string_view dependent_runtime_id,
        std::string_view dependency_runtime_id);

    // Bind every declared dependency spec to the supervisor for units that are
    // currently started. Returns true if all declared specs whose endpoints are
    // both live were registered; false if any live spec failed to register.
    // Specs whose units are not yet started are skipped (idempotent re-apply).
    [[nodiscard]] bool ApplyDependencyManifest();

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

    [[nodiscard]] std::vector<WorkerLog> GetWorkerLogs() const;

    [[nodiscard]] std::vector<PluginLoadResult> GetPluginLoadResults() const;

    [[nodiscard]] DiagnosticsExportResponse ExportDiagnostics(
        const DiagnosticsExportRequest& request) const;

    [[nodiscard]] supervisor::UnitId GetUnitId(
        std::string_view runtime_id) const;

private:
    struct LaunchSpec {
        std::string launcher_path;
        std::string args;
        std::string worker_id;
    };

    struct DependencySpec {
        std::string dependent_runtime_id;
        std::string dependency_runtime_id;
        bool applied{false};
    };

    // Guards all endpoint container state below. gRPC dispatches RPC handlers
    // concurrently, so every public method serializes through this mutex. Lock
    // order is always endpoint mutex -> supervisor's internal mutex; no path
    // acquires them in the reverse order.
    mutable std::mutex mutex_;
    supervisor::IWorkerSupervisor& supervisor_;
    std::unordered_map<std::string, LaunchSpec> launch_specs_;
    std::unordered_map<std::string, supervisor::UnitId> runtime_unit_ids_;
    std::unordered_map<std::string, supervisor::UnitId> worker_unit_ids_;
    std::vector<DependencySpec> dependency_specs_;
    std::vector<WorkerLog> worker_logs_;
    std::vector<PluginLoadResult> plugin_load_results_;
};

}  // namespace aetherflow::capture

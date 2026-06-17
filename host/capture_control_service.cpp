#include "capture_control_service.hpp"

#include <grpcpp/grpcpp.h>

#include <memory>
#include <string>
#include <utility>

#include "capture.grpc.pb.h"

namespace aetherflow::capture {

namespace capture_proto = ::aetherflow::capture::v1;

namespace {

// Transport vs. application outcome:
// Every RPC returns grpc::Status::OK as long as the request was delivered and
// processed. The application-level success/failure signal is carried in the
// frozen OperationStatus message (its `ok` field plus runtime_state, message,
// and retry_budget_remaining). Mapping a failed operation onto a gRPC error
// status would discard those fields (gRPC drops the response message on a
// non-OK status) and would force every Python consumer to special-case error
// codes instead of reading the authoritative host-reported state. The proto is
// frozen and intentionally models the outcome inside OperationStatus, so the
// adapter preserves that contract: gRPC status reflects transport health,
// OperationStatus.ok reflects the host's decision.
void WriteStatus(
    const OperationStatus& source,
    capture_proto::OperationStatus* target)
{
    target->set_ok(source.ok);
    target->set_runtime_state(source.runtime_state);
    target->set_message(source.message);
    target->set_retry_budget_remaining(source.retry_budget_remaining);
}

class CaptureControlService final : public capture_proto::CaptureControl::Service {
public:
    explicit CaptureControlService(CaptureControlEndpoint& endpoint)
        : endpoint_(endpoint)
    {
    }

    grpc::Status StartCapture(
        grpc::ServerContext*,
        const capture_proto::CaptureStartRequest* request,
        capture_proto::OperationStatus* response) override
    {
        const auto& mode = request->mode();
        WriteStatus(
            endpoint_.StartCapture(CaptureStartRequest{
                request->capture_plugin_id(),
                request->device_id(),
                CaptureMode{
                    mode.width(),
                    mode.height(),
                    mode.target_fps(),
                    mode.pixel_format(),
                    mode.stride_bytes(),
                },
                request->timeout_ms(),
            }),
            response);
        return grpc::Status::OK;
    }

    grpc::Status StopCapture(
        grpc::ServerContext*,
        const capture_proto::CaptureStopRequest* request,
        capture_proto::OperationStatus* response) override
    {
        WriteStatus(
            endpoint_.StopCapture(CaptureStopRequest{
                request->capture_plugin_id(),
                request->device_id(),
                request->reason(),
            }),
            response);
        return grpc::Status::OK;
    }

    grpc::Status ReportHeartbeat(
        grpc::ServerContext*,
        const capture_proto::WorkerHeartbeat* request,
        capture_proto::OperationStatus* response) override
    {
        WriteStatus(
            endpoint_.ReportHeartbeat(WorkerHeartbeat{
                request->worker_id(),
                request->health(),
                request->missed_heartbeats(),
                request->timestamp_ns(),
            }),
            response);
        return grpc::Status::OK;
    }

    grpc::Status ForwardWorkerLog(
        grpc::ServerContext*,
        const capture_proto::WorkerLog* request,
        capture_proto::OperationStatus* response) override
    {
        WriteStatus(
            endpoint_.ForwardWorkerLog(WorkerLog{
                request->worker_id(),
                request->level(),
                request->message(),
                request->timestamp_ns(),
            }),
            response);
        return grpc::Status::OK;
    }

    grpc::Status ReportPluginLoadResult(
        grpc::ServerContext*,
        const capture_proto::PluginLoadResult* request,
        capture_proto::OperationStatus* response) override
    {
        WriteStatus(
            endpoint_.ReportPluginLoadResult(PluginLoadResult{
                request->plugin_id(),
                request->loaded(),
                request->runtime_state(),
                request->error_code(),
                request->error_message(),
            }),
            response);
        return grpc::Status::OK;
    }

    grpc::Status ExportDiagnostics(
        grpc::ServerContext*,
        const capture_proto::DiagnosticsExportRequest* request,
        capture_proto::DiagnosticsExportResponse* response) override
    {
        DiagnosticsExportRequest native_request;
        native_request.include_recent_logs = request->include_recent_logs();
        native_request.include_sections.assign(
            request->include_sections().begin(),
            request->include_sections().end());

        const auto native_response = endpoint_.ExportDiagnostics(native_request);
        response->set_artifact_path(native_response.artifact_path);
        response->set_summary(native_response.summary);
        return grpc::Status::OK;
    }

private:
    CaptureControlEndpoint& endpoint_;
};

}  // namespace

class CaptureControlGrpcServer::Impl {
public:
    explicit Impl(CaptureControlEndpoint& endpoint)
        : service(endpoint)
    {
    }

    CaptureControlService service;
    std::unique_ptr<grpc::Server> server;
    std::string address;
};

CaptureControlGrpcServer::CaptureControlGrpcServer(
    CaptureControlEndpoint& endpoint)
    : impl_(std::make_unique<Impl>(endpoint))
{
}

CaptureControlGrpcServer::~CaptureControlGrpcServer() = default;

CaptureControlGrpcServer::CaptureControlGrpcServer(
    CaptureControlGrpcServer&&) noexcept = default;

CaptureControlGrpcServer& CaptureControlGrpcServer::operator=(
    CaptureControlGrpcServer&&) noexcept = default;

bool CaptureControlGrpcServer::Start(std::string_view listen_address)
{
    impl_->address = std::string(listen_address);

    grpc::ServerBuilder builder;
    builder.AddListeningPort(impl_->address, grpc::InsecureServerCredentials());
    builder.RegisterService(&impl_->service);
    impl_->server = builder.BuildAndStart();
    return impl_->server != nullptr;
}

void CaptureControlGrpcServer::Wait()
{
    if (impl_->server) {
        impl_->server->Wait();
    }
}

void CaptureControlGrpcServer::Shutdown()
{
    if (impl_->server) {
        impl_->server->Shutdown();
    }
}

const std::string& CaptureControlGrpcServer::listen_address() const
{
    return impl_->address;
}

}  // namespace aetherflow::capture

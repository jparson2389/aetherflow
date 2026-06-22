#pragma once

#include <memory>
#include <string>
#include <string_view>

#include "capture_control.hpp"

namespace aetherflow::capture {

class CaptureControlGrpcServer {
public:
    explicit CaptureControlGrpcServer(CaptureControlEndpoint& endpoint);
    ~CaptureControlGrpcServer();

    CaptureControlGrpcServer(const CaptureControlGrpcServer&) = delete;
    CaptureControlGrpcServer& operator=(const CaptureControlGrpcServer&) = delete;

    CaptureControlGrpcServer(CaptureControlGrpcServer&&) noexcept;
    CaptureControlGrpcServer& operator=(CaptureControlGrpcServer&&) noexcept;

    [[nodiscard]] bool Start(std::string_view listen_address);
    void Wait();
    void Shutdown();

    [[nodiscard]] const std::string& listen_address() const;

private:
    class Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace aetherflow::capture

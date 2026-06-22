#include "capture_control.hpp"
#include "capture_control_service.hpp"
#include "supervisor.hpp"

#include <chrono>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>

namespace {

struct LaunchSpecParts {
    std::string runtime_id;
    std::string launcher_path;
    std::string args;
};

LaunchSpecParts ParseLaunchSpec(std::string_view raw)
{
    const std::size_t equals = raw.find('=');
    if (equals == std::string_view::npos || equals == 0 ||
        equals == raw.size() - 1) {
        throw std::invalid_argument(
            "--launch-spec must use runtime_id=launcher_path[,args]");
    }

    LaunchSpecParts parts;
    parts.runtime_id = std::string(raw.substr(0, equals));

    const std::string_view remainder = raw.substr(equals + 1);
    const std::size_t comma = remainder.find(',');
    if (comma == std::string_view::npos) {
        parts.launcher_path = std::string(remainder);
        return parts;
    }

    parts.launcher_path = std::string(remainder.substr(0, comma));
    parts.args = std::string(remainder.substr(comma + 1));
    return parts;
}

}  // namespace

int main(int argc, char** argv)
{
    std::string listen_address = "127.0.0.1:50051";

    auto supervisor = aetherflow::supervisor::CreateWorkerSupervisor(
        3U,
        std::chrono::seconds{60});
    aetherflow::capture::CaptureControlEndpoint endpoint(*supervisor);

    try {
        for (int index = 1; index < argc; ++index) {
            const std::string_view arg(argv[index]);
            if (arg == "--listen") {
                if (++index >= argc) {
                    throw std::invalid_argument("--listen requires an address");
                }
                listen_address = argv[index];
                continue;
            }
            if (arg == "--launch-spec") {
                if (++index >= argc) {
                    throw std::invalid_argument(
                        "--launch-spec requires runtime_id=launcher_path[,args]");
                }
                const auto spec = ParseLaunchSpec(argv[index]);
                endpoint.RegisterLaunchSpec(
                    spec.runtime_id,
                    spec.launcher_path,
                    spec.args);
                continue;
            }
            throw std::invalid_argument("unknown argument: " + std::string(arg));
        }
    } catch (const std::exception& exc) {
        std::cerr << "Aetherflow CaptureControl server argument error: "
                  << exc.what() << '\n';
        return 2;
    }

    aetherflow::capture::CaptureControlGrpcServer server(endpoint);
    if (!server.Start(listen_address)) {
        std::cerr << "Aetherflow CaptureControl server failed to listen on "
                  << listen_address << '\n';
        return 1;
    }

    std::cerr << "AETHERFLOW_CAPTURE_CONTROL_LISTENING " << listen_address
              << '\n';
    server.Wait();
    return 0;
}

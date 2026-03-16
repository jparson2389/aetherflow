#include "plugin_system.hpp"

#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <system_error>
#include <vector>

namespace fs = std::filesystem;

namespace
{

    using aetherflow::plugins::PluginType;
    using aetherflow::plugins::RuntimeState;

    constexpr std::array<std::string_view, 6> kRuntimeStates = {
        "RUNNING",
        "DEGRADED",
        "RECOVERING",
        "FAILED",
        "LOCKED",
        "GRACE",
    };

    constexpr std::array<std::string_view, 6> kPluginTypes = {
        "input",
        "output",
        "capture",
        "display",
        "worker",
        "resource",
    };

    static_assert(aetherflow::plugins::kRequiredRsaKeyBits == 3072U);
    static_assert(
        std::string_view(aetherflow::plugins::kRequiredSignatureScheme) ==
        "Authenticode");
    static_assert(
        std::string_view(aetherflow::plugins::kRequiredDigestAlgorithm) ==
        "SHA-256");
    static_assert(static_cast<std::uint8_t>(PluginType::kInput) == 0U);
    static_assert(static_cast<std::uint8_t>(PluginType::kResource) == 5U);
    static_assert(static_cast<std::uint8_t>(RuntimeState::kRunning) == 0U);
    static_assert(static_cast<std::uint8_t>(RuntimeState::kGrace) == 5U);

    struct Options
    {
        fs::path repo_root;
        fs::path header_path;
        fs::path proto_path;
        fs::path output_path;
    };

    struct Report
    {
        bool success = true;
        std::vector<std::string> errors;
        std::vector<std::string> src_native_files;
        std::size_t rpc_count = 0;
        std::size_t message_count = 0;
    };

    std::string EscapeJson(std::string_view value)
    {
        std::string escaped;
        escaped.reserve(value.size());
        for (const char character : value)
        {
            switch (character)
            {
            case '\\':
                escaped += "\\\\";
                break;
            case '"':
                escaped += "\\\"";
                break;
            case '\n':
                escaped += "\\n";
                break;
            case '\r':
                escaped += "\\r";
                break;
            case '\t':
                escaped += "\\t";
                break;
            default:
                escaped.push_back(character);
                break;
            }
        }
        return escaped;
    }

    std::string Quote(std::string_view value)
    {
        return "\"" + EscapeJson(value) + "\"";
    }

    std::string PathText(const fs::path &path)
    {
        return path.lexically_normal().generic_string();
    }

    template <std::size_t kSize>
    std::string JsonArray(const std::array<std::string_view, kSize> &values)
    {
        std::ostringstream buffer;
        buffer << "[";
        for (std::size_t index = 0; index < values.size(); ++index)
        {
            if (index > 0U)
            {
                buffer << ", ";
            }
            buffer << Quote(values[index]);
        }
        buffer << "]";
        return buffer.str();
    }

    std::string JsonArray(const std::vector<std::string> &values)
    {
        std::ostringstream buffer;
        buffer << "[";
        for (std::size_t index = 0; index < values.size(); ++index)
        {
            if (index > 0U)
            {
                buffer << ", ";
            }
            buffer << Quote(values[index]);
        }
        buffer << "]";
        return buffer.str();
    }

    std::optional<std::string> ReadTextFile(
        const fs::path &path,
        std::vector<std::string> *errors)
    {
        std::ifstream stream(path, std::ios::binary);
        if (!stream)
        {
            errors->push_back("Unable to open file: " + PathText(path));
            return std::nullopt;
        }

        return std::string(
            std::istreambuf_iterator<char>(stream),
            std::istreambuf_iterator<char>());
    }

    std::size_t CountOccurrences(std::string_view haystack, std::string_view needle)
    {
        std::size_t count = 0U;
        std::size_t search_from = 0U;
        while (true)
        {
            const std::size_t position = haystack.find(needle, search_from);
            if (position == std::string_view::npos)
            {
                break;
            }
            ++count;
            search_from = position + needle.size();
        }
        return count;
    }

    bool ContainsAllTokens(
        std::string_view text,
        const std::vector<std::string_view> &tokens,
        const std::string &label,
        std::vector<std::string> *errors)
    {
        bool valid = true;
        for (const std::string_view token : tokens)
        {
            if (text.find(token) == std::string_view::npos)
            {
                valid = false;
                errors->push_back(label + " is missing required token: " +
                                  std::string(token));
            }
        }
        return valid;
    }

    bool HasNativeSourceExtension(const fs::path &path)
    {
        std::string extension = path.extension().string();
        std::transform(
            extension.begin(),
            extension.end(),
            extension.begin(),
            [](unsigned char character)
            {
                return static_cast<char>(std::tolower(character));
            });

        return extension == ".c" || extension == ".cc" || extension == ".cpp" ||
               extension == ".cxx" || extension == ".h" || extension == ".hh" ||
               extension == ".hpp" || extension == ".hxx" || extension == ".ixx";
    }

    Options ParseArguments(int argc, char *argv[])
    {
        Options options;
        options.repo_root = fs::current_path();

        for (int index = 1; index < argc; ++index)
        {
            const std::string_view argument = argv[index];
            if (argument == "--help")
            {
                std::cout
                    << "Usage: native_harness.exe [--repo-root PATH] [--header PATH] "
                       "[--proto PATH] [--output PATH]\n";
                std::exit(0);
            }

            if (index + 1 >= argc)
            {
                throw std::runtime_error("Missing value for argument: " +
                                         std::string(argument));
            }

            const fs::path value = argv[++index];
            if (argument == "--repo-root")
            {
                options.repo_root = value;
            }
            else if (argument == "--header")
            {
                options.header_path = value;
            }
            else if (argument == "--proto")
            {
                options.proto_path = value;
            }
            else if (argument == "--output")
            {
                options.output_path = value;
            }
            else
            {
                throw std::runtime_error("Unknown argument: " + std::string(argument));
            }
        }

        if (options.header_path.empty())
        {
            options.header_path = options.repo_root / "include" / "plugin_system.hpp";
        }
        if (options.proto_path.empty())
        {
            options.proto_path = options.repo_root / "proto" / "capture.proto";
        }

        options.repo_root = options.repo_root.lexically_normal();
        options.header_path = options.header_path.lexically_normal();
        options.proto_path = options.proto_path.lexically_normal();
        options.output_path = options.output_path.lexically_normal();
        return options;
    }

    void ValidateBoundary(const Options &options, Report *report)
    {
        const fs::path src_root = options.repo_root / "src";
        if (!fs::exists(src_root))
        {
            report->errors.push_back("Missing source tree: " + PathText(src_root));
            return;
        }

        std::error_code iterator_error;
        fs::recursive_directory_iterator iterator(
            src_root,
            fs::directory_options::skip_permission_denied,
            iterator_error);
        fs::recursive_directory_iterator end;

        while (iterator != end)
        {
            if (iterator_error)
            {
                report->errors.push_back(
                    "Failed while scanning src/: " + iterator_error.message());
                break;
            }

            const fs::directory_entry &entry = *iterator;
            std::error_code status_error;
            if (entry.is_regular_file(status_error) &&
                HasNativeSourceExtension(entry.path()))
            {
                std::error_code relative_error;
                fs::path relative_path =
                    fs::relative(entry.path(), options.repo_root, relative_error);
                report->src_native_files.push_back(
                    relative_error ? PathText(entry.path()) : PathText(relative_path));
            }

            ++iterator;
            iterator_error.clear();
        }

        std::sort(report->src_native_files.begin(), report->src_native_files.end());
        if (!report->src_native_files.empty())
        {
            std::ostringstream message;
            message << "Native source files are not allowed under src/: ";
            for (std::size_t index = 0; index < report->src_native_files.size();
                 ++index)
            {
                if (index > 0U)
                {
                    message << ", ";
                }
                message << report->src_native_files[index];
            }
            report->errors.push_back(message.str());
        }
    }

    void ValidateHeader(const Options &options, Report *report)
    {
        const auto header_text = ReadTextFile(options.header_path, &report->errors);
        if (!header_text.has_value())
        {
            return;
        }

        const std::vector<std::string_view> required_tokens = {
            "kRequiredSignatureScheme",
            "kRequiredDigestAlgorithm",
            "kRequiredRsaKeyBits",
            "enum class PluginType",
            "enum class RuntimeState",
            "struct Plugin",
            "struct PluginIdentity",
            "struct PluginPolicy",
            "struct SignaturePolicy",
            "struct PluginLoadDecision",
        };
        ContainsAllTokens(
            *header_text,
            required_tokens,
            "plugin_system.hpp",
            &report->errors);
    }

    void ValidateProto(const Options &options, Report *report)
    {
        const auto proto_text = ReadTextFile(options.proto_path, &report->errors);
        if (!proto_text.has_value())
        {
            return;
        }

        const std::vector<std::string_view> required_tokens = {
            "service CaptureControl",
            "rpc StartCapture",
            "rpc StopCapture",
            "rpc ReportHeartbeat",
            "rpc ForwardWorkerLog",
            "rpc ReportPluginLoadResult",
            "rpc ExportDiagnostics",
        };
        ContainsAllTokens(*proto_text, required_tokens, "capture.proto", &report->errors);
        report->rpc_count = CountOccurrences(*proto_text, "rpc ");
        report->message_count = CountOccurrences(*proto_text, "message ");
    }

    std::string BuildReportJson(const Options &options, const Report &report)
    {
        std::ostringstream json;
        json << "{\n";
        json << "  \"status\": " << Quote(report.success ? "ok" : "failed") << ",\n";
        json << "  \"repo_root\": " << Quote(PathText(options.repo_root)) << ",\n";
        json << "  \"header\": {\n";
        json << "    \"path\": " << Quote(PathText(options.header_path)) << ",\n";
        json << "    \"signature_scheme\": "
             << Quote(aetherflow::plugins::kRequiredSignatureScheme) << ",\n";
        json << "    \"digest_algorithm\": "
             << Quote(aetherflow::plugins::kRequiredDigestAlgorithm) << ",\n";
        json << "    \"rsa_key_bits\": " << aetherflow::plugins::kRequiredRsaKeyBits
             << ",\n";
        json << "    \"plugin_types\": " << JsonArray(kPluginTypes) << ",\n";
        json << "    \"runtime_states\": " << JsonArray(kRuntimeStates) << "\n";
        json << "  },\n";
        json << "  \"proto\": {\n";
        json << "    \"path\": " << Quote(PathText(options.proto_path)) << ",\n";
        json << "    \"service_name\": " << Quote("CaptureControl") << ",\n";
        json << "    \"rpc_count\": " << report.rpc_count << ",\n";
        json << "    \"message_count\": " << report.message_count << "\n";
        json << "  },\n";
        json << "  \"boundary\": {\n";
        json << "    \"src_native_files\": " << JsonArray(report.src_native_files)
             << "\n";
        json << "  },\n";
        json << "  \"errors\": " << JsonArray(report.errors) << "\n";
        json << "}\n";
        return json.str();
    }

    bool WriteReport(const fs::path &output_path, const std::string &report_json)
    {
        if (output_path.empty())
        {
            return true;
        }

        std::error_code create_error;
        const fs::path parent_path = output_path.parent_path();
        if (!parent_path.empty())
        {
            fs::create_directories(parent_path, create_error);
            if (create_error)
            {
                std::cerr << "Unable to create output directory: "
                          << create_error.message() << '\n';
                return false;
            }
        }

        std::ofstream stream(output_path, std::ios::binary | std::ios::trunc);
        if (!stream)
        {
            std::cerr << "Unable to write report: " << PathText(output_path) << '\n';
            return false;
        }
        stream << report_json;
        return static_cast<bool>(stream);
    }

} // namespace

int main(int argc, char *argv[])
{
    try
    {
        const Options options = ParseArguments(argc, argv);

        Report report;
        ValidateHeader(options, &report);
        ValidateProto(options, &report);
        ValidateBoundary(options, &report);
        report.success = report.errors.empty();

        const std::string report_json = BuildReportJson(options, report);
        if (!WriteReport(options.output_path, report_json))
        {
            return 1;
        }

        if (report.success)
        {
            std::cout << "Native harness validation complete.\n";
            if (!options.output_path.empty())
            {
                std::cout << "Report written to "
                          << PathText(options.output_path) << '\n';
            }
            return 0;
        }

        for (const std::string &error : report.errors)
        {
            std::cerr << error << '\n';
        }
        return 1;
    }
    catch (const std::exception &error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

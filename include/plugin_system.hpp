#pragma once

#include <cstdint>

namespace aetherflow::plugins {

enum class PluginType : std::uint8_t {
    kInput = 0,
    kOutput = 1,
    kCapture = 2,
    kDisplay = 3,
    kWorker = 4,
    kResource = 5,
};

struct PluginIdentity {
    const char* plugin_id;
    const char* name;
    const char* version;
    const char* api_version;
    PluginType plugin_type;
};

struct PluginPolicy {
    const char* required_entitlements;
    const char* requires_drivers;
    bool requires_worker;
    bool premium;
};

}  // namespace aetherflow::plugins

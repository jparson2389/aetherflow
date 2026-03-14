#pragma once

#include <cstdint>

namespace aetherflow::plugins {

inline constexpr const char* kRequiredSignatureScheme = "Authenticode";
inline constexpr const char* kRequiredDigestAlgorithm = "SHA-256";
inline constexpr std::uint32_t kRequiredRsaKeyBits = 3072;

enum class PluginType : std::uint8_t {
    kInput = 0,
    kOutput = 1,
    kCapture = 2,
    kDisplay = 3,
    kWorker = 4,
    kResource = 5,
};

enum class RuntimeState : std::uint8_t {
    kRunning = 0,
    kDegraded = 1,
    kRecovering = 2,
    kFailed = 3,
    kLocked = 4,
    kGrace = 5,
};

using PluginRuntimeState = RuntimeState;

struct Plugin {
    const char* plugin_id;
    const char* name;
    const char* version;
    const char* api_version;
    PluginType plugin_type;
    const char* const* required_entitlements;
    const char* const* requires_drivers;
    bool requires_worker;
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

struct SignaturePolicy {
    const char* signature_scheme;
    const char* digest_algorithm;
    std::uint32_t rsa_key_bits;
    const char* publisher_thumbprint;
    const char* trust_root_thumbprint;
    bool require_publisher_chain;
};

struct PluginLoadDecision {
    RuntimeState runtime_state;
    bool allow_process_load;
    bool allow_registration;
    const char* denial_reason;
};

}  // namespace aetherflow::plugins

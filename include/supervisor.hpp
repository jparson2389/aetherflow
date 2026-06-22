#pragma once

#include <chrono>
#include <cstdint>
#include <memory>
#include <string_view>
#include <vector>

#include "plugin_system.hpp"

namespace aetherflow::supervisor {

using plugins::RuntimeState;

// Default restart budget: 3 attempts within a 60-second sliding window.
// The host supervisor is the sole authority for restart decisions; Python
// consumers must not reimplement this logic.
inline constexpr std::uint32_t kDefaultMaxRestarts = 3U;
inline constexpr std::chrono::seconds kDefaultRestartWindow{60};

// Stable identifier for a supervised unit (worker process or plugin process).
// Assigned by StartUnit() and valid until the unit is torn down.
using UnitId = std::uint32_t;
inline constexpr UnitId kInvalidUnitId = 0U;

// Exit code and classification of a process termination event.
struct ExitStatus {
    int exit_code{0};
    bool crashed{false};  // true: abnormal termination (signal/SEH); false: clean exit
};

// Immutable point-in-time snapshot of a supervised unit's state.
// Shell consumers render this snapshot; they must not derive additional state
// independently from these fields.
struct UnitSnapshot {
    UnitId id{kInvalidUnitId};
    RuntimeState state{RuntimeState::kRunning};
    std::uint32_t restart_count{0};
    std::uint32_t restarts_in_window{0};
    std::uint32_t missed_heartbeats{0};
    bool process_alive{false};
};

// Abstraction over an OS-level process handle.
// Separates process lifecycle from the supervision state machine so the
// supervisor can be exercised in tests without spawning real processes.
class IProcessHandle {
public:
    virtual ~IProcessHandle() = default;

    // Returns true while the supervised process is still running.
    [[nodiscard]] virtual bool IsAlive() const = 0;

    // Request graceful termination. Returns true if the process exits within
    // grace_period. Callers must tolerate false (timeout or permission error).
    virtual bool Terminate(std::chrono::milliseconds grace_period) = 0;

    // Exit code of the exited process. Only valid after IsAlive() returns false.
    [[nodiscard]] virtual int ExitCode() const = 0;
};

// Host-authoritative supervisor for worker and plugin runtime units.
//
// This interface is the single decision authority for:
//   - process lifetime (start, stop)
//   - heartbeat liveness tracking
//   - crash detection and restart-budget enforcement
//   - runtime state surfacing to gRPC consumers
//
// Failure domain isolation: each unit owns its own state. A crash or budget
// exhaustion in unit A has no effect on the RuntimeState of unit B. The shell
// and unrelated plugins remain operational.
//
// Restart budget: per-unit budget of kDefaultMaxRestarts attempts within a
// kDefaultRestartWindow sliding window. Budget exhaustion produces
// RuntimeState::kFailed. The supervisor does not attempt further restarts after
// kFailed; manual reload via StartUnit() is required.
//
// Python workers and shell consumers obtain authoritative state only through the
// gRPC control plane backed by this interface. They must not make independent
// restart or health-transition decisions.
class IWorkerSupervisor {
public:
    virtual ~IWorkerSupervisor() = default;

    // Register and launch a supervised unit. Returns the stable UnitId.
    // unit_name: human-readable label used in diagnostics and logs.
    // launcher_path: absolute path to the process executable to spawn.
    // args: whitespace-separated command-line arguments for the process.
    // Precondition: launcher_path names an OS process executable; thread-only
    // or in-memory worker units are not valid supervision targets.
    // Precondition: unit_name must not already be registered as a live unit.
    // Returns kInvalidUnitId if the unit could not be started.
    [[nodiscard]] virtual UnitId StartUnit(
        std::string_view unit_name,
        std::string_view launcher_path,
        std::string_view args) = 0;

    // Register that dependent_id directly depends on dependency_id. When the
    // dependency crashes or stops, only its direct dependents are degraded;
    // unrelated units keep their current state.
    [[nodiscard]] virtual bool RegisterDependency(
        UnitId dependent_id,
        UnitId dependency_id) = 0;

    // Relaunch a unit that is in RuntimeState::kRecovering using its original
    // OS process launcher. Returns false for unknown, failed, or non-recovering
    // units and never restarts unrelated units.
    [[nodiscard]] virtual bool RestartUnit(UnitId id) = 0;

    // Request orderly shutdown of the given unit.
    // The process receives a graceful termination signal and is waited on for
    // grace_period. If the process does not exit in time, it is forcibly
    // terminated and the unit transitions to RuntimeState::kFailed.
    virtual void StopUnit(UnitId id, std::chrono::milliseconds grace_period) = 0;

    // Record a successful heartbeat tick received from the given unit.
    // Resets the missed-heartbeat counter. Transitions the unit from kDegraded
    // or kRecovering back to kRunning. No-op for units in kFailed state.
    virtual void RecordHeartbeat(UnitId id) = 0;

    // Record a missed heartbeat tick (no heartbeat received within the expected
    // interval). Escalation schedule:
    //   - 2 consecutive missed ticks  → kDegraded
    //   - 3 or more consecutive ticks → treated as a crash via RecordCrash
    // No-op for units already in kFailed state.
    virtual void RecordMissedHeartbeat(UnitId id) = 0;

    // Record an abnormal process exit for the given unit.
    // Increments the restart counter and enforces the budget:
    //   - within budget: transitions to kRecovering
    //   - budget exhausted: transitions to kFailed (permanent until manual reload)
    // The supervisor does not automatically relaunch the process; the caller
    // is responsible for calling StartUnit() again after kRecovering.
    virtual void RecordCrash(UnitId id, ExitStatus status) = 0;

    // Evaluate and apply the restart budget for the given unit.
    // Returns kRecovering if another attempt is allowed; kFailed if the budget
    // is exhausted. Called internally by RecordCrash; exposed for explicit
    // manual-restart flows.
    [[nodiscard]] virtual RuntimeState EnforceRestartBudget(UnitId id) = 0;

    // Return an immutable snapshot of the given unit's complete state.
    [[nodiscard]] virtual UnitSnapshot GetSnapshot(UnitId id) const = 0;

    // Return immutable snapshots for all known units. This is the stable
    // shell-facing state export; consumers must render these records rather
    // than infer the runtime unit set locally.
    [[nodiscard]] virtual std::vector<UnitSnapshot> GetSnapshots() const = 0;

    // Return the current RuntimeState of the given unit.
    [[nodiscard]] virtual RuntimeState GetState(UnitId id) const = 0;
};

[[nodiscard]] std::unique_ptr<IWorkerSupervisor> CreateWorkerSupervisor(
    std::uint32_t max_restarts = kDefaultMaxRestarts,
    std::chrono::seconds restart_window = kDefaultRestartWindow);

}  // namespace aetherflow::supervisor

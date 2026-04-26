#include "supervisor.hpp"

#include <chrono>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>

#ifdef _WIN32
#include <Windows.h>
#else
#include <cerrno>
#include <csignal>
#include <cstring>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace aetherflow::supervisor {

// ---------------------------------------------------------------------------
// Platform process handle implementations
// ---------------------------------------------------------------------------

#ifdef _WIN32

class Win32ProcessHandle final : public IProcessHandle {
public:
    explicit Win32ProcessHandle(HANDLE process_handle)
        : process_handle_(process_handle) {}

    ~Win32ProcessHandle() override {
        if (process_handle_ != INVALID_HANDLE_VALUE) {
            CloseHandle(process_handle_);
        }
    }

    [[nodiscard]] bool IsAlive() const override {
        if (process_handle_ == INVALID_HANDLE_VALUE) {
            return false;
        }
        DWORD exit_code = 0;
        if (!GetExitCodeProcess(process_handle_, &exit_code)) {
            return false;
        }
        return exit_code == STILL_ACTIVE;
    }

    bool Terminate(std::chrono::milliseconds grace_period) override {
        if (process_handle_ == INVALID_HANDLE_VALUE) {
            return true;
        }
        // Signal the process to exit gracefully via a WM_CLOSE / TerminateProcess.
        // For headless worker processes we go straight to TerminateProcess after
        // waiting the grace period for a clean exit.
        const DWORD wait_ms = static_cast<DWORD>(grace_period.count());
        const DWORD result = WaitForSingleObject(process_handle_, wait_ms);
        if (result == WAIT_OBJECT_0) {
            return true;  // Process already exited cleanly.
        }
        // Grace period elapsed — force terminate.
        TerminateProcess(process_handle_, 1);
        // Wait briefly for handle to become signaled after forced kill.
        return WaitForSingleObject(process_handle_, 2000) == WAIT_OBJECT_0;
    }

    [[nodiscard]] int ExitCode() const override {
        if (process_handle_ == INVALID_HANDLE_VALUE) {
            return -1;
        }
        DWORD exit_code = 0;
        GetExitCodeProcess(process_handle_, &exit_code);
        return static_cast<int>(exit_code);
    }

private:
    HANDLE process_handle_;
};

static std::unique_ptr<IProcessHandle> SpawnProcess(
    std::string_view launcher_path,
    std::string_view args)
{
    std::string cmdline = std::string(launcher_path);
    if (!args.empty()) {
        cmdline += ' ';
        cmdline += args;
    }

    STARTUPINFOA si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};

    const BOOL ok = CreateProcessA(
        nullptr,
        cmdline.data(),
        nullptr,
        nullptr,
        FALSE,
        CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS,
        nullptr,
        nullptr,
        &si,
        &pi);

    if (!ok) {
        return nullptr;
    }
    CloseHandle(pi.hThread);
    return std::make_unique<Win32ProcessHandle>(pi.hProcess);
}

#else  // POSIX

class PosixProcessHandle final : public IProcessHandle {
public:
    explicit PosixProcessHandle(pid_t pid) : pid_(pid) {}

    [[nodiscard]] bool IsAlive() const override {
        if (pid_ <= 0) {
            return false;
        }
        const int result = ::kill(pid_, 0);
        return result == 0;
    }

    bool Terminate(std::chrono::milliseconds grace_period) override {
        if (pid_ <= 0) {
            return true;
        }
        ::kill(pid_, SIGTERM);

        // Poll until the process exits or grace_period elapses.
        const auto deadline =
            std::chrono::steady_clock::now() + grace_period;
        while (std::chrono::steady_clock::now() < deadline) {
            int status = 0;
            const pid_t result = ::waitpid(pid_, &status, WNOHANG);
            if (result == pid_) {
                exit_code_ = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
                pid_ = -1;
                return true;
            }
            struct timespec ts{0, 10'000'000};  // 10 ms
            ::nanosleep(&ts, nullptr);
        }
        // Grace period elapsed — send SIGKILL.
        ::kill(pid_, SIGKILL);
        int status = 0;
        ::waitpid(pid_, &status, 0);
        exit_code_ = -1;
        pid_ = -1;
        return false;
    }

    [[nodiscard]] int ExitCode() const override {
        return exit_code_;
    }

private:
    pid_t pid_;
    int exit_code_{-1};
};

static std::unique_ptr<IProcessHandle> SpawnProcess(
    std::string_view launcher_path,
    std::string_view args)
{
    const pid_t pid = ::fork();
    if (pid < 0) {
        return nullptr;  // fork failed
    }
    if (pid == 0) {
        // Child: exec the launcher.
        const std::string path_str(launcher_path);
        const std::string args_str(args);
        ::execl(path_str.c_str(), path_str.c_str(),
                args_str.empty() ? nullptr : args_str.c_str(),
                nullptr);
        // exec failed — exit the child immediately so the parent can detect it.
        ::_exit(127);
    }
    return std::make_unique<PosixProcessHandle>(pid);
}

#endif  // _WIN32

// ---------------------------------------------------------------------------
// WorkerSupervisorImpl — concrete supervisor implementing IWorkerSupervisor
// ---------------------------------------------------------------------------

namespace {

using Clock = std::chrono::steady_clock;
using TimePoint = Clock::time_point;

struct UnitRecord {
    std::string name;
    RuntimeState state{RuntimeState::kRunning};
    std::uint32_t restart_count{0};
    std::uint32_t restarts_in_window{0};
    std::uint32_t missed_heartbeats{0};
    TimePoint window_start{Clock::now()};
    std::unique_ptr<IProcessHandle> process;

    // Per-unit budget limits copied from supervisor construction.
    std::uint32_t max_restarts{kDefaultMaxRestarts};
    std::chrono::seconds restart_window{kDefaultRestartWindow};
};

}  // namespace

// Thread-safe concrete supervisor.
//
// All public methods acquire the internal mutex before touching state, so the
// supervisor can be called from the gRPC control-plane thread (heartbeat ticks)
// and the watchdog thread (missed-heartbeat detection) concurrently.
class WorkerSupervisorImpl final : public IWorkerSupervisor {
public:
    explicit WorkerSupervisorImpl(
        std::uint32_t max_restarts = kDefaultMaxRestarts,
        std::chrono::seconds restart_window = kDefaultRestartWindow)
        : max_restarts_(max_restarts), restart_window_(restart_window) {}

    // Inject a mock process handle for a registered unit. Used in tests to
    // exercise the supervision state machine without real process spawning.
    void InjectProcess(UnitId id, std::unique_ptr<IProcessHandle> handle) {
        std::lock_guard lock(mutex_);
        GetRecord(id).process = std::move(handle);
    }

    [[nodiscard]] UnitId StartUnit(
        std::string_view unit_name,
        std::string_view launcher_path,
        std::string_view args) override
    {
        std::lock_guard lock(mutex_);

        // Reject duplicate registrations: a live unit with this name already exists.
        for (const auto& [existing_id, record] : records_) {
            if (record.name == unit_name &&
                record.state != RuntimeState::kFailed) {
                return kInvalidUnitId;
            }
        }

        const UnitId id = next_id_++;
        UnitRecord record;
        record.name = std::string(unit_name);
        record.state = RuntimeState::kRunning;
        record.max_restarts = max_restarts_;
        record.restart_window = restart_window_;
        record.window_start = Clock::now();

        if (!launcher_path.empty()) {
            record.process = SpawnProcess(launcher_path, args);
            if (!record.process) {
                // Process failed to launch — unit starts in failed state.
                record.state = RuntimeState::kFailed;
            }
        }

        records_.emplace(id, std::move(record));
        return id;
    }

    void StopUnit(UnitId id, std::chrono::milliseconds grace_period) override {
        std::lock_guard lock(mutex_);
        auto& record = GetRecord(id);

        if (record.state == RuntimeState::kFailed) {
            return;
        }
        if (record.process && record.process->IsAlive()) {
            record.process->Terminate(grace_period);
        }
        record.state = RuntimeState::kFailed;
    }

    void RecordHeartbeat(UnitId id) override {
        std::lock_guard lock(mutex_);
        auto& record = GetRecord(id);

        if (record.state == RuntimeState::kFailed) {
            return;
        }
        record.missed_heartbeats = 0;
        if (record.state == RuntimeState::kDegraded ||
            record.state == RuntimeState::kRecovering) {
            record.state = RuntimeState::kRunning;
        }
    }

    void RecordMissedHeartbeat(UnitId id) override {
        std::lock_guard lock(mutex_);
        auto& record = GetRecord(id);

        if (record.state == RuntimeState::kFailed) {
            return;
        }
        ++record.missed_heartbeats;
        if (record.missed_heartbeats >= 3U) {
            ++record.restart_count;
            ApplyBudget(record);
            return;
        }
        if (record.missed_heartbeats >= 2U) {
            record.state = RuntimeState::kDegraded;
        }
    }

    void RecordCrash(UnitId id, ExitStatus /*status*/) override {
        std::lock_guard lock(mutex_);
        auto& record = GetRecord(id);
        if (record.state == RuntimeState::kFailed) {
            return;
        }
        ++record.restart_count;
        ApplyBudget(record);
    }

    [[nodiscard]] RuntimeState EnforceRestartBudget(UnitId id) override {
        std::lock_guard lock(mutex_);
        return ApplyBudget(GetRecord(id));
    }

    [[nodiscard]] UnitSnapshot GetSnapshot(UnitId id) const override {
        std::lock_guard lock(mutex_);
        const auto& record = GetRecord(id);
        UnitSnapshot snap;
        snap.id = id;
        snap.state = record.state;
        snap.restart_count = record.restart_count;
        snap.restarts_in_window = record.restarts_in_window;
        snap.missed_heartbeats = record.missed_heartbeats;
        snap.process_alive = record.process && record.process->IsAlive();
        return snap;
    }

    [[nodiscard]] RuntimeState GetState(UnitId id) const override {
        std::lock_guard lock(mutex_);
        return GetRecord(id).state;
    }

private:
    UnitRecord& GetRecord(UnitId id) {
        auto it = records_.find(id);
        if (it == records_.end()) {
            throw std::out_of_range("supervisor: unknown UnitId " +
                                    std::to_string(id));
        }
        return it->second;
    }

    const UnitRecord& GetRecord(UnitId id) const {
        auto it = records_.find(id);
        if (it == records_.end()) {
            throw std::out_of_range("supervisor: unknown UnitId " +
                                    std::to_string(id));
        }
        return it->second;
    }

    // Evaluate the restart budget for the record and update its state.
    // Returns the resulting RuntimeState.
    RuntimeState ApplyBudget(UnitRecord& record) {
        const auto now = Clock::now();
        const auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            now - record.window_start);
        if (elapsed > record.restart_window) {
            record.window_start = now;
            record.restarts_in_window = 0;
        }
        ++record.restarts_in_window;
        record.state = (record.restarts_in_window > record.max_restarts)
            ? RuntimeState::kFailed
            : RuntimeState::kRecovering;
        return record.state;
    }

    mutable std::mutex mutex_;
    std::unordered_map<UnitId, UnitRecord> records_;
    UnitId next_id_{1U};
    std::uint32_t max_restarts_{kDefaultMaxRestarts};
    std::chrono::seconds restart_window_{kDefaultRestartWindow};
};

}  // namespace aetherflow::supervisor

#include "supervisor.hpp"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>

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
    // Quote argv[0] so launcher paths containing spaces (e.g. under
    // "C:\Program Files\...") are parsed as a single executable token rather
    // than split by CreateProcessA's whitespace-delimited resolution.
    std::string cmdline = '"' + std::string(launcher_path) + '"';
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

    ~PosixProcessHandle() override {
        // Non-blocking reap so a handle discarded without an explicit
        // Terminate/IsAlive does not leak a zombie process.
        if (pid_ > 0) {
            int status = 0;
            ::waitpid(pid_, &status, WNOHANG);
        }
    }

    [[nodiscard]] bool IsAlive() const override {
        if (pid_ <= 0) {
            return false;
        }
        // Reap the child non-blockingly. A process that has exited but not yet
        // been waited on is a zombie, and kill(pid, 0) still succeeds for a
        // zombie — so kill() alone would falsely report it alive. waitpid()
        // collects the exit status and lets the watchdog see the real death.
        int status = 0;
        const pid_t result = ::waitpid(pid_, &status, WNOHANG);
        if (result == pid_) {
            exit_code_ = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
            pid_ = -1;
            return false;
        }
        if (result < 0) {
            // No such child (already reaped elsewhere) — treat as not alive.
            pid_ = -1;
            return false;
        }
        // result == 0: child still running.
        return ::kill(pid_, 0) == 0;
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
    mutable pid_t pid_;
    mutable int exit_code_{-1};
};

static std::unique_ptr<IProcessHandle> SpawnProcess(
    std::string_view launcher_path,
    std::string_view args)
{
    // Split the args string into whitespace-separated tokens per the
    // IWorkerSupervisor contract, so each becomes a distinct argv entry.
    std::vector<std::string> tokens;
    {
        std::istringstream iss{std::string(args)};
        std::string token;
        while (iss >> token) {
            tokens.push_back(std::move(token));
        }
    }

    const pid_t pid = ::fork();
    if (pid < 0) {
        return nullptr;  // fork failed
    }
    if (pid == 0) {
        // Child: exec the launcher with a null-terminated argv vector.
        const std::string path_str(launcher_path);
        std::vector<char*> argv;
        argv.reserve(tokens.size() + 2);
        argv.push_back(const_cast<char*>(path_str.c_str()));
        for (std::string& token : tokens) {
            argv.push_back(const_cast<char*>(token.c_str()));
        }
        argv.push_back(nullptr);
        ::execv(path_str.c_str(), argv.data());
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
    std::string launcher_path;
    std::string args;
    RuntimeState state{RuntimeState::kRunning};
    std::uint32_t restart_count{0};
    std::uint32_t restarts_in_window{0};
    std::uint32_t missed_heartbeats{0};
    TimePoint window_start{Clock::now()};
    std::unique_ptr<IProcessHandle> process;
    std::vector<UnitId> direct_dependents;

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

        if (launcher_path.empty()) {
            return kInvalidUnitId;
        }

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
        record.launcher_path = std::string(launcher_path);
        record.args = std::string(args);
        record.state = RuntimeState::kRunning;
        record.max_restarts = max_restarts_;
        record.restart_window = restart_window_;
        record.window_start = Clock::now();

        record.process = SpawnProcess(launcher_path, args);
        if (!record.process) {
            return kInvalidUnitId;
        }

        records_.emplace(id, std::move(record));
        return id;
    }

    [[nodiscard]] bool RegisterDependency(
        UnitId dependent_id,
        UnitId dependency_id) override
    {
        std::lock_guard lock(mutex_);
        if (!HasRecord(dependent_id) || !HasRecord(dependency_id)) {
            return false;
        }
        auto& dependency = GetRecord(dependency_id);
        dependency.direct_dependents.push_back(dependent_id);
        return true;
    }

    [[nodiscard]] bool RestartUnit(UnitId id) override {
        std::unique_ptr<IProcessHandle> old_process;
        bool result = false;
        {
            std::lock_guard lock(mutex_);
            auto it = records_.find(id);
            if (it == records_.end()) {
                return false;  // Unknown id: contract returns false, not throw.
            }
            auto& record = it->second;
            if (record.state != RuntimeState::kRecovering) {
                return false;
            }

            // Move the old handle out before spawning so it is terminated on
            // both success and failure paths — a recovering unit's process may
            // still be alive and must not be abandoned when spawn fails.
            old_process = std::move(record.process);

            auto process = SpawnProcess(record.launcher_path, record.args);
            if (!process) {
                record.state = RuntimeState::kFailed;
                DegradeDirectDependents(record);
                result = false;
            } else {
                record.process = std::move(process);
                record.missed_heartbeats = 0;
                record.state = RuntimeState::kRunning;
                result = true;
            }
        }
        // Terminate the displaced handle outside the lock (both paths): Terminate()
        // can block on the grace window and must not stall other units.
        if (old_process && old_process->IsAlive()) {
            old_process->Terminate(std::chrono::milliseconds{0});
        }
        return result;
    }

    void StopUnit(UnitId id, std::chrono::milliseconds grace_period) override {
        std::unique_ptr<IProcessHandle> process;
        {
            std::lock_guard lock(mutex_);
            auto& record = GetRecord(id);

            if (record.state == RuntimeState::kFailed) {
                return;
            }
            // Move the handle out and mark the unit failed under the lock, then
            // terminate outside it: Terminate() can block for the full grace
            // window, and holding the supervisor mutex that long would stall
            // heartbeats and liveness polling for every other unit.
            process = std::move(record.process);
            record.state = RuntimeState::kFailed;
            DegradeDirectDependents(record);
        }
        if (process && process->IsAlive()) {
            process->Terminate(grace_period);
        }
    }

    void RecordHeartbeat(UnitId id) override {
        std::lock_guard lock(mutex_);
        auto& record = GetRecord(id);

        if (record.state == RuntimeState::kFailed) {
            return;
        }
        record.missed_heartbeats = 0;
        if (record.state == RuntimeState::kDegraded) {
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
            DegradeDirectDependents(record);
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
        DegradeDirectDependents(record);
    }

    [[nodiscard]] RuntimeState EnforceRestartBudget(UnitId id) override {
        std::lock_guard lock(mutex_);
        return ApplyBudget(GetRecord(id));
    }

    [[nodiscard]] UnitSnapshot GetSnapshot(UnitId id) const override {
        std::lock_guard lock(mutex_);
        return MakeSnapshot(id, GetRecord(id));
    }

    [[nodiscard]] std::vector<UnitSnapshot> GetSnapshots() const override {
        std::lock_guard lock(mutex_);
        std::vector<UnitId> ids;
        ids.reserve(records_.size());
        for (const auto& [id, record] : records_) {
            (void)record;
            ids.push_back(id);
        }
        std::sort(ids.begin(), ids.end());

        std::vector<UnitSnapshot> snapshots;
        snapshots.reserve(ids.size());
        for (const UnitId id : ids) {
            snapshots.push_back(MakeSnapshot(id, GetRecord(id)));
        }
        return snapshots;
    }

    [[nodiscard]] RuntimeState GetState(UnitId id) const override {
        std::lock_guard lock(mutex_);
        return GetRecord(id).state;
    }

    std::uint32_t PollProcessLiveness() override {
        std::lock_guard lock(mutex_);
        std::uint32_t transitioned = 0;
        for (auto& [id, record] : records_) {
            (void)id;
            // Only units the supervisor still believes are live are candidates.
            // kFailed and kRecovering units are already past their crash, so a
            // dead process there is expected and must not be re-counted.
            if (record.state != RuntimeState::kRunning &&
                record.state != RuntimeState::kDegraded) {
                continue;
            }
            if (record.process && !record.process->IsAlive()) {
                ++record.restart_count;
                ApplyBudget(record);
                DegradeDirectDependents(record);
                ++transitioned;
            }
        }
        return transitioned;
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

    [[nodiscard]] bool HasRecord(UnitId id) const {
        return records_.find(id) != records_.end();
    }

    void DegradeDirectDependents(const UnitRecord& record) {
        for (const UnitId dependent_id : record.direct_dependents) {
            auto& dependent = GetRecord(dependent_id);
            if (dependent.state != RuntimeState::kFailed) {
                dependent.state = RuntimeState::kDegraded;
            }
        }
    }

    [[nodiscard]] UnitSnapshot MakeSnapshot(
        UnitId id,
        const UnitRecord& record) const
    {
        UnitSnapshot snap;
        snap.id = id;
        snap.state = record.state;
        snap.restart_count = record.restart_count;
        snap.restarts_in_window = record.restarts_in_window;
        snap.missed_heartbeats = record.missed_heartbeats;
        snap.max_restarts = record.max_restarts;
        snap.process_alive = record.process && record.process->IsAlive();
        return snap;
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

std::unique_ptr<IWorkerSupervisor> CreateWorkerSupervisor(
    std::uint32_t max_restarts,
    std::chrono::seconds restart_window)
{
    return std::make_unique<WorkerSupervisorImpl>(max_restarts, restart_window);
}

// ---------------------------------------------------------------------------
// WorkerWatchdog — host-owned liveness polling driver
// ---------------------------------------------------------------------------

class WorkerWatchdog::Impl {
public:
    Impl(IWorkerSupervisor& supervisor, std::chrono::milliseconds interval)
        : supervisor_(supervisor), interval_(interval) {}

    ~Impl() { Stop(); }

    void Start() {
        if (running_.exchange(true)) {
            return;  // Already running.
        }
        thread_ = std::thread([this] { Loop(); });
    }

    void Stop() {
        if (!running_.exchange(false)) {
            return;  // Not running.
        }
        {
            std::lock_guard lock(wake_mutex_);
        }
        wake_.notify_all();
        if (thread_.joinable()) {
            thread_.join();
        }
    }

    std::uint32_t PollOnce() { return supervisor_.PollProcessLiveness(); }

private:
    void Loop() {
        std::unique_lock lock(wake_mutex_);
        while (running_.load()) {
            supervisor_.PollProcessLiveness();
            wake_.wait_for(lock, interval_, [this] { return !running_.load(); });
        }
    }

    IWorkerSupervisor& supervisor_;
    std::chrono::milliseconds interval_;
    std::atomic<bool> running_{false};
    std::thread thread_;
    std::mutex wake_mutex_;
    std::condition_variable wake_;
};

WorkerWatchdog::WorkerWatchdog(
    IWorkerSupervisor& supervisor,
    std::chrono::milliseconds interval)
    : impl_(std::make_unique<Impl>(supervisor, interval))
{
}

WorkerWatchdog::~WorkerWatchdog() = default;

void WorkerWatchdog::Start() { impl_->Start(); }

void WorkerWatchdog::Stop() { impl_->Stop(); }

std::uint32_t WorkerWatchdog::PollOnce() { return impl_->PollOnce(); }

}  // namespace aetherflow::supervisor

# Aetherflow System Architecture

## Overview

Aetherflow is a high-performance controller adapter ecosystem utilizing a microkernel host to manage native plugins and out-of-process Python workers via gRPC and shared memory.

## System Architecture

```mermaid
flowchart TB
    User[User] --> UI["PySide6 UI Host Shell"]
    UI --> UIRouter[UI Router]
    UIRouter --> PluginLoader["Plugin Loader / Registry"]

    subgraph Host["Microkernel Host"]
        PluginLoader
        ServiceContainer["Service Container"]
        WorkerSupervisor["Worker Supervisor"]
        IPC["gRPC + Shared Memory"]
    end

    subgraph Plugins["Native Plugin Layer"]
        Input["Input Provider"]
        Output["Output Provider"]
        Capture["Capture Provider"]
    end

    subgraph Workers["Python Workers (uv)"]
        CV["CV Worker"]
        ML["Inference Worker"]
        Script["Script Worker"]
    end

    PluginLoader --> Plugins
    WorkerSupervisor --> Workers
    IPC <--> Workers
```

## Runtime Data Flow

```mermaid
sequenceDiagram
    participant HW as "Hardware (Controller/Camera)"
    participant Host as "Microkernel Host"
    participant Worker as "CV/Script Worker"
    participant Game as "Target Game"

    HW->>Host: Raw Input / Frame
    par Parallel Processing
        Host->>Host: Low-Latency Pass-through
        Host->>Worker: Dispatch Frame (Shared Memory)
    end
    Worker->>Host: Logic Result (gRPC)
    Host->>Game: Final Virtual Input
```

## Plugin Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Discovery: Scan /plugins
    Discovery --> Validation: Verify Manifest
    Validation --> Loading: Map DLL/Module
    Loading --> Initialized: on_load()
    Initialized --> Active: Register Services
    Active --> Terminating: on_unload()
    Terminating --> [*]
```

## Worker Execution Model

```mermaid
flowchart LR
    Start((Start)) --> Env["Check uv Environment"]
    Env --> Spawn["Spawn Python Subprocess"]
    Spawn --> Monitor{Health Check}
    Monitor -- Heartbeat OK --> Monitor
    Monitor -- "Timeout/Crash" --> Recovery["Restart Worker"]
    Recovery --> Spawn
```

# Native Host Boundary

All C++ runtime and bridge code belongs under `host/`. Public headers and ABI
contracts belong under repo-root `include/`.

`host/native_harness.cpp` is the Phase 0 contract harness. It validates the
frozen native header, confirms the control-plane proto is present, and enforces
the repository boundary by rejecting native source files under `src/`.

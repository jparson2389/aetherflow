---
description: Workflow to manage the UV python environment, sync dependencies, and handle packages
---

# `manage-uv` Workflow

This workflow provides standard commands and procedures for managing the `uv` python environment, installing dependencies, and ensuring the project stay synchronized.

## Commands & Steps

1. **Sync All Dependencies**: Ensure the environment is up to date with the `uv.lock` file, including `dev` and `automation` groups:

   ```powershell
   uv sync --all-groups
   ```

2. **Add a Core Dependency**: Add a new requirement for the main application (which will update `pyproject.toml` and `uv.lock`):

   ```powershell
   uv add <package_name>
   ```

3. **Add a Development Dependency**: Add a tool needed only for development (e.g., testing, linting):

   ```powershell
   uv add --group dev <package_name>
   ```

4. **Add an Automation Dependency**: Add a package needed for agent and automation workflows:

   ```powershell
   uv add --group automation <package_name>
   ```

5. **Upgrade Dependencies**: Update all packages to their latest compatible versions and sync:

   ```powershell
   uv lock --upgrade
   uv sync --all-groups
   ```

6. **Remove a Dependency**: Remove a previously installed package from the project:

   ```powershell
   uv remove <package_name>
   ```

7. **Clean the Environment**: If the environment falls out of sync or becomes corrupted, you can wipe it and recreate it:
   ```powershell
   Remove-Item -Recurse -Force .venv
   uv sync --all-groups
   ```

> [!IMPORTANT] The isolated `uv` environment ensures reproducible builds. Always prefix your standard execution commands with `uv run` (e.g., `uv run python -m aetherflow.main`, `uv run pytest`, `uv run ruff check .`) to run them within the correct environment context.

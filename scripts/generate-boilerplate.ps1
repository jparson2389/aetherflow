$ErrorActionPreference = "Stop"

Write-Host "🧱 Generating src-layout boilerplate..." -ForegroundColor Cyan

# Package root (src-layout)
New-Item -ItemType Directory -Force -Path `
    "src/aetherflow", `
    "src/aetherflow/core", `
    "src/aetherflow/ui", `
    "src/aetherflow/ui/panels", `
    "src/aetherflow/vision", `
    "src/aetherflow/input", `
    "src/aetherflow/output", `
    "src/aetherflow/plugins", `
    "proto", `
    "assets/ui", `
    "tests", `
    "docs", `
    "logs" | Out-Null

# __init__.py files
$initFiles = @(
    "src/aetherflow/__init__.py",
    "src/aetherflow/core/__init__.py",
    "src/aetherflow/ui/__init__.py",
    "src/aetherflow/ui/panels/__init__.py",
    "src/aetherflow/vision/__init__.py",
    "src/aetherflow/input/__init__.py",
    "src/aetherflow/output/__init__.py",
    "src/aetherflow/plugins/__init__.py"
)
$initFiles | ForEach-Object { New-Item -ItemType File -Force -Path $_ | Out-Null }

# Minimal entrypoint (optional, helps compileall)
New-Item -ItemType File -Force -Path "src/aetherflow/main.py" | Out-Null

Write-Host "✅ Boilerplate created." -ForegroundColor Green
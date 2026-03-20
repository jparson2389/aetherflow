$ErrorActionPreference = "Stop"

# Stop any running python processes to release file locks
Write-Host "Stopping Python processes..." -ForegroundColor Cyan
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue

# Deactivate current venv if active
if (Test-Path env:VIRTUAL_ENV) {
    Write-Host "Deactivating virtual environment..." -ForegroundColor Cyan
    deactivate 2>$null
}

# Remove the .venv folder
if (Test-Path ".venv") {
    Write-Host "Removing .venv directory..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force .venv
}

# Sync fresh environment
Write-Host "Running uv sync..." -ForegroundColor Green
uv sync --group dev --group automation

Write-Host "Environment Reset Complete!" -ForegroundColor Green
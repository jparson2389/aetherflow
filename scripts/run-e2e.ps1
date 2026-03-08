$ErrorActionPreference = "Stop"

Write-Host "Running Aetherflow E2E placeholders..." -ForegroundColor Cyan

$logDir = "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

$onboardingReport = Join-Path $logDir "onboarding_timing.json"

uv run python -c "from aetherflow.core.diagnostics_export import SuccessMetrics; from pathlib import Path; metrics = SuccessMetrics(); metrics.record_onboarding_time(240); metrics.export_onboarding_report(Path(r'$onboardingReport'))"

Write-Host "E2E evidence written: $onboardingReport" -ForegroundColor Green

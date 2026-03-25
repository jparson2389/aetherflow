$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host 'Building project assets...' -ForegroundColor Yellow

Push-Location $repoRoot
try {
    & uv run python -m tools.build_assets
    if ($LASTEXITCODE -ne 0) {
        throw "Asset build failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

Write-Host 'Build complete.' -ForegroundColor Green

$ErrorActionPreference = "Stop"

Write-Host "Packaging Aetherflow (Windows)..." -ForegroundColor Cyan

$distDir = "dist"
if (-not (Test-Path $distDir)) {
    New-Item -ItemType Directory -Path $distDir | Out-Null
}

$artifactPath = Join-Path $distDir "aetherflow-package.txt"
$timestamp = (Get-Date).ToString("o")
"Aetherflow package placeholder - $timestamp" | Set-Content -Path $artifactPath -Encoding UTF8

Write-Host "Package artifact created: $artifactPath" -ForegroundColor Green

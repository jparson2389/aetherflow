$ErrorActionPreference = "Stop"

Write-Host "Building Aetherflow native contract harness..." -ForegroundColor Cyan

$headerPath = "include/plugin_system.hpp"
$protoPath = "proto/capture.proto"
$hostPath = "host"

if (-not (Test-Path $headerPath)) {
    throw "Missing plugin_system.hpp contract."
}

if (-not (Test-Path $protoPath)) {
    throw "Missing capture.proto contract."
}

if (-not (Test-Path $hostPath)) {
    throw "Missing host/ boundary."
}

Write-Host "Validated native contract inputs:" -ForegroundColor Green
Write-Host " - $headerPath"
Write-Host " - $protoPath"
Write-Host " - $hostPath"
Write-Host "Native build harness placeholder completed."

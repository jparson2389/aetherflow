$ErrorActionPreference = "Stop"

Write-Host "Building Aetherflow native contract harness..." -ForegroundColor Cyan

$headerPath = "include/plugin_system.hpp"
$protoPath = "proto/capture.proto"
$hostPath = "host"
$sourcePath = "host/native_harness.cpp"
$buildDir = "build"
$outputPath = Join-Path $buildDir "native_harness.exe"
$vswherePath = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"

if (-not (Test-Path $headerPath)) {
    throw "Missing plugin_system.hpp contract."
}

if (-not (Test-Path $protoPath)) {
    throw "Missing capture.proto contract."
}

if (-not (Test-Path $hostPath)) {
    throw "Missing host/ boundary."
}

if (-not (Test-Path $sourcePath)) {
    throw "Missing native harness source."
}

if (-not (Test-Path $buildDir)) {
    New-Item -ItemType Directory -Path $buildDir | Out-Null
}

Write-Host "Validated native contract inputs:" -ForegroundColor Green
Write-Host " - $headerPath"
Write-Host " - $protoPath"
Write-Host " - $hostPath"

if (-not (Test-Path $vswherePath)) {
    throw "vswhere.exe not found. Install Visual Studio Build Tools."
}

$installPath = & $vswherePath -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath

if (-not $installPath) {
    throw "Visual Studio C++ tools not found."
}

$vcvarsPath = Join-Path $installPath "VC\Auxiliary\Build\vcvars64.bat"
if (-not (Test-Path $vcvarsPath)) {
    throw "vcvars64.bat not found under $installPath"
}

$compileCommand = "call `"$vcvarsPath`" >nul && cl.exe /nologo /EHsc /std:c++20 /I include /Fe`"$outputPath`" `"$sourcePath`""
$compileOutput = & cmd /c $compileCommand 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host $compileOutput
    throw "Native harness build failed."
}

Write-Host "Native harness build complete: $outputPath" -ForegroundColor Green

$ErrorActionPreference = "Stop"

Write-Host "Building Aetherflow native contract harness..." -ForegroundColor Cyan

$projectRoot = (Resolve-Path ".").Path
$headerPath = Join-Path $projectRoot "include\plugin_system.hpp"
$protoPath = Join-Path $projectRoot "proto\capture.proto"
$srcPath = Join-Path $projectRoot "src"
$hostPath = Join-Path $projectRoot "host"
$sourcePath = Join-Path $projectRoot "host\native_harness.cpp"
$buildDir = Join-Path $projectRoot "build"
$logsDir = Join-Path $projectRoot "logs"
$outputPath = Join-Path $buildDir "native_harness.exe"
$reportPath = Join-Path $buildDir "native_harness_report.json"
$buildLogPath = Join-Path $logsDir "native_harness_build.log"
$validationLogPath = Join-Path $logsDir "native_harness_validation.log"
$vswherePath = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"
$cmdPath = if ($env:ComSpec) {
    $env:ComSpec
} else {
    Join-Path $env:SystemRoot "System32\cmd.exe"
}

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

if (-not (Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

if (-not (Test-Path $srcPath)) {
    throw "Missing src/ tree for native boundary enforcement."
}

Write-Host "Validated native contract inputs:" -ForegroundColor Green
Write-Host " - $headerPath"
Write-Host " - $protoPath"
Write-Host " - $hostPath"
Write-Host " - $srcPath"

if (-not (Test-Path $vswherePath)) {
    throw "vswhere.exe not found. Install Visual Studio Build Tools."
}

if (-not (Test-Path $cmdPath)) {
    throw "cmd.exe not found."
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

$compileCommand = "call `"$vcvarsPath`" >nul && cl.exe /nologo /EHsc /std:c++20 /W4 /WX /I `"$($projectRoot)\include`" /Fo`"$buildDir\\`" /Fe`"$outputPath`" `"$sourcePath`""
$compileOutput = & $cmdPath /c $compileCommand 2>&1
$compileOutput | Set-Content -Path $buildLogPath
if ($LASTEXITCODE -ne 0) {
    Write-Host $compileOutput
    throw "Native harness build failed. See $buildLogPath"
}

$validationOutput = & $outputPath `
    --repo-root $projectRoot `
    --header $headerPath `
    --proto $protoPath `
    --output $reportPath 2>&1
$validationOutput | Set-Content -Path $validationLogPath
if ($LASTEXITCODE -ne 0) {
    Write-Host $validationOutput
    throw "Native harness validation failed. See $validationLogPath"
}

Write-Host "Native harness build complete: $outputPath" -ForegroundColor Green
Write-Host "Native harness validation report: $reportPath" -ForegroundColor Green

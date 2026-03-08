$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path "$PSScriptRoot\.."
$logDir = Join-Path $projectRoot "logs"
$reportPath = Join-Path $logDir "env_report.json"

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}

function Get-CommandInfo {
    param(
        [string]$Name,
        [string[]]$VersionArgs
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        return @{
            available = $false
            path = $null
            version = $null
            error = "$Name not found"
        }
    }

    $versionOutput = $null
    $versionError = $null
    try {
        $versionOutput = & $Name @VersionArgs 2>&1
    } catch {
        $versionError = $_.Exception.Message
    }

    return @{
        available = $versionError -eq $null
        path = $command.Path
        version = $versionOutput
        error = $versionError
    }
}

$vswherePath = Join-Path ${env:ProgramFiles(x86)} "Microsoft Visual Studio\Installer\vswhere.exe"

function Get-ClInfo {
    $command = Get-Command "cl.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return Get-CommandInfo -Name "cl.exe" -VersionArgs @()
    }

    if (-not (Test-Path $vswherePath)) {
        return @{
            available = $false
            path = $null
            version = $null
            error = "cl.exe not found and vswhere.exe missing"
        }
    }

    $installPath = & $vswherePath -latest -products * `
        -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
        -property installationPath

    if (-not $installPath) {
        return @{
            available = $false
            path = $null
            version = $null
            error = "Visual Studio C++ tools not found"
        }
    }

    $vcvarsPath = Join-Path $installPath "VC\Auxiliary\Build\vcvars64.bat"
    if (-not (Test-Path $vcvarsPath)) {
        return @{
            available = $false
            path = $null
            version = $null
            error = "vcvars64.bat not found under $installPath"
        }
    }

    $whereOutput = & cmd /c "call `"$vcvarsPath`" >nul && where cl.exe"
    if (-not $whereOutput) {
        return @{
            available = $false
            path = $null
            version = $null
            error = "cl.exe not found after vcvars64.bat"
        }
    }

    $versionOutput = & cmd /c "call `"$vcvarsPath`" >nul && cl.exe 2>&1"
    return @{
        available = $true
        path = ($whereOutput | Select-Object -First 1)
        version = ($versionOutput | Select-String -Pattern "Version" | Select-Object -First 1).Line
        error = $null
    }
}

$uvInfo = Get-CommandInfo -Name "uv" -VersionArgs @("--version")
$pythonInfo = Get-CommandInfo -Name "python" -VersionArgs @("--version")
$powershellInfo = @{
    available = $true
    path = $PSHOME
    version = $PSVersionTable.PSVersion.ToString()
    error = $null
}
$clInfo = Get-ClInfo

$report = @{
    timestamp = (Get-Date).ToString("o")
    uv = $uvInfo
    python = $pythonInfo
    powershell = $powershellInfo
    cl = $clInfo
}

$reportJson = $report | ConvertTo-Json -Depth 4
[System.IO.File]::WriteAllText(
    $reportPath,
    $reportJson,
    [System.Text.UTF8Encoding]::new($false)
)

if (-not $uvInfo.available -or -not $pythonInfo.available -or -not $clInfo.available) {
    Write-Error "Environment verification failed. See $reportPath"
    exit 1
}

Write-Output "Environment verification passed. Report: $reportPath"

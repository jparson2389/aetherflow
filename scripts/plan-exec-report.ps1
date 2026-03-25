param(
    [string]$LogFilePath
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    $cmdArgs = @('run', 'python', '-m', 'tools.plan_exec_report')
    if (-not [string]::IsNullOrWhiteSpace($LogFilePath)) {
        $cmdArgs += '--log-file-path'
        $cmdArgs += $LogFilePath
    }

    & uv @cmdArgs
    if ($LASTEXITCODE -ne 0) {
        throw "plan-exec-report failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

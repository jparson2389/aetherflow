param(
    [string]$LogFilePath
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    $args = @('run', 'python', 'tools/plan_exec_report.py')
    if (-not [string]::IsNullOrWhiteSpace($LogFilePath)) {
        $args += '--log-file-path'
        $args += $LogFilePath
    }

    & uv @args
    if ($LASTEXITCODE -ne 0) {
        throw "plan-exec-report failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

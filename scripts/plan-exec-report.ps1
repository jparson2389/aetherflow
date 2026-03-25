param(
    [string]$LogFilePath
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

$uvArgs = @('run', '--project', $repoRoot, 'python', (Join-Path $repoRoot 'tools/plan_exec_report.py'))
if (-not [string]::IsNullOrWhiteSpace($LogFilePath)) {
    $uvArgs += '--log-file-path'
    $uvArgs += $LogFilePath
}

& uv @uvArgs
if ($LASTEXITCODE -ne 0) {
    throw "plan-exec-report failed with exit code $LASTEXITCODE."
}

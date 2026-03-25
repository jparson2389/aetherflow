param(
    [switch]$Debug
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    $cmdArgs = @('run', 'python', '-m', 'tools.verify_requirements')
    if ($Debug) {
        $cmdArgs += '--debug'
    }

    & uv @cmdArgs
    if ($LASTEXITCODE -ne 0) {
        throw "verify-requirements failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

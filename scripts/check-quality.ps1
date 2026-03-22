param(
    [string[]]$Paths = @()
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    $args = @('run', 'python', '-m', 'tools.check_quality')
    if ($Paths.Count -gt 0) {
        $args += '--paths'
        $args += $Paths
    }

    & uv @args
    if ($LASTEXITCODE -ne 0) {
        throw "Quality gate failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-ManifestConfig {
    param(
        [string]$RepoRoot
    )

    $manifestPath = Join-Path $RepoRoot 'agent_manifest.json'
    if (-not (Test-Path $manifestPath)) {
        throw "Manifest file not found: $manifestPath"
    }

    return Get-Content -Path $manifestPath -Raw | ConvertFrom-Json
}

function Get-ServerRootUrl {
    param(
        [string]$BaseUrl
    )

    $trimmed = $BaseUrl.TrimEnd('/')
    if ($trimmed.EndsWith('/v1')) {
        return $trimmed.Substring(0, $trimmed.Length - 3)
    }

    return $trimmed
}

function Get-PresetAliasConfig {
    param(
        [string]$PresetPath,
        [string[]]$Aliases
    )

    $config = @{}
    foreach ($alias in $Aliases) {
        $config[$alias] = @{}
    }

    $currentSection = ''
    foreach ($rawLine in Get-Content -Path $PresetPath) {
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith(';') -or $line.StartsWith('#')) {
            continue
        }

        if ($line -match '^\[(.+)\]$') {
            $currentSection = $Matches[1].Trim()
            continue
        }

        if (-not $config.ContainsKey($currentSection)) {
            continue
        }

        $parts = $line -split '=', 2
        if ($parts.Count -ne 2) {
            continue
        }

        $key = $parts[0].Trim().ToLowerInvariant()
        $value = $parts[1].Trim()
        switch ($key) {
            'model' {
                $config[$currentSection]['Model'] = $value
            }
            'model-draft' {
                $config[$currentSection]['ModelDraft'] = $value
            }
            'ctx-size' {
                $config[$currentSection]['CtxSize'] = $value
            }
            'jinja' {
                $config[$currentSection]['Jinja'] = $value -match '^(on|true|1|yes)$'
            }
            'chat-template' {
                $config[$currentSection]['ChatTemplate'] = $value
            }
        }
    }

    return $config
}

function Get-ArgumentValue {
    param(
        [object[]]$ArgsList,
        [string]$Flag
    )

    for ($index = 0; $index -lt $ArgsList.Count; $index++) {
        if ([string]$ArgsList[$index] -ne $Flag) {
            continue
        }

        if (($index + 1) -lt $ArgsList.Count) {
            return [string]$ArgsList[$index + 1]
        }
    }

    return $null
}

function Test-ArgumentSwitch {
    param(
        [object[]]$ArgsList,
        [string]$Flag
    )

    foreach ($arg in $ArgsList) {
        if ([string]$arg -eq $Flag) {
            return $true
        }
    }

    return $false
}

function Get-ActualAliasConfig {
    param(
        [object]$Model
    )

    $argsList = @()
    if ($null -ne $Model.status) {
        $hasArgs = $Model.status.PSObject.Properties.Match('args').Count -gt 0
        if ($hasArgs -and $null -ne $Model.status.args) {
            $argsList = @($Model.status.args)
        }
    }

    return [pscustomobject]@{
        Model      = Get-ArgumentValue -ArgsList $argsList -Flag '--model'
        ModelDraft = Get-ArgumentValue -ArgsList $argsList -Flag '--model-draft'
        CtxSize    = Get-ArgumentValue -ArgsList $argsList -Flag '--ctx-size'
        Jinja      = Test-ArgumentSwitch -ArgsList $argsList -Flag '--jinja'
        ChatTemplate = Get-ArgumentValue -ArgsList $argsList -Flag '--chat-template'
    }
}

function Get-MismatchedAliases {
    param(
        [object[]]$Models,
        [string[]]$Aliases,
        [hashtable]$ExpectedAliasConfig
    )

    $mismatched = @()
    foreach ($alias in $Aliases) {
        if (-not $ExpectedAliasConfig.ContainsKey($alias)) {
            continue
        }

        $model = $Models | Where-Object { [string]$_.id -eq $alias } |
            Select-Object -First 1
        if ($null -eq $model) {
            continue
        }

        $expected = $ExpectedAliasConfig[$alias]
        $actual = Get-ActualAliasConfig -Model $model

        if ($expected.ContainsKey('Model') -and $actual.Model -ne $expected['Model']) {
            $mismatched += $alias
            continue
        }

        if (
            $expected.ContainsKey('ModelDraft') -and
            $actual.ModelDraft -ne $expected['ModelDraft']
        ) {
            $mismatched += $alias
            continue
        }

        if ($expected.ContainsKey('CtxSize') -and $actual.CtxSize -ne $expected['CtxSize']) {
            $mismatched += $alias
            continue
        }

        if ($expected.ContainsKey('Jinja') -and $actual.Jinja -ne $expected['Jinja']) {
            $mismatched += $alias
            continue
        }

        if (
            $expected.ContainsKey('ChatTemplate') -and
            $actual.ChatTemplate -ne $expected['ChatTemplate']
        ) {
            $mismatched += $alias
        }
    }

    return @($mismatched)
}

function Wait-ForServerHealth {
    param(
        [string]$ServerRootUrl,
        [int]$Attempts = 30,
        [int]$DelaySeconds = 2
    )

    $healthUrl = "$ServerRootUrl/health"
    for ($attempt = 0; $attempt -lt $Attempts; $attempt++) {
        Start-Sleep -Seconds $DelaySeconds
        try {
            $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                return $true
            }
        }
        catch {
        }
    }

    return $false
}

function Invoke-JsonEndpoint {
    param(
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest `
            -Uri $Url `
            -UseBasicParsing `
            -SkipHttpErrorCheck `
            -ErrorAction Stop
        $content = [string]$response.Content
        $statusCode = [int]$response.StatusCode

        if ([string]::IsNullOrWhiteSpace($content)) {
            return [pscustomobject]@{
                IsSuccess  = $false
                Url        = $Url
                StatusCode = $statusCode
                Content    = ''
                Json       = $null
                Error      = 'Empty response body.'
            }
        }

        try {
            $json = $content | ConvertFrom-Json -ErrorAction Stop
            return [pscustomobject]@{
                IsSuccess  = ($statusCode -ge 200 -and $statusCode -lt 300)
                Url        = $Url
                StatusCode = $statusCode
                Content    = $content
                Json       = $json
                Error      = $null
            }
        }
        catch {
            return [pscustomobject]@{
                IsSuccess  = $false
                Url        = $Url
                StatusCode = $statusCode
                Content    = $content
                Json       = $null
                Error      = $_.Exception.Message
            }
        }
    }
    catch {
        return [pscustomobject]@{
            IsSuccess  = $false
            Url        = $Url
            StatusCode = 0
            Content    = ''
            Json       = $null
            Error      = $_.Exception.Message
        }
    }
}

function Get-AvailableModels {
    param(
        [string]$ServerRootUrl
    )

    $candidateUrls = @(
        "$ServerRootUrl/models",
        "$ServerRootUrl/v1/models"
    )

    $lastResult = $null
    foreach ($url in $candidateUrls) {
        $result = Invoke-JsonEndpoint -Url $url
        $lastResult = $result
        if (-not $result.IsSuccess -or $null -eq $result.Json) {
            continue
        }

        $models = @()
        if ($result.Json -is [System.Array]) {
            $models = @($result.Json)
        }
        elseif ($result.Json.PSObject.Properties.Match('data').Count -gt 0) {
            $models = @($result.Json.data)
        }
        elseif ($result.Json.PSObject.Properties.Match('models').Count -gt 0) {
            $models = @($result.Json.models)
        }

        return [pscustomobject]@{
            Models     = $models
            Url        = $result.Url
            StatusCode = $result.StatusCode
            Content    = $result.Content
            Error      = $result.Error
        }
    }

    return [pscustomobject]@{
        Models     = @()
        Url        = if ($null -ne $lastResult) { $lastResult.Url } else { $candidateUrls[0] }
        StatusCode = if ($null -ne $lastResult) { $lastResult.StatusCode } else { 0 }
        Content    = if ($null -ne $lastResult) { $lastResult.Content } else { '' }
        Error      = if ($null -ne $lastResult) { $lastResult.Error } else { 'No response received.' }
    }
}

function Wait-ForAliasInventory {
    param(
        [string]$ServerRootUrl,
        [string[]]$RequiredAliases,
        [hashtable]$ExpectedAliasConfig = @{},
        [int]$Attempts = 15,
        [int]$DelaySeconds = 2
    )

    $lastModels = @()
    $lastMismatched = @()
    $lastProbeUrl = ''
    $lastProbeStatusCode = 0
    $lastProbeError = ''
    $lastProbeContent = ''
    for ($attempt = 0; $attempt -lt $Attempts; $attempt++) {
        Start-Sleep -Seconds $DelaySeconds
        $probe = Get-AvailableModels -ServerRootUrl $ServerRootUrl
        $lastProbeUrl = [string]$probe.Url
        $lastProbeStatusCode = [int]$probe.StatusCode
        $lastProbeError = [string]$probe.Error
        $lastProbeContent = [string]$probe.Content

        $models = @($probe.Models)
        $ids = @($models | ForEach-Object { [string]$_.id })
        $missing = @($RequiredAliases | Where-Object { $_ -notin $ids })
        $mismatched = @()
        if ($missing.Count -eq 0 -and $ExpectedAliasConfig.Count -gt 0) {
            $mismatched = @(Get-MismatchedAliases `
                -Models $models `
                -Aliases $RequiredAliases `
                -ExpectedAliasConfig $ExpectedAliasConfig)
        }

        if ($missing.Count -eq 0 -and $mismatched.Count -eq 0) {
            return [pscustomobject]@{
                IsValid       = $true
                Missing       = @()
                Mismatched    = @()
                Models        = $models
                SeenIds       = $ids
                ProbeUrl      = $lastProbeUrl
                ProbeStatus   = $lastProbeStatusCode
                ProbeError    = $lastProbeError
                ProbeContent  = $lastProbeContent
            }
        }

        $lastModels = $models
        $lastMismatched = $mismatched
    }

    $lastIds = @($lastModels | ForEach-Object { [string]$_.id })
    $lastMissing = @($RequiredAliases | Where-Object { $_ -notin $lastIds })
    return [pscustomobject]@{
        IsValid       = $false
        Missing       = $lastMissing
        Mismatched    = $lastMismatched
        Models        = $lastModels
        SeenIds       = $lastIds
        ProbeUrl      = $lastProbeUrl
        ProbeStatus   = $lastProbeStatusCode
        ProbeError    = $lastProbeError
        ProbeContent  = $lastProbeContent
    }
}

function Get-PortOwnerProcess {
    param(
        [int]$Port
    )

    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($null -eq $connection) {
        return $null
    }

    return Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
}

function Write-AliasSummary {
    param(
        [object[]]$Models,
        [string[]]$Aliases
    )

    Write-Host 'Active alias inventory:' -ForegroundColor Cyan
    foreach ($alias in $Aliases) {
        $model = $Models | Where-Object { [string]$_.id -eq $alias } | Select-Object -First 1
        if ($null -eq $model) {
            Write-Host "  $alias -> missing" -ForegroundColor Red
            continue
        }

        $status = 'unknown'
        if ($null -ne $model.status -and $null -ne $model.status.value) {
            $status = [string]$model.status.value
        }

        $path = ''
        $hasPath = $model.PSObject.Properties.Match('path').Count -gt 0
        if ($hasPath -and $null -ne $model.path) {
            $path = [string]$model.path
        }
        elseif ($null -ne $model.status) {
            $hasArgs = $model.status.PSObject.Properties.Match('args').Count -gt 0
            if ($hasArgs -and $null -ne $model.status.args) {
                $argsList = @($model.status.args)
                $modelArgIndex = [Array]::IndexOf($argsList, '--model')
                if ($modelArgIndex -ge 0 -and ($modelArgIndex + 1) -lt $argsList.Count) {
                    $path = [string]$argsList[$modelArgIndex + 1]
                }
            }
        }

        if ([string]::IsNullOrWhiteSpace($path)) {
            $path = '<router-managed>'
        }

        Write-Host "  $alias -> $status -> $path" -ForegroundColor Green
    }
}

function Get-ContentPreview {
    param(
        [string]$Content,
        [int]$MaxLength = 400
    )

    if ([string]::IsNullOrWhiteSpace($Content)) {
        return '<empty>'
    }

    $singleLine = ($Content -replace '\s+', ' ').Trim()
    if ($singleLine.Length -le $MaxLength) {
        return $singleLine
    }

    return $singleLine.Substring(0, $MaxLength) + '...'
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifest = Get-ManifestConfig -RepoRoot $repoRoot
$presetPath = Resolve-Path (Join-Path $repoRoot $manifest.model_preset_path)
$requiredAliases = @($manifest.required_aliases | ForEach-Object { [string]$_ })
$optionalAliases = @($manifest.optional_aliases | ForEach-Object { [string]$_ })
$expectedAliasConfig = Get-PresetAliasConfig `
    -PresetPath ([string]$presetPath) `
    -Aliases ($requiredAliases + $optionalAliases)
$baseUrl = [string]$manifest.base_url
$serverRootUrl = Get-ServerRootUrl -BaseUrl $baseUrl
$uri = [Uri]$baseUrl
$port = $uri.Port
$hostAddress = $uri.Host
$llamaExe = 'C:\Users\Dada\AI_Tools\llama.cpp\build\bin\Release\llama-server.exe'

Write-Host 'Initializing Aetherflow...' -ForegroundColor Cyan

if (-not (Test-Path $llamaExe)) {
    throw "llama-server executable not found: $llamaExe"
}

if (-not (Test-Path $presetPath)) {
    throw "Preset file not found: $presetPath"
}

uv sync --group dev --group automation

$owner = Get-PortOwnerProcess -Port $port
if ($null -ne $owner) {
    if ($owner.ProcessName -ne 'llama-server') {
        throw "Port $port is already in use by '$($owner.ProcessName)'."
    }

    Write-Host 'Existing llama-server detected. Validating alias inventory...' -ForegroundColor Yellow
    $healthy = Wait-ForServerHealth -ServerRootUrl $serverRootUrl -Attempts 5 -DelaySeconds 1
    if ($healthy) {
        $inventory = Wait-ForAliasInventory `
            -ServerRootUrl $serverRootUrl `
            -RequiredAliases $requiredAliases `
            -ExpectedAliasConfig $expectedAliasConfig `
            -Attempts 3 `
            -DelaySeconds 1
        if ($inventory.IsValid) {
            Write-Host "llama-server already active on port $port and matches expected aliases." -ForegroundColor Green
            Write-AliasSummary -Models $inventory.Models -Aliases ($requiredAliases + $optionalAliases)
            exit 0
        }
    }

    Write-Host 'Existing llama-server does not match the repo-local preset. Restarting...' -ForegroundColor Yellow
    Stop-Process -Id $owner.Id -Force
    Start-Sleep -Seconds 2
}

Write-Host 'Starting llama-server (single-model router mode)...' -ForegroundColor Cyan
$llamaArgs = @(
    '--models-preset', [string]$presetPath,
    '--models-max', '1',
    '--parallel', '1',
    '--host', $hostAddress,
    '--port', [string]$port
)

$process = Start-Process -FilePath $llamaExe -ArgumentList $llamaArgs -WindowStyle Normal -PassThru

Write-Host 'Waiting for llama-server health endpoint...' -ForegroundColor Yellow
$ready = Wait-ForServerHealth -ServerRootUrl $serverRootUrl -Attempts 30 -DelaySeconds 2
if (-not $ready) {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
    throw 'llama-server did not respond on /health within 60 seconds.'
}

Write-Host 'Validating alias inventory from /models...' -ForegroundColor Yellow
$inventory = Wait-ForAliasInventory `
    -ServerRootUrl $serverRootUrl `
    -RequiredAliases $requiredAliases `
    -ExpectedAliasConfig $expectedAliasConfig `
    -Attempts 45 `
    -DelaySeconds 2
if (-not $inventory.IsValid) {
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }
    $failureMessages = @()
    if ($inventory.Missing.Count -gt 0) {
        $failureMessages += "missing aliases: $($inventory.Missing -join ', ')"
    }
    if ($inventory.Mismatched.Count -gt 0) {
        $failureMessages += "preset drift: $($inventory.Mismatched -join ', ')"
    }
    if ($inventory.SeenIds.Count -gt 0) {
        $failureMessages += "seen ids: $($inventory.SeenIds -join ', ')"
    }
    if ($inventory.ProbeStatus -gt 0) {
        $failureMessages += "probe status: $($inventory.ProbeStatus)"
    }
    if (-not [string]::IsNullOrWhiteSpace($inventory.ProbeUrl)) {
        $failureMessages += "probe url: $($inventory.ProbeUrl)"
    }
    if (-not [string]::IsNullOrWhiteSpace($inventory.ProbeError)) {
        $failureMessages += "probe error: $($inventory.ProbeError)"
    }
    $failureMessages += "probe body: $(Get-ContentPreview -Content ([string]$inventory.ProbeContent))"
    $failureText = $failureMessages -join '; '
    throw "llama-server started, but validation failed: $failureText"
}

Write-Host "llama-server ready on $baseUrl" -ForegroundColor Green
Write-AliasSummary -Models $inventory.Models -Aliases ($requiredAliases + $optionalAliases)

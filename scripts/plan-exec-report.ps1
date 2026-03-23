param(
    [string]$LogFilePath)
$ErrorActionPreference = "Stop"
if (!(Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}
# Resolve the plan execution log to inspect.
if ([string]::IsNullOrWhiteSpace($LogFilePath)) {
    $logCandidates = Get-ChildItem -Path "logs" -Filter "plan_execution_*.log" |
        Sort-Object LastWriteTime -Descending
    if (-not $logCandidates) {
        throw "No plan_execution_*.log files found under logs/."
    }
    $planLogPath = $logCandidates[0].FullName
} else {
    if (-not (Test-Path $LogFilePath)) {
        throw "Specified LogFilePath '$LogFilePath' does not exist."
    }
    $planLogPath = (Resolve-Path $LogFilePath).Path
}
Write-Host "Analyzing plan execution log: $planLogPath" -ForegroundColor Cyan
$reportPath = Join-Path "logs" "plan_exec_report_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').md"
# Extract high-signal lines from the plan execution log.
$logLines = Get-Content -Path $planLogPath
$timestampPattern = '^(?<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \|'
$runTimestamps = @(
    $logLines |
        ForEach-Object {
            if ($_ -match $timestampPattern) {
                $matches['ts']
            }
        })
$runWindow = '(no timestamps found)'
if ($runTimestamps.Count -gt 0) {
    $runWindow = "$($runTimestamps[0]) -> $($runTimestamps[-1])"
}
$stateLines = $logLines | Where-Object { $_ -match '\[state\]' }
$summaryLines = $logLines | Where-Object { $_ -match 'Execution Summary \|' }
$errorLines = $logLines | Where-Object { $_ -match '\sERROR\s' }
$warningLines = $logLines | Where-Object { $_ -match '\sWARNING\s' }
$pmFailureLines = $logLines | Where-Object { $_ -match 'PM verify failed' -or $_ -match '\[pm_next\]' }
# Determine overall status.
$status = "Success"
$statusReason = "No ERROR lines detected in plan execution log."
if ($errorLines.Count -gt 0) {
    $status = "Failed"
    $statusReason = $errorLines[-1]
} elseif ($pmFailureLines.Count -gt 0) {
    $status = "Partial"
    $statusReason = $pmFailureLines[-1]
}
# Snapshot git changes to describe what plan_exec modified.
$gitStatus = @()
$insideGitRepo = $false
try {
    & git rev-parse --is-inside-work-tree 1>$null 2>$null
    $insideGitRepo = $LASTEXITCODE -eq 0
} catch {
    $insideGitRepo = $false
}
if ($insideGitRepo) {
    $gitStatus = git status --porcelain 2>$null
}
$added = @()
$modified = @()
$deleted = @()
foreach ($line in $gitStatus) {
    if (-not $line) { continue }
    # Format: XY <path>
    $statusCode = $line.Substring(0, 2)
    $path = $line.Substring(3).Trim()
    switch -regex ($statusCode) {
        '^\?\?' { $added += $path; break }
        'A'     { $added += $path; break }
        'D'     { $deleted += $path; break }
        default { $modified += $path; break }
    }
}
function Format-SectionList([string]$title, [string[]]$items) {
    if ($items.Count -eq 0) {
        return @("### $title", "", "- (none)", "")
    }
    $lines = @("### $title", "")
    foreach ($i in $items | Sort-Object -Unique) {
        $lines += "- $i"
    }
    $lines += ""
    return $lines
}
$reportLines = @()
$reportLines += "# Plan Execution Report"
$reportLines += ""
$reportLines += "Generated: $(Get-Date -Format o)"
$reportLines += "Source log: $planLogPath"
$reportLines += "Log file: $([System.IO.Path]::GetFileName($planLogPath))"
$reportLines += "Run window: $runWindow"
$reportLines += ""
$reportLines += "## Overall Status"
$reportLines += ""
$reportLines += "- **Status**: $status"
$reportLines += "- **Reason**: $statusReason"
$reportLines += ""
$reportLines += "## Plan State Snapshots"
$reportLines += ""
if ($stateLines.Count -gt 0) {
    foreach ($line in $stateLines) {
        $reportLines += "- $line"
    }
} else {
    $reportLines += "- (no [state] lines found)"
}
$reportLines += ""
$reportLines += "## Execution Summaries"
$reportLines += ""
if ($summaryLines.Count -gt 0) {
    foreach ($line in $summaryLines) {
        $reportLines += "- $line"
    }
} else {
    $reportLines += "- (no Execution Summary lines found)"
}
$reportLines += ""
$reportLines += "## Warnings And Errors"
$reportLines += ""
if ($warningLines.Count -gt 0) {
    $reportLines += "### Warnings"
    $reportLines += ""
    foreach ($line in $warningLines) {
        $reportLines += "- $line"
    }
    $reportLines += ""
}
if ($errorLines.Count -gt 0) {
    $reportLines += "### Errors"
    $reportLines += ""
    foreach ($line in $errorLines) {
        $reportLines += "- $line"
    }
    $reportLines += ""
}
$reportLines += Format-SectionList -title "New Files (Untracked/Added)" -items $added
$reportLines += Format-SectionList -title "Modified Files" -items $modified
$reportLines += Format-SectionList -title "Deleted Files" -items $deleted
$reportLines | Out-File -FilePath $reportPath -Encoding utf8
Write-Host "Wrote plan execution report to $reportPath" -ForegroundColor Green

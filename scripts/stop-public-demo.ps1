<#
.SYNOPSIS
    Stop leftover processes from a previous .\scripts\start-public-demo.ps1 run.

.DESCRIPTION
    start-public-demo.ps1 stops the frontend and the tunnel itself when it exits,
    so this script is only needed when that window was killed hard (closed with
    the X button, machine crash) and left the dev server holding port 5173.

    It reads the process list recorded by the start script and stops only those
    processes, and only when the recorded name and start time still match the
    running process, so a reused PID belonging to something else is left alone.
    It never sweeps node / python / cloudflared by name.

.EXAMPLE
    .\scripts\stop-public-demo.ps1
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$stateFile = Join-Path (Join-Path $env:TEMP "accounting-ai-public-demo") "state.json"

if (-not (Test-Path $stateFile)) {
    Write-Host "No public demo state file found at $stateFile - nothing to stop." -ForegroundColor Yellow
    Write-Host "If a dev server is still holding a port, find it with:" -ForegroundColor Yellow
    Write-Host "    Get-NetTCPConnection -LocalPort 5173 | Select-Object OwningProcess" -ForegroundColor Yellow
    return
}

$state = Get-Content $stateFile -Raw | ConvertFrom-Json
$stopped = 0

foreach ($record in @($state.processes)) {
    $process = Get-Process -Id $record.id -ErrorAction SilentlyContinue

    if (-not $process) {
        Write-Host "pid $($record.id) ($($record.name)) is already gone." -ForegroundColor DarkGray
        continue
    }

    # PIDs are reused. Only stop a process that is still the one we started.
    $recordedStart = [datetime]::Parse($record.startTimeUtc).ToUniversalTime()
    $actualStart = $process.StartTime.ToUniversalTime()

    if ($process.ProcessName -ne $record.name -or [math]::Abs(($actualStart - $recordedStart).TotalSeconds) -gt 2) {
        Write-Host "pid $($record.id) is now '$($process.ProcessName)' started $actualStart - not ours, skipping." -ForegroundColor Yellow
        continue
    }

    Stop-Process -Id $process.Id -Force
    Write-Host "Stopped $($process.ProcessName) (pid $($process.Id))." -ForegroundColor Green
    $stopped++
}

Remove-Item $stateFile -Force -ErrorAction SilentlyContinue

Write-Host "Stopped $stopped process(es)." -ForegroundColor Green
Write-Host "The backend runs in the start script's own window; close it or press Ctrl+C there." -ForegroundColor Cyan

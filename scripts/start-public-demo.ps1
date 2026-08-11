<#
.SYNOPSIS
    Start a temporary, free, one-link public demo of the app from this machine.

.DESCRIPTION
    Serves the whole demo behind a single Cloudflare Quick Tunnel URL:

        https://<random>.trycloudflare.com        -> Vite dev server (the UI)
        https://<random>.trycloudflare.com/api/*  -> Vite proxy -> backend on 127.0.0.1

    Because the browser only ever sees one origin there is no CORS to configure
    and no second link to hand out.

    The frontend and the tunnel run as background processes with their output
    redirected to log files.  The script waits for the tunnel to print its URL,
    then runs the backend in this window so Ctrl+C stops the demo and backend
    logs stay visible.  On exit the background processes are stopped.

    THIS IS NOT PRODUCTION HOSTING.  The URL changes on every run, the tunnel
    dies with this window, and the laptop has to stay awake.  Use a real VPS and
    domain for anything a paying client depends on.

    Nothing is written to backend\.env or frontend\.env.  APP_PUBLIC_URL and the
    frontend API base are set on the child processes only.

.PARAMETER BackendPort
    Local port for Uvicorn. Default 8010.

.PARAMETER FrontendPort
    Local port for the Vite dev server. Default 5173.

.PARAMETER NoOpen
    Do not open the public URL in the default browser.

.PARAMETER PublicUrl
    Use an already-running public URL (named tunnel, reverse proxy, real domain)
    instead of starting a Cloudflare Quick Tunnel. Whatever serves this URL must
    forward to the frontend port.

.PARAMETER SkipMigrations
    Skip 'alembic upgrade head' before starting the backend.

.EXAMPLE
    .\scripts\start-public-demo.ps1

.EXAMPLE
    .\scripts\start-public-demo.ps1 -PublicUrl https://demo.example.com -NoOpen
#>

[CmdletBinding()]
param(
    [int]$BackendPort = 8010,
    [int]$FrontendPort = 5173,
    [switch]$NoOpen,
    [string]$PublicUrl,
    [switch]$SkipMigrations
)

$ErrorActionPreference = "Stop"

$CloudflaredInstallHint = "winget install -e --id Cloudflare.cloudflared --accept-package-agreements --accept-source-agreements"
$TunnelUrlPattern = 'https://[a-z0-9-]+\.trycloudflare\.com'
$TunnelUrlTimeoutSeconds = 60
$FrontendReadyTimeoutSeconds = 120

function Write-Step { param([string]$Message) Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Ok { param([string]$Message) Write-Host "    $Message" -ForegroundColor Green }
function Write-Warn { param([string]$Message) Write-Host "    $Message" -ForegroundColor Yellow }

# Windows PowerShell 5.1 wraps a native command's stderr in an error record, and
# under $ErrorActionPreference = 'Stop' that aborts the script on the first line
# uvicorn or alembic logs whenever output is redirected or piped. Native commands
# are therefore run with the preference relaxed and their exit code checked.
function Invoke-Native {
    param([scriptblock]$Command, [string]$FailureMessage)

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $Command
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if ($FailureMessage -and $LASTEXITCODE -ne 0) {
        Write-Error "$FailureMessage (exit code $LASTEXITCODE)"
    }
}

function Test-PortOpen {
    param([string]$TargetHost, [int]$Port)

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $client.Connect($TargetHost, $Port)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Wait-ForPort {
    param([string]$TargetHost, [int]$Port, [int]$TimeoutSeconds, [System.Diagnostics.Process]$Process)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if ($Process -and $Process.HasExited) { return $false }
        if (Test-PortOpen -TargetHost $TargetHost -Port $Port) { return $true }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

# Log files are still open for writing by the child process, so they are read
# with an explicit share mode rather than through Get-Content.
function Read-LiveLog {
    param([string]$Path)

    if (-not (Test-Path $Path)) { return "" }

    $stream = $null
    $reader = $null
    try {
        $stream = [System.IO.File]::Open(
            $Path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite)
        $reader = New-Object System.IO.StreamReader($stream)
        return $reader.ReadToEnd()
    }
    catch {
        return ""
    }
    finally {
        if ($reader) { $reader.Dispose() }
        elseif ($stream) { $stream.Dispose() }
    }
}

function Write-LogTail {
    param([string[]]$Paths, [int]$Lines = 20)

    foreach ($path in $Paths) {
        $text = Read-LiveLog -Path $path
        if (-not $text) { continue }
        $tail = ($text -split "`r?`n" | Where-Object { $_ -ne "" } | Select-Object -Last $Lines)
        foreach ($line in $tail) { Write-Host "      $line" -ForegroundColor DarkYellow }
    }
}

# --------------------------------------------------------------------------
# 1. Locate the repository and check prerequisites
# --------------------------------------------------------------------------

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot "backend"
$frontendRoot = Join-Path $repoRoot "frontend"
$activateScript = Join-Path $backendRoot ".venv\Scripts\Activate.ps1"
$viteEntryPoint = Join-Path $frontendRoot "node_modules\vite\bin\vite.js"

if (-not (Test-Path (Join-Path $frontendRoot "package.json"))) {
    Write-Error "Could not locate the repository from $PSScriptRoot. Run this script from the checkout, as .\scripts\start-public-demo.ps1"
}

Write-Step "Checking prerequisites"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    if (Test-Path "C:\nodejs\node.exe") {
        $env:Path = "C:\nodejs;$env:Path"
        Write-Ok "Added C:\nodejs to PATH for this session."
    }
    else {
        Write-Error "Node.js not found on PATH and C:\nodejs\node.exe does not exist. Install Node.js first."
    }
}

$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$npmCommand = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    Write-Error "npm not found on PATH even though node is available. Reinstall Node.js."
}

$useQuickTunnel = -not $PublicUrl

if ($useQuickTunnel) {
    if (-not (Get-Command cloudflared -ErrorAction SilentlyContinue)) {
        Write-Error "cloudflared not found on PATH. Install it with:`n`n    $CloudflaredInstallHint`n`nThen open a new terminal and rerun this script."
    }
    $cloudflaredVersion = Invoke-Native { cloudflared --version 2>&1 } | Select-Object -First 1
    Write-Ok "cloudflared: $cloudflaredVersion"
}
else {
    $PublicUrl = $PublicUrl.TrimEnd('/')
    if ($PublicUrl -notmatch '^https?://') {
        Write-Error "-PublicUrl must start with http:// or https://. Got: $PublicUrl"
    }
    Write-Ok "Using the supplied public URL; no Quick Tunnel will be started."
}

if (-not (Test-Path $activateScript)) {
    Write-Error "Virtual environment not found at $activateScript. Create it with: python -m venv .venv (inside backend), then pip install -r requirements.txt"
}

if (-not (Test-Path (Join-Path $backendRoot ".env"))) {
    Write-Error "backend\.env not found. Copy backend\.env.example to backend\.env and set DATABASE_URL."
}

if (Test-PortOpen -TargetHost "127.0.0.1" -Port $FrontendPort) {
    Write-Error "Port $FrontendPort is already in use. Stop the other dev server, or pass -FrontendPort <port>."
}

if (Test-PortOpen -TargetHost "127.0.0.1" -Port $BackendPort) {
    Write-Error "Port $BackendPort is already in use. Stop the other backend, or pass -BackendPort <port>."
}

Write-Ok "Node: $(Invoke-Native { node --version })"
Write-Ok "Repository: $repoRoot"

if (-not (Test-Path $viteEntryPoint)) {
    Write-Step "Installing frontend dependencies"
    Invoke-Native { & $npmCommand.Source install --prefix $frontendRoot } "npm install failed."
    if (-not (Test-Path $viteEntryPoint)) {
        Write-Error "Vite is still missing at $viteEntryPoint after npm install."
    }
}

# --------------------------------------------------------------------------
# 2. Start the frontend and the tunnel
# --------------------------------------------------------------------------

$runDirectory = Join-Path $env:TEMP "accounting-ai-public-demo"
New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null

$frontendOutLog = Join-Path $runDirectory "frontend.out.log"
$frontendErrLog = Join-Path $runDirectory "frontend.err.log"
$tunnelOutLog = Join-Path $runDirectory "tunnel.out.log"
$tunnelErrLog = Join-Path $runDirectory "tunnel.err.log"
$stateFile = Join-Path $runDirectory "state.json"

$startedProcesses = @()

Push-Location $repoRoot
try {
    Write-Step "Starting frontend on http://127.0.0.1:$FrontendPort with API base /api"

    # Inherited by the child process. The frontend calls /api/*, the Vite proxy
    # forwards to the backend, and the browser stays on a single origin.
    $env:VITE_API_BASE_URL = "/api"
    $env:VITE_DEV_API_PROXY_TARGET = "http://127.0.0.1:$BackendPort"
    $env:VITE_PUBLIC_DEMO = "1"
    if (-not $useQuickTunnel) {
        $env:VITE_PUBLIC_DEMO_ALLOWED_HOSTS = ([System.Uri]$PublicUrl).Host
    }

    # Vite is launched through node rather than 'npm run dev' so the dev server
    # is a single process this script can stop; npm.cmd would leave it orphaned
    # holding the port.
    $frontendProcess = Start-Process -FilePath $nodeCommand.Source `
        -ArgumentList @($viteEntryPoint, "--host", "127.0.0.1", "--port", "$FrontendPort", "--strictPort") `
        -WorkingDirectory $frontendRoot -NoNewWindow -PassThru `
        -RedirectStandardOutput $frontendOutLog -RedirectStandardError $frontendErrLog
    $startedProcesses += $frontendProcess

    if (-not (Wait-ForPort -TargetHost "127.0.0.1" -Port $FrontendPort -TimeoutSeconds $FrontendReadyTimeoutSeconds -Process $frontendProcess)) {
        Write-Warn "Frontend did not start listening on 127.0.0.1:$FrontendPort within $FrontendReadyTimeoutSeconds seconds. Last log lines:"
        Write-LogTail -Paths @($frontendErrLog, $frontendOutLog)
        Write-Error "Frontend failed to start. Full log: $frontendOutLog"
    }

    Write-Ok "Frontend is listening."

    if ($useQuickTunnel) {
        Write-Step "Starting Cloudflare Quick Tunnel"

        $tunnelProcess = Start-Process -FilePath "cloudflared" `
            -ArgumentList @("tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:$FrontendPort") `
            -NoNewWindow -PassThru `
            -RedirectStandardOutput $tunnelOutLog -RedirectStandardError $tunnelErrLog
        $startedProcesses += $tunnelProcess

        # cloudflared prints the generated URL on stderr, so both streams are scanned.
        $deadline = (Get-Date).AddSeconds($TunnelUrlTimeoutSeconds)
        while (-not $PublicUrl -and (Get-Date) -lt $deadline) {
            foreach ($log in @($tunnelErrLog, $tunnelOutLog)) {
                $match = [regex]::Match((Read-LiveLog -Path $log), $TunnelUrlPattern)
                if ($match.Success) { $PublicUrl = $match.Value; break }
            }

            if ($PublicUrl) { break }
            if ($tunnelProcess.HasExited) { break }
            Start-Sleep -Milliseconds 500
        }

        if ($PublicUrl) {
            Write-Ok "Tunnel URL captured: $PublicUrl"
        }
        else {
            Write-Host ""
            Write-Warn "COULD NOT CAPTURE THE TUNNEL URL within $TunnelUrlTimeoutSeconds seconds."
            if ($tunnelProcess.HasExited) {
                Write-Warn "cloudflared exited with code $($tunnelProcess.ExitCode); the demo will not be reachable."
            }
            Write-Warn "Last tunnel log lines:"
            Write-LogTail -Paths @($tunnelErrLog, $tunnelOutLog)
            Write-Warn "Full log: $tunnelErrLog"
            Write-Warn "The backend starts without APP_PUBLIC_URL, so handover messages show the"
            Write-Warn "'[add your domain here]' placeholder. Read the URL from the log above, then"
            Write-Warn "rerun with -PublicUrl <url> to get it into handover messages."
            Write-Host ""
        }
    }

    @{
        startedUtc   = (Get-Date).ToUniversalTime().ToString("o")
        publicUrl    = $PublicUrl
        frontendPort = $FrontendPort
        backendPort  = $BackendPort
        processes    = @($startedProcesses | ForEach-Object {
                @{ id = $_.Id; name = $_.ProcessName; startTimeUtc = $_.StartTime.ToUniversalTime().ToString("o") }
            })
    } | ConvertTo-Json -Depth 4 | Set-Content -Path $stateFile -Encoding UTF8

    # ----------------------------------------------------------------------
    # 3. Summary
    # ----------------------------------------------------------------------

    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Green
    Write-Host " ONE-LINK PUBLIC DEMO" -ForegroundColor Green
    Write-Host "===============================================================" -ForegroundColor Green
    if ($PublicUrl) {
        Write-Host " Public demo URL   : $PublicUrl" -ForegroundColor Green
        Write-Host " Public API check  : $PublicUrl/api/health"
    }
    else {
        Write-Host " Public demo URL   : NOT AVAILABLE - see the warning above" -ForegroundColor Red
    }
    Write-Host " Frontend (local)  : http://127.0.0.1:$FrontendPort"
    Write-Host " Backend (local)   : http://127.0.0.1:$BackendPort  (Swagger at /docs)"
    Write-Host " Logs              : $runDirectory"
    Write-Host "---------------------------------------------------------------" -ForegroundColor Green
    Write-Host " Temporary demo, not production hosting:" -ForegroundColor Yellow
    Write-Host "  - this laptop must stay awake and online" -ForegroundColor Yellow
    Write-Host "  - this window must stay open; closing it ends the demo" -ForegroundColor Yellow
    Write-Host "  - the public URL changes every run and has no uptime guarantee" -ForegroundColor Yellow
    Write-Host "  - do not expose real client data through it" -ForegroundColor Yellow
    Write-Host "---------------------------------------------------------------" -ForegroundColor Green
    Write-Host " Press Ctrl+C to stop the backend; the frontend and the tunnel"
    Write-Host " are stopped straight afterwards."
    Write-Host "===============================================================" -ForegroundColor Green
    Write-Host ""

    if ($PublicUrl -and -not $NoOpen) {
        Start-Process $PublicUrl | Out-Null
    }

    # ----------------------------------------------------------------------
    # 4. Backend in the foreground
    # ----------------------------------------------------------------------

    Set-Location $backendRoot
    & $activateScript

    $env:PYTHONPATH = $backendRoot
    $env:APP_ENV = "development"
    $env:AI_JOURNAL_PROVIDER = "rules"
    if ($PublicUrl) {
        # Process-scoped only; backend\.env is never modified. Pydantic settings
        # give environment variables priority over the .env file.
        $env:APP_PUBLIC_URL = $PublicUrl
    }

    if (-not $SkipMigrations) {
        Write-Step "Applying database migrations"
        Invoke-Native { alembic upgrade head } "alembic upgrade head failed. Is PostgreSQL running and is DATABASE_URL correct?"
    }

    Write-Step "Starting backend on http://127.0.0.1:$BackendPort"
    # No --reload: an auto-restarting backend makes a live demo flaky.
    # No exit-code check: Ctrl+C is the normal way this returns.
    Invoke-Native { uvicorn app.main:app --host 127.0.0.1 --port $BackendPort }
}
finally {
    Write-Host ""
    Write-Step "Stopping the public demo"

    foreach ($process in $startedProcesses) {
        if ($process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            Write-Ok "Stopped $($process.ProcessName) (pid $($process.Id))."
        }
    }

    Remove-Item $stateFile -Force -ErrorAction SilentlyContinue
    Pop-Location
    Write-Ok "Demo stopped. Logs kept in $runDirectory"
}

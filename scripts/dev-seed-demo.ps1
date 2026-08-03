<#
.SYNOPSIS
    Seed local demo data (demo user, company, chart of accounts, journals).

.DESCRIPTION
    Activates the backend virtual environment and runs
    backend/scripts/seed_demo_data.py.

    The seed is idempotent and additive: re-running it will not duplicate data
    and will not delete anything. It refuses to run when APP_ENV is production.

.EXAMPLE
    .\scripts\dev-seed-demo.ps1

.EXAMPLE
    .\scripts\dev-seed-demo.ps1 --reset-demo-password
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot "backend"
$activateScript = Join-Path $backendRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $activateScript)) {
    Write-Error "Virtual environment not found at $activateScript. Create it with: python -m venv .venv (inside backend), then pip install -r requirements.txt"
}

Set-Location $backendRoot
& $activateScript

$env:PYTHONPATH = $backendRoot
$env:APP_ENV = "development"
$env:AI_JOURNAL_PROVIDER = "rules"

python scripts/seed_demo_data.py @args

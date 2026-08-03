<#
.SYNOPSIS
    Start the backend API for local development.

.DESCRIPTION
    Activates the backend virtual environment, applies Alembic migrations, and
    starts Uvicorn on http://127.0.0.1:8010.

    Requires PostgreSQL to be running and backend/.env to exist.
    Non-destructive: it never drops or resets the database.

.EXAMPLE
    .\scripts\dev-start-backend.ps1
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $repoRoot "backend"
$activateScript = Join-Path $backendRoot ".venv\Scripts\Activate.ps1"

if (-not (Test-Path $activateScript)) {
    Write-Error "Virtual environment not found at $activateScript. Create it with: python -m venv .venv (inside backend), then pip install -r requirements.txt"
}

if (-not (Test-Path (Join-Path $backendRoot ".env"))) {
    Write-Error "backend\.env not found. Copy backend\.env.example to backend\.env and set DATABASE_URL."
}

Set-Location $backendRoot
& $activateScript

$env:PYTHONPATH = $backendRoot
$env:APP_ENV = "development"
$env:AI_JOURNAL_PROVIDER = "rules"

Write-Host "Applying database migrations..." -ForegroundColor Cyan
alembic upgrade head

Write-Host "Starting backend on http://127.0.0.1:8010 (Swagger at /docs)" -ForegroundColor Green
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010

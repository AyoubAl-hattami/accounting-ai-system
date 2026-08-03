<#
.SYNOPSIS
    Start the frontend dev server for local development.

.DESCRIPTION
    Adds C:\nodejs to PATH when node is not already available, installs
    dependencies if node_modules is missing, and runs the Vite dev server.

    Non-destructive: it never deletes node_modules or build output.

.EXAMPLE
    .\scripts\dev-start-frontend.ps1
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $repoRoot "frontend"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    if (Test-Path "C:\nodejs\node.exe") {
        $env:Path = "C:\nodejs;$env:Path"
    }
    else {
        Write-Error "Node.js not found on PATH and C:\nodejs\node.exe does not exist. Install Node.js first."
    }
}

Set-Location $repoRoot

if (-not (Test-Path (Join-Path $frontendRoot "node_modules"))) {
    Write-Host "node_modules missing - installing frontend dependencies..." -ForegroundColor Cyan
    npm install --prefix frontend
}

Write-Host "Starting frontend dev server on http://127.0.0.1:5173" -ForegroundColor Green
npm run dev --prefix frontend

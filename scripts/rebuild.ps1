# Sync dependencies and rebuild the production frontend after dev work.
$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir

Write-Host "Rebuilding VLCouch for production..." -ForegroundColor Cyan

if (-not (Test-Path "$root\backend\.venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv "$root\backend\.venv"
}

Write-Host "Syncing Python dependencies..."
& "$root\backend\.venv\Scripts\pip" install -q -r "$root\backend\requirements.txt"

Push-Location "$root\frontend"
Write-Host "Syncing frontend dependencies..."
npm install --no-fund --no-audit
Write-Host "Building frontend for production..."
npm run build
Pop-Location

Write-Host ""
Write-Host "Production build ready: frontend\dist" -ForegroundColor Green
Write-Host "Restart the production server (start.bat) if it is already running." -ForegroundColor Yellow

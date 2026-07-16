# Start backend and frontend dev servers in separate windows
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "Starting VLCouch dev servers..." -ForegroundColor Cyan

# Ensure backend venv exists
if (-not (Test-Path "$root\backend\.venv")) {
    Write-Host "Creating Python virtual environment..."
    python -m venv "$root\backend\.venv"
    & "$root\backend\.venv\Scripts\pip" install -r "$root\backend\requirements.txt"
}

# Ensure frontend deps exist
if (-not (Test-Path "$root\frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..."
    Push-Location "$root\frontend"
    npm install
    Pop-Location
}

# Start backend with proper environment for development mode
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root'; $env:APP_ENV='development'; & backend\.venv\Scripts\python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend"
)

# Start frontend
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\frontend'; npm run dev"
)

Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Green
Write-Host ""
Write-Host "Two new terminal windows were opened. Close them to stop the servers." -ForegroundColor Yellow

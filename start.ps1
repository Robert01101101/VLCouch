# Launch VLCouch (production). Opens the default browser ASAP.
# Safe to run repeatedly — reuses an already-running server.
$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
$port = 8000
$hostAddr = "127.0.0.1"
$baseUrl = "http://${hostAddr}:$port"
$uvicorn = Join-Path $root "backend\.venv\Scripts\uvicorn.exe"

function Show-Error([string]$message) {
    Add-Type -AssemblyName System.Windows.Forms
    [void][System.Windows.Forms.MessageBox]::Show(
        $message,
        "VLCouch",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Warning
    )
}

function Test-ServerReady {
    try {
        $response = Invoke-WebRequest -Uri "$baseUrl/api/health" -UseBasicParsing -TimeoutSec 1
        return ($response.StatusCode -eq 200 -and $response.Content -match '"ok"')
    } catch {
        return $false
    }
}

function Test-PortListening {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Where-Object { $_.LocalAddress -in @("127.0.0.1", "0.0.0.0", "::") }
    return $null -ne $conn
}

function Wait-ServerReady([int]$timeoutSec = 60) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-ServerReady) { return $true }
        Start-Sleep -Milliseconds 100
    }
    return $false
}

function Start-AppServer {
    # Never inherit test env from a developer shell or prior test run.
    $env:APP_ENV = "production"
    Remove-Item Env:TEST_MODE -ErrorAction SilentlyContinue
    Remove-Item Env:TEST_DB_PATH -ErrorAction SilentlyContinue
    Remove-Item Env:TEST_MEDIA_ROOTS -ErrorAction SilentlyContinue
    Remove-Item Env:TEST_POSTERS_DIR -ErrorAction SilentlyContinue

    if (-not (Test-Path $uvicorn)) {
        Show-Error @"
Python environment is not set up.

Run this once from the project folder:
  .\scripts\install-shortcuts.ps1
"@
        exit 1
    }

    if (-not (Test-Path (Join-Path $root "frontend\dist\index.html"))) {
        Show-Error @"
Frontend build is missing.

Run this once from the project folder:
  .\scripts\install-shortcuts.ps1
"@
        exit 1
    }

    if (Test-PortListening) {
        if (-not (Wait-ServerReady -timeoutSec 30)) {
            Show-Error "Port $port is in use, but VLCouch did not respond.`nClose the other program or change the port."
            exit 1
        }
        return
    }

    Start-Process -FilePath $uvicorn -ArgumentList @(
        "app.main:app",
        "--host", $hostAddr,
        "--port", "$port",
        "--app-dir", "backend"
    ) -WorkingDirectory $root -WindowStyle Hidden | Out-Null

    if (-not (Wait-ServerReady -timeoutSec 60)) {
        Show-Error "The server did not start in time.`nCheck that Python and dependencies are installed."
        exit 1
    }
}

if (Test-ServerReady) {
    Start-Process $baseUrl | Out-Null
    exit 0
}

Start-AppServer
Start-Process $baseUrl | Out-Null

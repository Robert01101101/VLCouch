# Stop all running VLCouch servers
# This script stops any existing VLCouch Python and Node.js processes

$ErrorActionPreference = "Stop"

Write-Host "Stopping any running VLCouch servers..." -ForegroundColor Yellow

# Find and stop any running Python processes related to VLCouch
$pythonProcesses = Get-Process -Name python* -ErrorAction SilentlyContinue | Where-Object { 
    $_.Path -like "*vlcouch*" -or 
    $_.CommandLine -like "*uvicorn*" -or 
    $_.CommandLine -like "*app.main*" 
}

if ($pythonProcesses) {
    Write-Host "Stopping $($(Get-Process -Name python* -ErrorAction SilentlyContinue | Where-Object { 
        $_.Path -like "*vlcouch*" -or 
        $_.CommandLine -like "*uvicorn*" -or 
        $_.CommandLine -like "*app.main*" 
    }).Count) existing VLCouch Python server(s)..." -ForegroundColor Red
    $pythonProcesses | Stop-Process -Force
} else {
    Write-Host "No existing VLCouch Python servers found." -ForegroundColor Green
}

# Find and stop any running Node.js processes related to frontend dev server
$nodeProcesses = Get-Process -Name node* -ErrorAction SilentlyContinue | Where-Object { 
    $_.CommandLine -like "*vite*" -or 
    $_.CommandLine -like "*dev*" 
}

if ($nodeProcesses) {
    Write-Host "Stopping $($(Get-Process -Name node* -ErrorAction SilentlyContinue | Where-Object { 
        $_.CommandLine -like "*vite*" -or 
        $_.CommandLine -like "*dev*" 
    }).Count) existing frontend dev server(s)..." -ForegroundColor Red
    $nodeProcesses | Stop-Process -Force
} else {
    Write-Host "No existing frontend dev servers found." -ForegroundColor Green
}

Write-Host "All VLCouch processes have been stopped." -ForegroundColor Green
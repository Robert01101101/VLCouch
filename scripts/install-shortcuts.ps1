# One-time setup: dependencies, production build, Desktop + Start Menu shortcuts.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$launchScript = Join-Path $root "launch.vbs"
$appName = "VLCouch"

Write-Host "Setting up $appName..." -ForegroundColor Cyan

function Test-CommandExists([string]$name) {
    return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function Test-VlcInstalled {
    $paths = @(
        "${env:ProgramFiles}\VideoLAN\VLC\vlc.exe",
        "${env:ProgramFiles(x86)}\VideoLAN\VLC\vlc.exe"
    )
    foreach ($path in $paths) {
        if (Test-Path $path) { return $true }
    }
    try {
        $key = Get-ItemProperty -Path "HKLM:\SOFTWARE\VideoLAN\VLC" -ErrorAction Stop
        if ($key.InstallDir -and (Test-Path (Join-Path $key.InstallDir "vlc.exe"))) {
            return $true
        }
    } catch {
        # VLC not in registry
    }
    return $false
}

$missing = @()
if (-not (Test-CommandExists python)) {
    $missing += "Python 3 — install from https://www.python.org/downloads/ or run: winget install Python.Python.3.12"
}
if (-not (Test-CommandExists npm)) {
    $missing += "Node.js — install from https://nodejs.org/ or run: winget install OpenJS.NodeJS.LTS"
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Host "Missing required software:" -ForegroundColor Red
    foreach ($item in $missing) {
        Write-Host "  - $item" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Install the items above, then run Setup.bat again." -ForegroundColor Red
    exit 1
}

if (-not (Test-CommandExists ffmpeg)) {
    Write-Host "Warning: ffmpeg not found on PATH. Thumbnails will not work until you install it." -ForegroundColor Yellow
    Write-Host "  Install with: winget install Gyan.FFmpeg" -ForegroundColor Yellow
}

if (-not (Test-VlcInstalled)) {
    Write-Host "Warning: VLC not found. Playback will not work until you install it." -ForegroundColor Yellow
    Write-Host "  Install from https://www.videolan.org/ or run: winget install VideoLAN.VLC" -ForegroundColor Yellow
}

Write-Host ""
if (-not (Test-Path (Join-Path $root ".env"))) {
    $example = Join-Path $root ".env.example"
    if (Test-Path $example) {
        Copy-Item $example (Join-Path $root ".env")
        Write-Host "Created .env from .env.example — add media folders in Settings after launch." -ForegroundColor Yellow
    } else {
        Write-Host "Warning: no .env file found. Create one with your MEDIA_ROOTS." -ForegroundColor Yellow
    }
}

if (-not (Test-Path (Join-Path $root "backend\.venv"))) {
    Write-Host "Creating Python virtual environment..."
    python -m venv (Join-Path $root "backend\.venv")
}

Write-Host "Installing Python dependencies..."
& (Join-Path $root "backend\.venv\Scripts\pip") install -q -r (Join-Path $root "backend\requirements.txt")

Push-Location (Join-Path $root "frontend")
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..."
    npm install
}
Write-Host "Building frontend for production..."
npm run build
Pop-Location

function New-AppShortcut([string]$path) {
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($path)
    $shortcut.TargetPath = $launchScript
    $shortcut.WorkingDirectory = $root
    $shortcut.Description = "Browse and play your local media library"

    $icon = Join-Path $root "vlcouch.ico"
    if (Test-Path $icon) {
        $shortcut.IconLocation = $icon
    } else {
        $shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,184"
    }

    $shortcut.Save()
}

$desktop = [Environment]::GetFolderPath("Desktop")
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"

New-AppShortcut (Join-Path $desktop "$appName.lnk")
New-AppShortcut (Join-Path $startMenu "$appName.lnk")
New-AppShortcut (Join-Path $root "$appName.lnk")

Write-Host ""
Write-Host "Shortcuts created:" -ForegroundColor Green
Write-Host "  Project:    $(Join-Path $root "$appName.lnk")"
Write-Host "  Desktop:    $(Join-Path $desktop "$appName.lnk")"
Write-Host "  Start menu: $(Join-Path $startMenu "$appName.lnk")"
Write-Host ""
Write-Host "Bookmark in your browser: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "Click a shortcut to launch - your browser opens automatically." -ForegroundColor Cyan

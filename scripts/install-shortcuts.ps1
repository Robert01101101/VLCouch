# One-time setup: dependencies, production build, Desktop + Start Menu shortcuts.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$launchScript = Join-Path $root "launch.vbs"
$appName = "VLCouch"

Write-Host "Setting up $appName..." -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $root ".env"))) {
    $example = Join-Path $root ".env.example"
    if (Test-Path $example) {
        Copy-Item $example (Join-Path $root ".env")
        Write-Host "Created .env from .env.example - edit MEDIA_ROOTS before browsing your library." -ForegroundColor Yellow
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

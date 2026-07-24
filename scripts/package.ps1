# Assemble dist/staging for the Windows installer (embeddable Python + built frontend).
param(
    [switch]$SkipFrontendBuild
)

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir
$staging = Join-Path $root "dist\staging"
$versionFile = Join-Path $root "VERSION"

if (-not (Test-Path $versionFile)) {
    throw "VERSION file not found at $versionFile"
}
$version = (Get-Content $versionFile -Raw).Trim()
if (-not $version) {
    throw "VERSION file is empty"
}

$pythonVersion = "3.12.8"
$pythonZipName = "python-$pythonVersion-embed-amd64.zip"
$pythonZipUrl = "https://www.python.org/ftp/python/$pythonVersion/$pythonZipName"
$cacheDir = Join-Path $root "dist\cache"
$pythonZipPath = Join-Path $cacheDir $pythonZipName
$pythonDir = Join-Path $staging "python"

Write-Host "Packaging VLCouch $version..." -ForegroundColor Cyan

if (Test-Path $staging) {
    Remove-Item $staging -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $staging, $cacheDir | Out-Null

if (-not $SkipFrontendBuild) {
    Push-Location (Join-Path $root "frontend")
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing frontend dependencies..."
        npm install --no-fund --no-audit
    }
    Write-Host "Building frontend..."
    npm run build
    Pop-Location
}

if (-not (Test-Path (Join-Path $root "frontend\dist\index.html"))) {
    throw "frontend/dist is missing. Run npm run build in frontend/ first."
}

if (-not (Test-Path $pythonZipPath)) {
    Write-Host "Downloading Python $pythonVersion embeddable..."
    Invoke-WebRequest -Uri $pythonZipUrl -OutFile $pythonZipPath -UseBasicParsing
}

Write-Host "Extracting Python runtime..."
Expand-Archive -Path $pythonZipPath -DestinationPath $pythonDir -Force

$pthFiles = Get-ChildItem -Path $pythonDir -Filter "python*._pth"
if ($pthFiles.Count -ne 1) {
    throw "Expected one python*._pth file in $pythonDir"
}
$pthPath = $pthFiles[0].FullName
$pthContent = Get-Content $pthPath -Raw
if ($pthContent -notmatch "Lib\\site-packages") {
    Add-Content -Path $pthPath -Value "Lib\site-packages"
}
if ($pthContent -notmatch "import site") {
    Add-Content -Path $pthPath -Value "import site"
}

$sitePackages = Join-Path $pythonDir "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null

$getPip = Join-Path $cacheDir "get-pip.py"
if (-not (Test-Path $getPip)) {
    Write-Host "Downloading get-pip.py..."
    Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getPip -UseBasicParsing
}

$pythonExe = Join-Path $pythonDir "python.exe"
Write-Host "Bootstrapping pip..."
& $pythonExe $getPip --no-warn-script-location | Out-Null

Write-Host "Installing Python dependencies..."
& $pythonExe -m pip install --disable-pip-version-check -q `
    -r (Join-Path $root "backend\requirements.txt") `
    --target $sitePackages

Write-Host "Copying application files..."
$backendDest = Join-Path $staging "backend"
New-Item -ItemType Directory -Force -Path (Join-Path $backendDest "app") | Out-Null
Copy-Item -Path (Join-Path $root "backend\app\*") -Destination (Join-Path $backendDest "app") -Recurse -Force

$versionTxtDest = Join-Path $backendDest "app\version.txt"
Set-Content -Path $versionTxtDest -Value $version -NoNewline -Encoding utf8

$frontendDest = Join-Path $staging "frontend\dist"
New-Item -ItemType Directory -Force -Path $frontendDest | Out-Null
Copy-Item -Path (Join-Path $root "frontend\dist\*") -Destination $frontendDest -Recurse -Force

$scriptsDest = Join-Path $staging "scripts"
New-Item -ItemType Directory -Force -Path $scriptsDest | Out-Null
Copy-Item -Path (Join-Path $root "scripts\start.ps1") -Destination $scriptsDest -Force
Copy-Item -Path (Join-Path $root "scripts\stop-all.ps1") -Destination $scriptsDest -Force

foreach ($file in @("launch.vbs", "vlcouch.ico")) {
    $src = Join-Path $root $file
    if (Test-Path $src) {
        Copy-Item -Path $src -Destination (Join-Path $staging $file) -Force
    }
}

$installJson = @{
    version  = $version
    data_dir = "%LOCALAPPDATA%\VLCouch\data"
} | ConvertTo-Json -Compress
Set-Content -Path (Join-Path $staging "install.json") -Value $installJson -Encoding utf8

Write-Host "Smoke-testing packaged server startup..."
$env:VLCOUCH_DATA_DIR = Join-Path $env:TEMP "vlcouch-package-smoke\data"
New-Item -ItemType Directory -Force -Path $env:VLCOUCH_DATA_DIR | Out-Null
$env:APP_ENV = "production"
Remove-Item Env:TEST_MODE -ErrorAction SilentlyContinue

$smokeProc = Start-Process -FilePath $pythonExe -ArgumentList @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", "127.0.0.1",
    "--port", "8010",
    "--app-dir", "backend"
) -WorkingDirectory $staging -WindowStyle Hidden -PassThru

try {
    $ready = $false
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:8010/api/health" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 200
        }
    }
    if (-not $ready) {
        throw "Packaged server did not respond on port 8010"
    }
    Write-Host "Smoke test passed." -ForegroundColor Green
} finally {
    if ($smokeProc -and -not $smokeProc.HasExited) {
        Stop-Process -Id $smokeProc.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:VLCOUCH_DATA_DIR -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "Staging ready: $staging" -ForegroundColor Green
Write-Host "Version: $version"

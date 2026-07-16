param(
    [ValidateSet("api", "unit", "e2e", "all")]
    [string]$Layer = "all"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $root

function Ensure-BackendVenv {
    if (-not (Test-Path "$projectRoot\backend\.venv")) {
        Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
        python -m venv "$projectRoot\backend\.venv"
        & "$projectRoot\backend\.venv\Scripts\python" -m pip install --disable-pip-version-check -r "$projectRoot\backend\requirements.txt"
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    & "$projectRoot\backend\.venv\Scripts\python" -m pip install -q --disable-pip-version-check -r "$projectRoot\backend\requirements-dev.txt"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

function Run-ApiTests {
    Write-Host "`n=== Backend API tests (pytest) ===" -ForegroundColor Cyan
    Ensure-BackendVenv
    $env:APP_ENV = "test"
    $env:TEST_MODE = "true"
    Push-Location "$projectRoot\backend"
    try {
        & ".\.venv\Scripts\python" -m pytest tests -q
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

function Run-UnitTests {
    Write-Host "`n=== Frontend unit tests (Vitest) ===" -ForegroundColor Cyan
    if (-not (Test-Path "$projectRoot\frontend\node_modules")) {
        Push-Location "$projectRoot\frontend"
        npm install
        Pop-Location
    }
    Push-Location "$projectRoot\frontend"
    try {
        npm test -- --run
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

function Run-E2ETests {
    Write-Host "`n=== E2E tests (Playwright) ===" -ForegroundColor Cyan
    Ensure-BackendVenv
    if (-not (Test-Path "$projectRoot\frontend\node_modules")) {
        Push-Location "$projectRoot\frontend"
        npm install
        Pop-Location
    }
    if (-not (Test-Path "$projectRoot\node_modules")) {
        Push-Location $projectRoot
        npm install
        Pop-Location
    }
    Push-Location $projectRoot
    try {
        npx playwright install chromium
        npm run test:e2e
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } finally {
        Pop-Location
    }
}

switch ($Layer) {
    "api"  { Run-ApiTests }
    "unit" { Run-UnitTests }
    "e2e"  { Run-E2ETests }
    "all"  {
        Run-ApiTests
        Run-UnitTests
        Run-E2ETests
    }
}

Write-Host "`nAll requested tests passed." -ForegroundColor Green

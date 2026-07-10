# Suggest relevant tests after agent completes a turn (fail-open, non-blocking)
$ErrorActionPreference = "SilentlyContinue"

$inputJson = [Console]::In.ReadToEnd() | ConvertFrom-Json
$editedFiles = @()

if ($inputJson.edited_files) {
    $editedFiles = $inputJson.edited_files
}

$suggestions = @()

foreach ($file in $editedFiles) {
    if ($file -match "backend/app/") {
        $suggestions += "Run: .\scripts\test.ps1 -Layer api"
    }
    if ($file -match "frontend/src/") {
        $suggestions += "Run: .\scripts\test.ps1 -Layer unit"
        if ($file -match "pages/") {
            $suggestions += "Run: .\scripts\test.ps1 -Layer e2e"
        }
    }
}

if ($suggestions.Count -gt 0) {
    $unique = $suggestions | Select-Object -Unique
    Write-Host ""
    Write-Host "Suggested verification:" -ForegroundColor Cyan
    foreach ($s in $unique) {
        Write-Host "  $s"
    }
}

exit 0

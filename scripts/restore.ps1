# ==============================================================================
# InfraDoc - Production Restore Script for Windows Environment
# ==============================================================================
param(
    [Parameter(Mandatory=$true)]
    [string]$Archive
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Archive)) {
    Write-Error "Backup archive not found: $Archive"
    exit 1
}

Write-Host "======================================================" -ForegroundColor Yellow
Write-Host " Starting InfraDoc Restore from $Archive at $(Get-Date)" -ForegroundColor Yellow
Write-Host "======================================================" -ForegroundColor Yellow

if (Test-Path ".\backend\.venv\Scripts\python.exe") {
    $pythonExe = ".\backend\.venv\Scripts\python.exe"
} else {
    $pythonExe = "python"
}

& $pythonExe scripts\restore.py $Archive
if ($LASTEXITCODE -ne 0) {
    Write-Error "Restore failed!"
    exit $LASTEXITCODE
}

Write-Host "Restore finished successfully!" -ForegroundColor Green

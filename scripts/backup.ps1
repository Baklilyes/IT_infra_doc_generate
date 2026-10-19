# ==============================================================================
# InfraDoc - Production Backup Script for Windows Environment
# ==============================================================================
param(
    [string]$OutputDir = ".\backups"
)

$ErrorActionPreference = "Stop"

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host " Starting InfraDoc Backup at $(Get-Date)" -ForegroundColor Cyan
Write-Host " Output directory: $OutputDir" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

if (Test-Path ".\backend\.venv\Scripts\python.exe") {
    $pythonExe = ".\backend\.venv\Scripts\python.exe"
} else {
    $pythonExe = "python"
}

& $pythonExe scripts\backup.py --output-dir $OutputDir
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backup failed!"
    exit $LASTEXITCODE
}

Write-Host "Backup finished successfully!" -ForegroundColor Green

# Host (PC) smoke test of the Mamba HAR C model — no MCU needed.
# Compiles firmware/host/host_main.c with gcc inside WSL and runs it.
# Usage: powershell -ExecutionPolicy Bypass -File .\run_host_test.ps1 [-Iterations 1000]
param([int]$Iterations = 1)

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$wslRoot = (wsl wslpath -a ($repo -replace '\\', '/') | Select-Object -First 1).Trim()
$logDir = Join-Path $PSScriptRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("host_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".txt")

$out = wsl -e bash "$wslRoot/firmware/host/run_host_test.sh" $Iterations 2>&1
$code = $LASTEXITCODE
$out | Tee-Object -FilePath $log
if ($code -ne 0) {
    Write-Host "FAILED (exit $code)"
    exit $code
}
Write-Host "Log saved: $log"

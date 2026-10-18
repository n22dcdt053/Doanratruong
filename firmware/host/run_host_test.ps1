# Host (PC) test of the Mamba HAR C model — no MCU needed. Compiles and runs
# firmware/host/host_main.c with WSL gcc; evidence lands in firmware/host/logs/.
#   Single sample + timing + RSS:  .\run_host_test.ps1 -Iterations 1000
#   Batch -> logits CSV:           .\run_host_test.ps1 -Batch .\logs\batch_demo.f32 -OutName fixed_logits.csv
param(
    [int]$Iterations = 1,
    [string]$Batch,
    [string]$OutName
)

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$wslRoot = (wsl wslpath -a ($repo -replace '\\', '/') | Select-Object -First 1).Trim()
$logDir = Join-Path $PSScriptRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if ($Batch) {
    if (-not $OutName) { $OutName = "batch_logits.csv" }
    $batchWsl = (wsl wslpath -a ((Resolve-Path $Batch).Path -replace '\\', '/') | Select-Object -First 1).Trim()
    $outWsl = "$wslRoot/firmware/host/logs/$OutName"
    $out = wsl -e bash "$wslRoot/firmware/host/run_host_test.sh" --batch "$batchWsl" "$outWsl" 2>&1
    $code = $LASTEXITCODE
    $out
    if ($code -ne 0) {
        Write-Host "FAILED (exit $code)"
        exit $code
    }
    Write-Host "CSV saved: $(Join-Path $logDir $OutName)"
    return
}

$log = Join-Path $logDir ("host_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".txt")
$out = wsl -e bash "$wslRoot/firmware/host/run_host_test.sh" $Iterations 2>&1
$code = $LASTEXITCODE
$out | Tee-Object -FilePath $log
if ($code -ne 0) {
    Write-Host "FAILED (exit $code)"
    exit $code
}
Write-Host "Log saved: $log"

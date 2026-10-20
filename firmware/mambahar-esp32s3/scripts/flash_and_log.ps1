# Flash firmware to ESP32-S3 and capture the serial log as evidence (DATN).
#
# Modes:
#   .\flash_and_log.ps1                          build + upload + capture 35s
#   .\flash_and_log.ps1 -SkipBuild               upload + capture (firmware unchanged)
#   .\flash_and_log.ps1 -SkipBuild -SkipUpload   capture only (board already flashed)
#   .\flash_and_log.ps1 -Port COM7 -DurationSec 25
#
# Evidence: logs\esp32s3_har_<timestamp>.txt and logs\build_<timestamp>.txt
param(
    [string]$Port,
    [int]$DurationSec = 35,
    [switch]$SkipBuild,
    [switch]$SkipUpload
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$logDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
Set-Location $root
$ts = Get-Date -Format "yyyyMMdd_HHmmss"

# Returns the first USB serial port; empty when only non-USB (e.g. Bluetooth) ports exist.
function Get-UsbSerialPort {
    try {
        $found = Get-PnpDevice -Class Ports -Status OK -ErrorAction Stop |
            Where-Object { $_.FriendlyName -notmatch "Bluetooth" -and $_.FriendlyName -match "\((COM\d+)\)" } |
            ForEach-Object { [regex]::Match($_.FriendlyName, "\((COM\d+)\)").Groups[1].Value }
        return ($found | Select-Object -First 1)
    } catch {
        # PnpDevice unavailable: fall back to raw list (may include Bluetooth; pass -Port to be sure).
        return ([System.IO.Ports.SerialPort]::GetPortNames() | Select-Object -First 1)
    }
}

if (-not $SkipBuild) {
    Write-Host "== build =="
    # Native tools (gcc/pio) write warnings to stderr; keep them from tripping
    # ErrorActionPreference=Stop — exit code is the source of truth.
    $ErrorActionPreference = "Continue"
    pio run 2>&1 | Tee-Object -FilePath (Join-Path $logDir "build_$ts.txt")
    $ErrorActionPreference = "Stop"
    if ($LASTEXITCODE -ne 0) { throw "Build failed (see logs\build_$ts.txt)" }
}

if (-not $SkipUpload) {
    if (-not $Port) { $Port = Get-UsbSerialPort }
    if (-not $Port) { throw "No USB serial port found. Plug the board with a USB-C data cable, or pass -Port COMx." }
    Write-Host "== upload to $Port =="
    $env:PLATFORMIO_UPLOAD_PORT = $Port
    $ErrorActionPreference = "Continue"
    pio run -t upload 2>&1 | Tee-Object -FilePath (Join-Path $logDir "upload_$ts.txt")
    $ErrorActionPreference = "Stop"
    if ($LASTEXITCODE -ne 0) { throw "Upload failed. Hold BOOT while plugging the board, or check the cable is a data cable." }
    Start-Sleep -Seconds 2
} elseif (-not $Port) {
    $Port = Get-UsbSerialPort
    if (-not $Port) { throw "No USB serial port found for capture. Pass -Port COMx." }
}

Write-Host "== capturing $DurationSec s on $Port @115200 =="
$logFile = Join-Path $logDir "esp32s3_har_$ts.txt"
$sp = New-Object System.IO.Ports.SerialPort
$sp.PortName = $Port
$sp.BaudRate = 115200
$sp.Parity = [System.IO.Ports.Parity]::None
$sp.DataBits = 8
$sp.StopBits = [System.IO.Ports.StopBits]::One
# DTR/RTS off: don't disturb the board after esptool's hard reset (PS 5.1 also
# mangles enum members inside New-Object -ArgumentList, hence property-by-property).
$sp.DtrEnable = $false
$sp.RtsEnable = $false
$sp.Open()
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$sb = New-Object System.Text.StringBuilder
while ($sw.Elapsed.TotalSeconds -lt $DurationSec) {
    $chunk = $sp.ReadExisting()
    if ($chunk) { [void]$sb.Append($chunk); Write-Host -NoNewline $chunk }
    Start-Sleep -Milliseconds 50
}
$sp.Close()
$sb.ToString() | Out-File -FilePath $logFile -Encoding utf8
Write-Host ""
Write-Host "== saved: $logFile =="

$preds = [regex]::Matches($sb.ToString(), "Prediction:\s*(-?\d+)")
if ($preds.Count -eq 0) {
    Write-Host "WARNING: no 'Prediction:' line captured. Check port, baud rate, and that the board booted."
} else {
    foreach ($m in $preds) { Write-Host ("Prediction seen: " + $m.Groups[1].Value) }
}

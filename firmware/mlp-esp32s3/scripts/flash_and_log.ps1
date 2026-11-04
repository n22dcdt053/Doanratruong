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
    [int]$DurationSec = 45,
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
    # -j 1: xtensa-gcc 8.4 ICEs (RTL pass "ira") in esp_lcd_panel_rgb.c under
    # parallel builds; serial build is the known working workaround.
    pio run -j 1 2>&1 | Tee-Object -FilePath (Join-Path $logDir "build_$ts.txt")
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
    # Traceability (thesis form B.1: firmware-commit-checksum): the firmware log
    # carries its git commit, so record the exact binary hash next to the upload.
    $uploadLog = Join-Path $logDir "upload_$ts.txt"
    foreach ($name in @("firmware.bin", "firmware.elf")) {
        $path = Join-Path $root ".pio\build\esp32s3\$name"
        if (Test-Path $path) {
            $line = "sha256 " + $name + ": " + (Get-FileHash -Algorithm SHA256 $path).Hash.ToLower()
            Add-Content -Path $uploadLog -Value $line
            Write-Host $line
        }
    }
    # Open the port right after esptool releases it (0.3 s) so the boot banner
    # (FW commit / reset reason / boot #) lands in the log, not just the test.
    Start-Sleep -Milliseconds 300
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
$readErrors = 0
while ($sw.Elapsed.TotalSeconds -lt $DurationSec) {
    if (-not $sp.IsOpen) {
        # USB-serial hiccup: reopen (keep DTR/RTS low so the board is not reset).
        try {
            $sp.DtrEnable = $false
            $sp.RtsEnable = $false
            $sp.Open()
            Write-Host ""
            Write-Host "== serial port reopened =="
        } catch {
            Start-Sleep -Milliseconds 500
            continue
        }
    }
    try {
        $chunk = $sp.ReadExisting()
        if ($chunk) { [void]$sb.Append($chunk); Write-Host -NoNewline $chunk }
    } catch {
        $readErrors++
        Write-Host ""
        Write-Host ("WARNING: serial read error #" + $readErrors + ": " + $_.Exception.Message)
        try { $sp.Close() } catch { }
        if ($readErrors -ge 5) { break }
        Start-Sleep -Seconds 1
    }
    Start-Sleep -Milliseconds 50
}
try { $sp.Close() } catch { }
$sb.ToString() | Out-File -FilePath $logFile -Encoding utf8
Write-Host ""
Write-Host "== saved: $logFile =="

$preds = [regex]::Matches($sb.ToString(), "(?:Prediction:\s*|pred=)(-?\d+)")
if ($preds.Count -eq 0) {
    Write-Host "WARNING: no prediction line captured. Check port, baud rate, and that the board booted."
} else {
    $vals = $preds | ForEach-Object { $_.Groups[1].Value }
    $summary = ($vals | Group-Object | Sort-Object Name | ForEach-Object { "$($_.Name):$($_.Count)" }) -join " "
    Write-Host ("Predictions seen: " + $preds.Count + " -> " + $summary)
}

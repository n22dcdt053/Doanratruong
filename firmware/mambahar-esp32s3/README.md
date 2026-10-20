# mambahar-esp32s3 — Mamba HAR inference trên ESP32-S3 (dev project DATN)

## Mục đích
Chạy suy luận Mamba HAR (6 lớp) trên ESP32-S3 bằng nguồn kế thừa MambaLite-Micro,
làm bước đệm đo kích thước/độ trễ trước khi có Portenta H7 (STM32H7).
KHÔNG thay thế nghiệm thu trên Portenta H7.

## Nguồn
- Upstream: `..\..\MambaLite-Micro` (commit `44d51fc`, MIT) — **không sửa**.
- Port từ `examples/mambahar-arduino-6` (HAR) + `examples/mambakws-esp32-3` (khung ESP-IDF).
- Wrapper mô hình đã vendor sang `..\common\mambahar.c` (copy 1:1 ngày 18/10/2026,
  sha256 `84AC465D…`); **mọi sửa đổi từ đây làm trên bản vendor**, upstream giữ nguyên.
  Diff so với upstream ghi vào nhật ký quyết định của `HUONG_PHAT_TRIEN.md`.
- Weights `const float` → nằm trong flash; kiểm tra dung lượng sau build.

## Chạy
Mở PowerShell:
```powershell
cd D:\DoanNhomQuy\firmware\mambahar-esp32s3
powershell -ExecutionPolicy Bypass -File .\scripts\flash_and_log.ps1 -DurationSec 155
```
- Script: build (trừ khi `-SkipBuild`) + nạp + bắt log N giây, tự lưu evidence vào `logs\`.
- Đã nạp rồi, chỉ đọc log: thêm `-SkipBuild -SkipUpload`.
- Chỉ định cổng khi có nhiều COM: thêm `-Port COM11` (cổng USB-UART CH343; xem bằng `pio device list`).
- Không nhận cổng: cắm cáp USB-C **truyền dữ liệu**, hoặc bấm giữ BOOT khi cắm.
- USB-serial có thể drop giữa chừng (log ghi `WARNING: serial read error` rồi
  `== serial port reopened ==`); script vẫn lưu phần đã bắt.

## Chế độ hiện tại: 1.000 lượt, 20 mẫu, số học proxy tính trên bo
- 1 lần boot; vòng lặp **im lặng** (không in gì giữa `t0..t1`) → số đo thời gian sạch.
- `vTaskDelay(1)` sau mỗi lượt, **ngoài cửa sổ đo** → IDLE0 có CPU, không trigger task watchdog.
- 20 mẫu UCI thật, **đủ 6 lớp** (3 mẫu/lớp dự đoán host + 2 mẫu phụ): chỉ số
  `79,80,81,128,133,134,109,110,111,31,33,34,0,1,2,55,56,57,112,35` — đúng bytes
  `firmware/host/logs/uci_test.f32`; nhãn/logits tham chiếu từ
  `firmware/host/logs/uci_test_logits_final.csv` nhúng sẵn trong `src/uci_samples.h`.
- Bo tự tính `max|Δlogit|`, MAE trên 6.000 so sánh (1.000 lượt × 6 logits) và đếm lệch nhãn.
- **Không phải tier-B**: đây là số học **proxy** (Xtensa / ESP-IDF / build C). Tier-B nghiệm
  thu cần Portenta H7 (build C++ qua `main.cpp`) và ngưỡng do GVHD xác nhận.

## Truy vết firmware (biểu mẫu B.1)
- `scripts/gen_build_info.py` (PlatformIO `extra_scripts`) sinh `src/build_info.h` mỗi build:
  commit ngắn + trạng thái cây + giờ UTC. Firmware in ngay đầu log:
  `FW commit <sha> (clean|dirty) built <UTC> | opt=<mức tối ưu>`.
- `flash_and_log.ps1` ghi thêm `sha256 firmware.bin` + `firmware.elf` vào `upload_*.txt`.
- Quy trình: commit mã nguồn → build/nạp/log trong một lần chạy → commit log. Log mang commit
  và hash của đúng binary đã nạp.

## Log kỳ vọng (log thật 20/10: `logs\esp32s3_har_20261020_134435.txt`, 2.164 B)
```
starting in 4 seconds...
starting in 3 seconds...
starting in 2 seconds...
starting in 1 seconds...
starting in 0 seconds...
FW commit 940d3ac (clean) built 2026-10-20T06:44:38Z UTC | opt=debug(-Og)
Reset: reason=1 (POWERON) | boot #1 since RTC_NOINIT init
ESP32-S3 bring-up (proxy numerics, NOT tier-B acceptance; Portenta H7 required)
Stability+numerics: 1000 runs x 20 UCI samples, quiet loop, WDT fed
Test start: boot #1 | free heap 385668 bytes
BENCH DONE: runs=1000 samples=20 invalid=0 label_mismatch=0
proxy numerics (Xtensa/ESP-IDF/C; NOT tier-B): comparisons=6000 max|dlogit|=7.629e-06 MAE=9.157e-07
time_us: min=122165 p50=122230 p95=122265 max=122505 mean=122228 sd=30
heap: end=385452 min_ever=342196 bytes
heap every 50 runs (bytes): 385668 385668 ... (21 mốc, phẳng)
sample 0 (idx 79): pred=0 host_pred=0 max|d|=2.742e-06
... (20 dòng, mỗi mẫu 1 dòng)
Resets: boot_start=1 boot_end=1 | no reset during test
```
- `Reset:` + `Resets:` là firmware tự đo (không phải chuỗi cố định): `esp_reset_reason()` và
  bộ đếm `RTC_NOINIT`. Reset mềm/WDT làm tăng bộ đếm; mất điện thì RTC mất và báo POWERON
  (khi đó log sẽ có thêm dòng `Test start` thứ hai).
- `opt=debug(-Og)`: `sdkconfig.esp32s3` đang `CONFIG_COMPILER_OPTIMIZATION_DEBUG` → một phần
  lớn khoảng cách 122 ms vs 416 µs trên PC; chưa thử `-O2`/`-Os`.
- `7,629e-6 = 2^-17` ≈ 1 ULP float32 quanh |logit| ≈ 74 → lệch chủ yếu ở độ phân giải float32.
  Ngưỡng 1e-4 / 1e-5 **chưa được GVHD xác nhận**; chỉ ghi nhận là dưới ngưỡng đã ghi trong
  `HUONG_PHAT_TRIEN.md`.
- Heap phẳng: 21 mốc đều 385.668 B; Δ216 B chỉ ở lần in đầu. Đỉnh làm việc
  385.668 − 342.196 = **43.472 B**.
- `-2` vẫn là mã "logits không hữu hạn" (logits lỗi không bị tính thành lớp 0).

## Evidence tự động
- `logs\build_<timestamp>.txt` — output build (có bảng Flash/RAM).
- `logs\upload_<timestamp>.txt` — output nạp (kèm `Hash of data verified` + sha256 bin/elf).
- `logs\esp32s3_har_<timestamp>.txt` — log serial thô.
- `logs\esp32s3_har_20261020_124034.txt` — lần chạy **trước khi sửa**: 24 trigger task
  watchdog (IDLE0) + 24 ngoại lệ 161–171 ms; giữ làm dấu vết lỗi đã sửa.

## Giới hạn
- Đây là **bring-up ESP32 (proxy)**, không phải nghiệm thu tiêu chí nào: 1.000 lượt,
  Flash/RAM map file, năng lượng phải chạy trên **Portenta H7 thật**.
- 20 mẫu luân phiên (không phải 1.000 đầu vào khác nhau); `host_pred` là dự đoán của
  host, không phải nhãn thật (dataset gốc đã xoá).
- Board: **ESP32-S3-WROOM-1 N16R8** (`board = esp32-s3-devkitc-1`, flash 16 MB khai trong
  `platformio.ini`, PSRAM tắt); bo DevKitC-1 có 2 cổng USB — dùng cổng **UART/CH343**
  (COM11 ngày 20/10).

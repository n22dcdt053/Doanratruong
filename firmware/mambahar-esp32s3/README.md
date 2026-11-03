# mambahar-esp32s3 — Mamba HAR inference trên ESP32-S3 (nền tảng chính của DATN)

## Mục đích
Chạy suy luận Mamba HAR (6 lớp) trên ESP32-S3 bằng nguồn kế thừa MambaLite-Micro.
ESP32-S3 là nền tảng chính của đồ án (việc chuyển từ Portenta H7 được giảng viên đồng ý
qua tin nhắn; chưa có văn bản). Ngưỡng sai số 1e-4 / 1e-5 vẫn chờ giảng viên xác nhận,
nên tài liệu chỉ báo số đo, không kết luận theo ngưỡng nào.

> Thành viên nhóm mới: đọc [HUONG_DAN_NHOM.md](HUONG_DAN_NHOM.md) để clone đúng upstream + chạy lấy bằng chứng.

## Nguồn
- Upstream: `..\..\MambaLite-Micro` (commit `44d51fc`, MIT) — **không sửa**.
- Port từ `examples/mambahar-arduino-6` (HAR) + `examples/mambakws-esp32-3` (khung ESP-IDF).
- Wrapper mô hình đã vendor sang `..\common\mambahar.c` (bản sửa từ upstream: leak fix,
  trả 6 logits); **mọi sửa đổi từ đây làm trên bản vendor**, upstream giữ nguyên.
  Hash ghi trong `source_manifest.json`; diff trong `..\common\mambahar_vs_upstream.diff`
  (kernel: `..\common\mamba_vs_upstream.diff`).
- Weights `const float` → nằm trong flash; kiểm tra dung lượng sau build.

## Chạy
Từ thư mục gốc repo, mở PowerShell:
```powershell
cd firmware\mambahar-esp32s3
powershell -ExecutionPolicy Bypass -File .\scripts\flash_and_log.ps1 -DurationSec 155
```
- Script: build (trừ khi `-SkipBuild`) + nạp + bắt log N giây, tự lưu evidence vào `logs\`.
- Đã nạp rồi, chỉ đọc log: thêm `-SkipBuild -SkipUpload`.
- Chỉ định cổng khi có nhiều COM: thêm `-Port COM11` (cổng USB-UART CH343; xem bằng `pio device list`).
- Không nhận cổng: cắm cáp USB-C **truyền dữ liệu**, hoặc bấm giữ BOOT khi cắm.
- USB-serial có thể drop giữa chừng (log ghi `WARNING: serial read error` rồi
  `== serial port reopened ==`); script vẫn lưu phần đã bắt.

## Chế độ hiện tại: 1.000 lượt, 20 mẫu, đối chiếu số học với host trên bo
- 1 lần boot; vòng lặp **im lặng** (không in gì giữa `t0..t1`) → số đo thời gian sạch.
- `vTaskDelay(1)` sau mỗi lượt, **ngoài cửa sổ đo** → IDLE0 có CPU, không trigger task watchdog.
- 20 mẫu UCI thật, **đủ 6 lớp** (3 mẫu/lớp dự đoán host + 2 mẫu phụ): chỉ số
  `79,80,81,128,133,134,109,110,111,31,33,34,0,1,2,55,56,57,112,35` — đúng bytes
  `firmware/host/logs/uci_test.f32`; nhãn/logits tham chiếu từ
  `firmware/host/logs/uci_test_logits_final.csv` nhúng sẵn trong `src/uci_samples.h`.
- Bo tự tính `max|Δlogit|`, MAE trên 6.000 phép so (1.000 lượt × 6 logit) và đếm lệch nhãn.
  Vì 20 mẫu lặp lại 50 lần, thực chất chỉ có 120 cặp (mẫu × logit) khác nhau; hàm suy luận
  tất định nên các lần lặp cho cùng kết quả.
- Đây là số đo trên ESP32-S3 (Xtensa / ESP-IDF / build C). Ngưỡng sai số 1e-4 / 1e-5
  **chờ giảng viên xác nhận**; tài liệu chỉ ghi số đo, không kết luận theo ngưỡng nào.

## Truy vết firmware (biểu mẫu B.1)
- `scripts/gen_build_info.py` (PlatformIO `extra_scripts`) sinh `src/build_info.h` mỗi build:
  commit ngắn + trạng thái cây + giờ UTC. Firmware in ngay đầu log:
  `FW commit <sha> (clean|dirty) built <UTC> | opt=<mức tối ưu>`.
- `flash_and_log.ps1` ghi thêm `sha256 firmware.bin` + `firmware.elf` vào `upload_*.txt`.
- Quy trình: commit mã nguồn → build/nạp/log trong một lần chạy → commit log. Log mang commit
  và hash của đúng binary đã nạp.

## Log kỳ vọng
Log chính thức mới: `logs\esp32s3_har_20261103_202410.txt` (firmware `ccf239d`, cây sạch).
Log 20/10 `logs\esp32s3_har_20261020_134435.txt` vẫn giữ để đối chiếu lịch sử.

```
starting in 4 seconds...
starting in 3 seconds...
starting in 2 seconds...
starting in 1 seconds...
starting in 0 seconds...
FW commit ccf239d (clean) built 2026-11-03T13:24:18Z UTC | opt=debug(-Og)
Reset: reason=1 (POWERON) | boot #1 since RTC_NOINIT init
Previous test: none
ESP32-S3 HAR benchmark (target platform; error thresholds pending advisor confirmation)
Stability+numerics: 1000 runs x 20 UCI samples, quiet loop, WDT fed
Test start: boot #1 | free heap 385668 bytes
BENCH DONE: runs=1000 samples=20 invalid=0 label_mismatch=0
numerics vs host (Xtensa/ESP-IDF/C; error thresholds pending advisor confirmation): comparisons=6000 (distinct sample x logit pairs=120, each repeated 50x; deterministic) max|dlogit|=7.629e-06 MAE=9.157e-07
time_us: min=122162 p50=122227 p95=122263 max=122491 mean=122225 sd=30
heap: end=385452 min_ever=342196 bytes
heap every 50 runs (bytes): 385668 385668 ... (21 mốc, phẳng)
sample 0 (idx 79): pred=0 host_pred=0 max|d|=2.742e-06
... (20 dòng, mỗi mẫu 1 dòng)
Resets: boot_count=1 prev_test_interrupted=0 | power-on clean run
```
- `Reset:` + `Previous test:` + `Resets:` là firmware tự đo (không phải chuỗi cố định):
  `esp_reset_reason()`, bộ đếm `RTC_NOINIT`, và cờ `TEST_RUNNING` / `TEST_DONE` trong
  `RTC_NOINIT`. Trước vòng suy luận firmware đặt `TEST_RUNNING`; sau vòng đặt `TEST_DONE`.
  Nếu lần boot sau còn thấy `TEST_RUNNING`, dòng `Previous test:` ghi
  `INTERRUPTED (reset during test)` và `prev_test_interrupted=1`.
- So sánh bộ đếm ở đầu và cuối trong cùng một lần chạy không phát hiện được reset, vì sau
  reset dòng cuối không bao giờ được in. Bằng chứng "không reset" của một lần chạy sạch:
  `reason=1 (POWERON)`, đúng một dòng `Test start`, `Previous test: none`, và
  `boot_count=1 prev_test_interrupted=0`.
- `opt=debug(-Og)`: `sdkconfig.esp32s3` đang `CONFIG_COMPILER_OPTIMIZATION_DEBUG` → một phần
  lớn khoảng cách 122 ms vs 416 µs trên PC; chưa thử `-O2`/`-Os`.
- `7,629e-6 = 2^-17` ≈ 1 ULP float32 quanh |logit| ≈ 74 → lệch chủ yếu ở độ phân giải float32.
  Ngưỡng 1e-4 / 1e-5 **chưa được giảng viên xác nhận**; các số trên chỉ là số đo.
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
- 20 mẫu lấy từ tập test chỉ là kiểm tra sơ bộ, không đại diện cho toàn bộ 2.947 mẫu.
  "20/20 khớp" là khớp với **dự đoán của host**, không phải nhãn thật: mẫu idx 128 có
  nhãn thật lớp 2 nhưng cả host và bo đều dự đoán lớp 1.
- Build đang `-Og` ở 160 MHz, nên p50 ~122 ms không đại diện cho hiệu năng cuối.
- Chưa đo năng lượng, chưa có map file / stack high-water mark, chưa chạy toàn bộ 2.947 mẫu;
  những mục đó cần brief riêng.
- Dataset UCI HAR vẫn nằm ở `data/UCI HAR Dataset/` trên máy (đã gitignore). Cách tải lại:
  tải archive `archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip`,
  giải nén vào `data/UCI HAR Dataset/` (xem header `firmware/host/uci_har.py`).
- Board: **ESP32-S3-WROOM-1 N16R8** (`board = esp32-s3-devkitc-1`, flash 16 MB khai trong
  `platformio.ini`, PSRAM tắt); bo DevKitC-1 có 2 cổng USB — dùng cổng **UART/CH343**.
  Số COM thay đổi theo máy: log 20/10 dùng COM11, log chính thức 03/11 dùng COM4.

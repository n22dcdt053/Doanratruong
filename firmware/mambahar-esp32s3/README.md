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

## Chạy (thứ 3, 20/10)
Mở PowerShell:
```powershell
cd D:\DoanNhomQuy\firmware\mambahar-esp32s3
powershell -ExecutionPolicy Bypass -File .\scripts\flash_and_log.ps1
```
- Lần đầu (20/10 đã chạy): script build + nạp + bắt 35 giây log, tự lưu evidence vào `logs\`.
- Đã nạp rồi, chỉ đọc log: thêm `-SkipBuild -SkipUpload`
- Chỉ định cổng khi có nhiều COM: thêm `-Port COM11` (cổng USB-UART CH343; xem bằng `pio device list`).
- Không nhận cổng: cắm cáp USB-C **truyền dữ liệu**, hoặc bấm giữ BOOT khi cắm.

## Log kỳ vọng (bo tự reset mỗi ~17 giây)
```
starting in 5 seconds...
...
Input: UCI HAR test sample 0 (standardized, 570 floats)
Free heap before: <n> bytes
Model_Forward completed.
Prediction: <0..5>
Logits: <6 giá trị, 6 chữ số thập phân>
Elapsed time: <N> microseconds (<x.xx> milliseconds)
Free heap after: <n> bytes
Min free heap ever: <n> bytes
Restarting in 10 seconds...
```
Input hiện tại = **mẫu 0 của UCI HAR test set** (`src/uci_sample.h`, đúng bytes
`firmware/host/logs/uci_test.f32` mà host đã chạy) → so trực tiếp với dòng 0 của
`firmware/host/logs/uci_test_logits_final.csv` (host: pred **4**, logits
`-8.880633 -6.193293 -3.396970 2.071888 10.757054 -6.310842`). Ngày 20/10 trên bo:
pred 4, **max|Δlogit| 1,35e-6, MAE 5,0e-7** (in 6 chữ số nên sai số gồm cả làm tròn
khi in; ngưỡng tầng B: 1e-4 / 1e-5 — đây là bằng chứng sớm trên ESP32, **chưa thay
nghiệm thu Portenta H7**). `Prediction: -2` vẫn là nghĩa "logits không hữu hạn" khi
ai đó thay lại `sample_input.h` (mẫu demo sai thang). Heap: `before - min ever`
≈ đỉnh bộ nhớ suy luận (đúng yêu cầu "bộ nhớ sử dụng khi suy luận").

## Evidence tự động
- `logs\build_<timestamp>.txt` — output build (có bảng Flash/RAM) → trả lời yêu cầu
  "kiểm tra kích thước mô hình và bộ nhớ sử dụng khi suy luận".
- `logs\upload_<timestamp>.txt` — output nạp (kèm dòng `Hash of data verified`).
- `logs\esp32s3_har_<timestamp>.txt` — log serial thô.

## Giới hạn hiện tại (đúng như upstream, sửa sau theo đề cương)
- 1 mẫu duy nhất rồi reset (`sample_input.h` có 4000 float ≈ 7 mẫu, hiện chỉ dùng 570 đầu).
- Chỉ in nhãn argmax, chưa xuất 6 logits (MT2 sẽ làm).
- Board: **ESP32-S3-WROOM-1 N16R8** (`board = esp32-s3-devkitc-1`, flash 16 MB khai trong
  `platformio.ini`); bo DevKitC-1 có 2 cổng USB — dùng cổng **UART/CH343** (COM11 ngày 20/10).

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
- Lần đầu: script build + nạp + bắt 35 giây log, tự lưu evidence vào `logs\`.
- Đã nạp rồi, chỉ đọc log: thêm `-SkipBuild -SkipUpload`
- Không nhận cổng: cắm cáp USB-C **truyền dữ liệu**, hoặc bấm giữ BOOT khi cắm.

## Log kỳ vọng (bo tự reset mỗi ~17 giây)
```
starting in 5 seconds...
...
Free heap before: <n> bytes
Model_Forward completed.
Prediction: <0..5>
Elapsed time: <N> microseconds (<x.xx> milliseconds)
Free heap after: <n> bytes
Min free heap ever: <n> bytes
Restarting in 10 seconds...
```
`Prediction` phải nằm trong 0..5. Heap: `before - min ever` ≈ đỉnh bộ nhớ suy luận
(đúng yêu cầu "bộ nhớ sử dụng khi suy luận"). Muốn biết đúng/sai cần đối chiếu mẫu trong
`sample_input.h` (bước đối chiếu số học là việc tuần sau theo đề cương MT3).

## Evidence tự động
- `logs\build_<timestamp>.txt` — output build (có bảng Flash/RAM) → trả lời yêu cầu
  "kiểm tra kích thước mô hình và bộ nhớ sử dụng khi suy luận".
- `logs\esp32s3_har_<timestamp>.txt` — log serial thô.

## Giới hạn hiện tại (đúng như upstream, sửa sau theo đề cương)
- 1 mẫu duy nhất rồi reset (`sample_input.h` có 4000 float ≈ 7 mẫu, hiện chỉ dùng 570 đầu).
- Chỉ in nhãn argmax, chưa xuất 6 logits (MT2 sẽ làm).
- Board mặc định: `seeed_xiao_esp32s3`; đổi board khác chỉ cần sửa `board =` trong `platformio.ini`.

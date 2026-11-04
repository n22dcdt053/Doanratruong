# mamba-retrained-esp32s3 — Mamba HAR trên ESP32-S3 với trọng số huấn luyện lại (seed 42)

## Mục đích
Firmware Mamba HAR (6 lớp) chạy trên **ESP32-S3** bằng bộ trọng số **huấn luyện lại** trên
`ml/split_manifest.csv`, để so với firmware MLP đối chứng trên **cùng bo, cùng tập chia, cùng
khung đo** (MT5). Đây là bản song song của project `firmware/mambahar-esp32s3/` (bản đó chạy
trọng số công khai và được giữ nguyên làm bằng chứng cho bộ trọng số công khai).

Khác biệt so với project cũ đúng ở hai chỗ:
- `platformio.ini` thêm `-I../../ml/results/mamba_retrained` **đầu tiên**, để
  `mamba_weights.h` của bản huấn luyện lại thắng bản công khai trong `MambaLite-Micro/`;
- `src/uci_samples.h` mang logit/dự đoán tham chiếu của bộ trọng số mới (cùng 20 mẫu, cùng
  đầu vào bit-exact).

Mọi thứ còn lại (cấu trúc suy luận, `sdkconfig.esp32s3`, vòng đo 1.000 lượt × 20 mẫu, cờ
`TEST_RUNNING`/`TEST_DONE`, cách tính thống kê, `-Og` ở 160 MHz) giữ nguyên như bản cũ.

## Nguồn trọng số
- `ml/results/mamba_retrained/mamba_weights.h` — sinh bởi `ml/export_mamba_c.py`.
- Checkpoint: `ml/results/mamba_retrained/mamba_seed42.pt`
  sha256 `f742597b772f609968040e0ffc22f50b011a996ebf3c05fdbdfa8ec95b6f7839`.
- Header: sha256 `5d8499d2dfb07e425814492b17ab83368cd6e8c199895d4c69493905d9687c50`
  (in `%.9e`, khác `%.8f` của header công khai; xem `REPORT_03.md`).
- Bộ mẫu nhúng: `ml/gen_mamba_retrained_samples.py` (đọc lại chỉ số từ project cũ, assert
  20 × 570 giá trị bit-exact với `uci_samples` cũ và với `data/UCI HAR Dataset/test/X_test.txt`).
- Nguồn upstream: `..\..\MambaLite-Micro` (commit `44d51fc`, MIT) — **không sửa**; kernel +
  wrapper vendor ở `..\common\mamba.c` / `..\common\mambahar.c` — **không sửa** trong brief này.

## Build (PC, không cần bo)
```powershell
cd firmware\mamba-retrained-esp32s3
pio run -j 1
```
- `pio` nằm ở `C:\Users\Admin\.platformio\penv\Scripts` (thêm vào `PATH` nếu cần).
- `-j 1` vì xtensa-gcc 8.4 ICE ở `esp_lcd_panel_rgb.c` khi build song song.
- Build ghi `src/build_info.h` (commit ngắn + trạng thái cây + giờ UTC) trước mỗi lần build.

## Chạy trên bo (người kiểm tra chạy, không phải brief này)
```powershell
cd firmware\mamba-retrained-esp32s3
powershell -ExecutionPolicy Bypass -File .\scripts\flash_and_log.ps1 -DurationSec 155
```
- Script tự build (trừ khi `-SkipBuild`) + nạp + bắt log `DurationSec` giây, lưu
  `logs\build_*.txt`, `logs\upload_*.txt`, `logs\esp32s3_har_*.txt`.
- Đã nạp rồi, chỉ đọc log: thêm `-SkipBuild -SkipUpload`.
- Chỉ định cổng khi có nhiều COM: thêm `-Port COMx` (xem bằng `pio device list`).

## Log kỳ vọng (định tính; chưa chạy trên bo nên không có số thời gian ở đây)
Các dòng khóa phải xuất hiện đúng như sau (giá trị commit/giờ do firmware tự in):

```
FW commit <sha> (clean) built <UTC> UTC | opt=debug(-Og)
Reset: reason=1 (POWERON) | boot #1 since RTC_NOINIT init
Previous test: none
ESP32-S3 Mamba-HAR (retrained, seed 42) benchmark (control comparison; error thresholds pending advisor confirmation)
Test start: boot #1 | free heap <n> bytes          <- đúng một dòng
BENCH DONE: runs=1000 samples=20 invalid=0 label_mismatch=0
...
Resets: boot_count=1 prev_test_interrupted=0 | power-on clean run
```
- `Reset:` / `Previous test:` / `Resets:` là firmware tự đo (`esp_reset_reason()`, bộ đếm
  `RTC_NOINIT`, cờ `TEST_RUNNING`/`TEST_DONE`), không phải chuỗi cố định.
- `label_mismatch` ở đây là lệch so với **dự đoán tham chiếu của C trên PC** (cùng bộ trọng số),
  không phải nhãn thật.
- `invalid=0` nghĩa là không lượt nào trả `-2` ("logits không hữu hạn").

## Giới hạn
- Build `-Og` ở 160 MHz: thời gian đo được **không** đại diện cho hiệu năng cuối (chưa thử
  `-O2`/`-Os`/240 MHz).
- Chỉ 20 mẫu test và 1 seed: kiểm tra sơ bộ, không đại diện toàn bộ 2.947 mẫu.
- Chưa đo năng lượng, chưa có GPIO marker, chưa có map file / stack high-water mark.
- Ngưỡng sai số 1e-4 / 1e-5 **chờ giảng viên xác nhận**: tài liệu chỉ ghi số đo, không kết luận
  theo ngưỡng nào và không kết luận mô hình nào tốt hơn.
- Thư mục `logs/` của project này để trống (chỉ `.gitkeep`); log chỉ được thêm sau khi chạy bo.

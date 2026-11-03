# MLP 561-64-6 trên ESP32-S3 — firmware đối chứng

Mô hình đối chứng cho MT5: cùng bo ESP32-S3, cùng cấu hình build, cùng 20 mẫu UCI
và cùng khung đo 1000 lượt × 20 mẫu như firmware Mamba. Đây là firmware MLP
FP32 561-64-6; không biên dịch mã nguồn Mamba hay MambaLite-Micro.

**Chưa chạy trên bo.** Việc chạy và tạo log do người kiểm tra thực hiện.

## Nguồn trọng số

- Checkpoint: `ml/results/mlp_seed42.pt`,
  sha256 `0999a6a7a73afcb752b99275f640254d4d20c2231079eb0bc5330b7470701239`.
- Header sinh tự động: `firmware/common/mlp_weights.h`,
  sha256 `398dd42647171f99058628b129dd27e83a95d708c57bfb24b581c02e86bdf758`
  (145.432 byte float32; `ml/export_mlp_c.py` sinh lại từ checkpoint).
- Bộ mẫu: `src/mlp_samples.h`, sinh bởi `ml/gen_mlp_samples.py` từ 20 chỉ số
  `uci_index` của `firmware/mambahar-esp32s3/src/uci_samples.h`.
- Suy luận: `firmware/common/mlp_har.c` (561 → 64 ReLU → 6, FP32, không cấp phát động).

## Cấu hình build

Giống project Mamba: `board = esp32-s3-devkitc-1`, `platform = espressif32 @ 6.9.0`,
`framework-espidf @ 3.50301.0`, `framework = espidf`, `sdkconfig.esp32s3` copy
byte-identical (sha256 `9d48f45c0d4aef6ac07f5656ef7eb1353ef0f82aeba10b36637456b76c42cfeb`),
tối ưu `-Og`, CPU 160 MHz. Khác biệt duy nhất: không có các `-I` trỏ vào
`MambaLite-Micro`.

## Build

```powershell
cd firmware\mlp-esp32s3
pio run -j 1
```

Kết quả build trên PC (xem `docs/briefs/REPORT_04.md`): Flash 401.516 B
(38,3% của 1.048.576 B), RAM 17.148 B (5,2% của 327.680 B).

## Chạy trên bo (người kiểm tra)

```powershell
cd firmware\mlp-esp32s3
powershell -ExecutionPolicy Bypass -File .\scripts\flash_and_log.ps1 -DurationSec 45
```

Thêm `-Port COMx` nếu máy có nhiều cổng USB-serial. Script build + nạp + ghi log
vào `logs\`; mặc định đo 45 giây. Không chạy lệnh này trong quá trình phát triển
trên PC.

## Log kỳ vọng định tính

Không điền số thời gian vì chưa chạy trên bo. Các dòng khóa cần có:

```text
FW commit <hash> (clean) built <UTC> | opt=debug(-Og)
Reset: reason=1 (POWERON) | boot #1 since RTC_NOINIT init
Previous test: none
BENCH DONE: runs=1000 samples=20 invalid=0 label_mismatch=0
Resets: boot_count=1 prev_test_interrupted=0 | power-on clean run
```

`label_mismatch` so với **dự đoán tham chiếu của MLP chạy trên host C**
(`ml/results/mlp_c_logits_test.csv`), không phải nhãn thật. Dòng numerics ghi
`vs host C (MLP)` với 120 cặp sample × logit, mỗi cặp lặp 50 lần.

## Giới hạn

- Build `-Og` ở 160 MHz; số thời gian (khi có log) không đại diện cho hiệu năng cuối.
- Chỉ 20 mẫu test, 1 seed huấn luyện; chưa đo năng lượng/GPIO marker.
- Ngưỡng sai số 1e-4 / 1e-5 vẫn chờ giảng viên xác nhận; log chỉ báo số đo.
- Chưa có Mamba retrain trên cùng `ml/split_manifest.csv`, nên chưa so sánh
  thời gian/bộ nhớ giữa hai mô hình.

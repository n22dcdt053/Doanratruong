# BÁO CÁO TIẾN ĐỘ — 04/11/2026

Đề tài: Mamba HAR (UCI HAR, 6 lớp) trên vi điều khiển · Nhóm: Nguyễn Mai Trọng Quý (N22DCDT053), Võ Trung Nhân (N22DCDT043), Đinh Hữu Phước (N22DCDT047) · GVHD: TS. Nguyễn Thanh Bình

Báo cáo này thay thế báo cáo 20/10/2026 ở những chỗ hai bản khác nhau (báo cáo 20/10 mô tả Portenta H7 là đích và ESP32-S3 là proxy; nay nền tảng chính là ESP32-S3). Bằng chứng nằm trong nhánh `dev` (mốc `81a2515`, đã gộp 45 commit), mỗi mốc có code, log chạy thật và manifest.

Trạng thái chung: đã có đủ **hai mô hình (Mamba huấn luyện lại, MLP đối chứng) trên cùng tập chia theo người, cùng bo, cùng cấu hình build**, có kiểm chứng số học C↔PyTorch trên PC, có thống kê bootstrap theo người. **Chưa có** số đo năng lượng, chưa chạy đủ 2.947 mẫu trên bo, chưa có map file/stack.

## Đã xong

1. **Chuyển nền tảng.** Theo trao đổi qua tin nhắn với thầy, nhóm chuyển đích sang ESP32-S3 (devkit N16R8), không còn yêu cầu Portenta H7. Nhóm xin thầy xác nhận bằng văn bản/điều chỉnh đề cương (xem mục xin ý kiến).
2. **Chia dữ liệu theo người** (`ml/split_manifest.csv`, `GroupShuffleSplit` seed 42): train 5.551 / val 1.801 (người 1, 3, 15, 25, 27) / test 2.947 (9 người gốc). Có script kiểm các tập không giao nhau.
3. **MLP đối chứng 561-64-6 (ReLU, FP32, 36.358 tham số)** train theo Bảng 2 (Adam 1e-3, batch 64, ≤100 epoch, dừng sớm 10 theo macro-F1 val, seed 42), export sang C, kiểm riêng trên PC.
4. **Mamba huấn luyện lại** (gate #1) theo cùng quy trình và cùng tập chia: PyTorch thuần chạy CPU (36.742 tham số), dựng theo đặc tả `firmware/common/mamba.c`. **Không dùng `mamba_ssm`** vì máy nhóm không có CUDA (xem mục xin ý kiến). Trọng số công khai chỉ giữ cho kiểm chứng số học.
5. **Chất lượng phân loại trên test (2.947 mẫu, 9 người, 1 seed):**

   | | Mamba (huấn luyện lại) | MLP |
   |---|---|---|
   | Accuracy | 0,9298 | 0,9403 |
   | Macro-F1 | 0,9273 | 0,9400 |

   Bootstrap CI 95% theo cụm người (B = 2.000, seed 42, ghép cặp): Δ macro-F1 (Mamba − MLP) = −1,27 điểm % [−3,11; +0,66]; Δ accuracy = −1,05 điểm % [−2,60; +0,75]. Bỏ-một-người: ΔF1 trong khoảng −1,90 … −0,58. Khoảng tin cậy chứa 0; chỉ có 9 người test và 1 seed, nên **nhóm chưa kết luận mô hình nào tốt hơn**.
6. **Kiểm chứng C ↔ PyTorch trên PC** (0 lệch nhãn ở cả ba bộ trọng số): MLP max|Δlogit| 1,43e-5; Mamba huấn luyện lại 2,21e-4 (2.947 mẫu); Mamba trọng số công khai 1,88e-4 (7.352 mẫu train).
7. **Chạy thật trên ESP32-S3 (devkit N16R8)**, ba firmware cùng `sdkconfig` (giống từng byte), `-Og`, 160 MHz, 1.000 lượt × 20 mẫu nhúng, khởi động nguội, không reset giữa chừng, `invalid=0`, `label_mismatch=0` (so với dự đoán host):

   | Firmware | FW commit | p50 / lượt | max\|Δlogit\| vs host | Flash |
   |---|---|---|---|---|
   | Mamba, trọng số công khai | `ccf239d` | 122.227 µs | 7,629e-6 | 408.492 B |
   | Mamba, huấn luyện lại | `8c0ac36` | 121.973 µs | 1,526e-5 | 408.524 B |
   | MLP | `667430b` | 10.666 µs | 0 | 401.516 B |

   Log: `firmware/{mambahar-esp32s3,mamba-retrained-esp32s3,mlp-esp32s3}/logs/`. Thời gian đo ở `-Og` nên **không đại diện hiệu năng thật**; "khớp 20/20" so với dự đoán host, không phải nhãn thật.
8. Từ 18–20/10 (không đổi): sửa rò rỉ bộ nhớ và đọc quá biên ở mã kế thừa, ASan/UBSan/LSan sạch, A/B upstream↔bản dev và gcc↔g++ bit-exact trên 2.947 mẫu (phụ lục `reports/KIEM_CHUNG_SO_HOC_PC_20261020.md`).

## Chưa làm

- Nhận mẫu qua UART (PC→MCU, gói 570 float + checksum) và chạy đủ 2.947 mẫu trên bo; hiện chỉ 20 mẫu nhúng trong flash.
- GPIO marker bao vùng suy luận và **đo năng lượng** (phương án dự kiến: INA226 + một bo ESP32-S3 khác làm logger; chưa dựng, chưa có số).
- Flash/RAM theo map file + linker script ESP32-S3, tách tĩnh / heap / stack (hiện chỉ có số PlatformIO).
- Bootstrap/thống kê cho thời gian và năng lượng; hình vẽ (confusion matrix, forest plot, phân bố độ trễ).
- Thử `-O2`/`-Os`, nhiều seed huấn luyện (hiện 1 seed).
- Thuyết minh.

## Kính xin ý kiến

1. **Xác nhận bằng văn bản việc chuyển sang ESP32-S3** (hoặc điều chỉnh đề cương) và cách gọi trong báo cáo cuối: ESP32-S3 là nền tảng nghiệm thu, không còn là "proxy".
2. **Ngưỡng sai số.** Nhóm đã ghi trước hai tầng: C↔PyTorch max ≤1e-3 / MAE ≤1e-4; MCU↔C max ≤1e-4 / MAE ≤1e-5. Số đo hiện thấp hơn các mức này (ví dụ MCU↔C: max 1,526e-5, MAE 1,03e-6 với Mamba huấn luyện lại), nhưng vì ngưỡng chưa được thầy xác nhận nên nhóm chưa ghi "đạt".
3. **Mô hình Mamba huấn luyện lại là bản PyTorch viết lại**, không phải `mamba_ssm` gốc, nên chưa đối chiếu trực tiếp tuyên bố "100% khớp" của bài báo. Nhờ thầy cho biết cách này có chấp nhận được không, hay cần thêm một lần chạy `mamba_ssm` trên Colab/WSL.
4. **Đo năng lượng:** nhờ thầy góp ý phương án (INA226 + logger tự dựng, hay mượn PPK2 nếu phòng lab có) và thời hạn.
5. **Ít người trong tập test (9) và 1 seed:** nhờ thầy cho biết có cần chạy thêm seed huấn luyện, hay chỉ cần nêu giới hạn trong báo cáo.
6. §11.3 ghi "nhóm hai sinh viên" nhưng nhóm có 3 bạn; nhờ thầy chốt cách chia (đã nêu ở báo cáo 20/10).

## Kế hoạch 1–2 tuần

UART + chạy đủ 2.947 mẫu trên bo (MT3 tầng B đầy đủ) → GPIO marker + dựng phép đo năng lượng → map file/stack → hình và bảng tổng hợp. Nếu thầy yêu cầu thêm seed hoặc `mamba_ssm`, nhóm làm sau khi có ý kiến.

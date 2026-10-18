# BÁO CÁO TIẾN ĐỘ — 20/10/2026

**Đề tài:** Mamba HAR trên STM32H7 (Portenta H7) · **Nhóm:** Nguyễn Mai Trọng Quý (N22DCDT053), Võ Trung Nhân (N22DCDT043), Đinh Hữu Phước (N22DCDT047) · **GVHD:** TS. Nguyễn Thanh Bình

**Mốc kiểm soát Bảng 7 (hết tuần 2):** tái lập mẫu gốc + **quyết định checkpoint**. Trạng thái: tái lập ✅ (số liệu dưới); quyết định checkpoint chờ chốt môi trường huấn luyện — kính nhờ thầy trả lời sớm.

**Trạng thái:** chưa có bo Portenta H7. Các phần không cần bo đã xong, bằng chứng lưu bằng commit + log (nhánh `dev`, commit bằng chứng `66d444c`).

## Đã xong (không cần bo)

1. **Tái lập + kiểm chứng số học trên máy tính nhóm** (Windows gọi qua PowerShell → chương trình chạy trong WSL Ubuntu, gcc/g++ 13.3, x86-64; **không phải** giả lập phần cứng): chạy hết **2.947 mẫu test UCI HAR** — accuracy **92,67%**, macro-F1 **92,65%**, 0 mẫu NaN/không hợp lệ (confusion matrix trong phụ lục). Trọng số công khai, chỉ dùng tham chiếu MT1/MT3 — **không** đưa vào bảng so sánh Mamba↔MLP.
2. **Chốt "upstream gốc ≡ bản cuối" trên chính 2.947 mẫu thật** (cùng runner host, chỉ khác 2 file mô hình): dự đoán khớp từng mẫu; các bản CSV logits (trước/sau vendor `mamba.c`, bản cuối) trùng từng byte. Phạm vi khẳng định: **chỉ cho đầu ra hữu hạn** (UCI chuẩn hóa: 0 NaN). Lưu ý kỹ thuật: firmware biên dịch mô hình bằng **C++** (`arm-none-eabi-g++`, qua `main.cpp` + `extern "C"`), host dùng gcc **C** — đã kiểm A/B `g++ ≡ gcc` bit-exact trên 2.947 mẫu; phần còn lại (target ARM Cortex-M7, newlib/FPU) sẽ chốt bằng đo trên bo (dung sai tầng B).
3. **Sửa 2 lỗi mã nguồn kế thừa, có bằng chứng trước/sau**: rò rỉ ~8,1 KB/lượt (ước tính — chưa đo trên bo: nếu giữ nguyên thì RAM 511 KB hết sau ~60 lượt) và 1 lỗi đọc quá biên (`mamba.c:94`). ASan/UBSan/LSan nay **sạch trên 4 lượt chạy**: 1 mẫu (2 chế độ), **1.000 lượt liên tiếp**, và **cả batch 2.947 mẫu hữu hạn**.
4. **Build thành công firmware Portenta H7:** Flash **307.368 B / 768 KB**; RAM tĩnh **77.256 B / 511 KB** (heap đỉnh + stack đo riêng khi có bo). **ESP32-S3 chỉ là nền thử giao thức, ngoài phạm vi bắt buộc — đích nghiệm thu là Portenta H7.**
5. **Chốt trước dung sai MT3** (ghi nhật ký trước khi so số thật): hai tầng — A (C↔PyTorch) max ≤1e-3 / MAE ≤1e-4; B (MCU↔C) max ≤1e-4 / MAE ≤1e-5; mẫu biên top-2 hẹp liệt kê riêng. **Kính xin thầy xác nhận trước khi đánh giá chính thức.**

## Kính xin ý kiến (đường găng)

- **Bo + bộ đo — đề nghị chốt trước 25/10/2026** (lead time mua/mượn; không có bo là không thể nghiệm thu):
  - Bo: **Portenta H7 (ABX00042)** + cáp USB-C truyền dữ liệu.
  - Đo năng lượng: **khuyến nghị PPK2** (mượn/mua) — đo được theo từng lượt/pha như Bảng 3. Nếu chỉ có **INA226**: vẫn dùng được nhưng nhiều khả năng chỉ báo **năng lượng trung bình theo khối** (mất phân giải từng lượt) — nhóm sẽ ghi rõ phương pháp trong hồ sơ đo.
- **Môi trường huấn luyện lại:** kế hoạch của nhóm là **PyTorch thuần CPU trên máy nhóm** (mô hình ~36,7k tham số, không cần GPU); chỉ xin dùng WSL/Colab nếu phát sinh phụ thuộc `mamba_ssm`. Hạn mốc: xác nhận trong 2 tuần đầu (§7.4).
- §11.3 ghi "nhóm hai sinh viên" nhưng nhóm có 3 bạn — nhờ thầy chốt cách chia.

## Kế hoạch 1–2 tuần (theo Bảng 7)

Chia dữ liệu theo người (`GroupShuffleSplit` seed 42) → **huấn luyện lại + quyết định checkpoint** (mốc tuần 2–3) → khi có bo: flash Portenta, **1.000 lượt liên tiếp**, đo Flash/RAM theo map file (tách tĩnh/heap/stack) + năng lượng; song song hoàn thiện giao thức nhận gói trên ESP32 (chỉ để thử giao thức, không thay thế nghiệm thu).

## Phụ lục

`docs/KIEM_CHUNG_SO_HOC_PC_20261020.md` — sinh tự động từ log thật: A/B `gcc↔g++` và `upstream↔bản dev` trên 2.947 mẫu, ASan mở rộng, chấm điểm UCI + confusion matrix, log thô, **sha256 từng file** + commit HEAD của cây sinh ra phụ lục. Commit bằng chứng: `66d444c`.

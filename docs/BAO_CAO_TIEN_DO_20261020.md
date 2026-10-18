# BÁO CÁO TIẾN ĐỘ — 20/10/2026

**Đề tài:** Mamba HAR trên STM32H7 (Portenta H7) · **Nhóm:** Nguyễn Mai Trọng Quý (N22DCDT053), Võ Trung Nhân (N22DCDT043), Đinh Hữu Phước (N22DCDT047) · **GVHD:** TS. Nguyễn Thanh Bình

**Trạng thái:** chưa có bo Portenta H7. Các phần không cần bo đã xong, bằng chứng lưu kèm (commit + log).

## Đã xong

1. **Bản C tham chiếu chạy trực tiếp trên máy tính nhóm** (đúng mã nguồn C sẽ nạp lên bo: Windows gọi qua PowerShell, chương trình chạy trong WSL Ubuntu, gcc; không phải giả lập phần cứng) — chạy hết **2.947 mẫu test UCI HAR**: accuracy **92,67%**, macro-F1 **92,65%**, 0 mẫu NaN. Trọng số công khai, chỉ dùng cho kiểm chứng số học (không dùng so sánh Mamba ↔ MLP).
2. **Sửa 2 lỗi của mã nguồn kế thừa, có bằng chứng trước/sau** (ASan/LSan + log RSS): rò rỉ ~8,1 KB mỗi lượt (nếu không sửa thì hết RAM sau ~60 lượt — không thể đạt yêu cầu 1.000 lượt) và đọc quá biên bộ nhớ. Kiểm chứng: kết quả số học **giữ nguyên từng byte** (bit-exact trên 2.947 mẫu).
3. **Build thành công firmware Portenta H7:** Flash 307.368 B / 768 KB; RAM tĩnh 77.256 B / 511 KB (heap đỉnh và stack sẽ đo riêng khi có bo). Firmware ESP32-S3 (bản luyện tập, **không thay thế nghiệm thu**) build OK, chờ cắm bo để đọc log.
4. **Chốt trước dung sai kiểm chứng C ↔ PyTorch ↔ MCU** (ghi nhật ký trước khi so số thật): hai tầng — A (C ↔ PyTorch) 1e-3 / MAE 1e-4; B (MCU ↔ C) 1e-4 / MAE 1e-5; mẫu biên top-2 hẹp liệt kê riêng. **Kính xin thầy xác nhận trước khi đánh giá chính thức.**

## Kính xin ý kiến

- Phần cứng: mua **Portenta H7 (ABX00042)** + cáp USB-C truyền dữ liệu; bộ đo năng lượng dùng **PPK2 hay phương án INA226**?
- Huấn luyện lại Mamba theo Bảng 2 (mốc 2 tuần đầu): dùng máy của nhóm hay Colab/WSL?
- Đề cương ghi "nhóm hai sinh viên", nhóm có 3 bạn — nhờ thầy chốt lại.

## Kế hoạch 1–2 tuần tới

Chia dữ liệu theo người (GroupShuffleSplit seed 42) → huấn luyện lại → khi có bo: chạy 1.000 lượt liên tiếp + đo Flash/heap/thời gian; song song hoàn thiện giao thức nhận gói trên ESP32.

## Phụ lục kèm theo

`docs/NGHIEM_THU_SO_HOC_HOST_20261020.md` — code kiểm chứng nguyên văn (mục 3), log thô (mục 4), checksum SHA-256 từng file (mục 6). Sinh tự động bằng `python firmware/host/make_evidence_bundle.py`.

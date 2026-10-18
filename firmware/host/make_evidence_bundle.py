#!/usr/bin/env python3
"""Sinh phụ lục nghiệm thu (1 file markdown) từ code + log thực tế trong repo.

    python firmware/host/make_evidence_bundle.py
    -> NGHIEM_THU_SO_HOC_HOST_20261020.md  (repo root)

File sinh tự động — đừng sửa tay; chạy lại script sau mỗi đợt đo mới.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "firmware" / "host"
LOGS = HOST / "logs"
OUT = ROOT / "NGHIEM_THU_SO_HOC_HOST_20261020.md"

EMBEDDED: list[Path] = []


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def read_text(p: Path) -> str:
    """Doc text bat ke encoding thuc te (log PowerShell 5.1 la UTF-16 co BOM)."""
    raw = p.read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    if b"\x00" in raw:
        return raw.decode("utf-16-le", errors="replace")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def block(title: str, path: Path, lang: str = "text") -> str:
    EMBEDDED.append(path)
    text = read_text(path).rstrip()
    rel = path.relative_to(ROOT).as_posix()
    return f"### {title}\n\n`{rel}`\n\n```{lang}\n{text}\n```\n"


def tail_block(title: str, path: Path, lines: int = 8) -> str:
    EMBEDDED.append(path)
    all_lines = read_text(path).splitlines()
    text = "\n".join(all_lines[-lines:])
    rel = path.relative_to(ROOT).as_posix()
    return f"### {title}\n\n`{rel}` — {lines} dòng cuối\n\n```text\n{text}\n```\n"


def line_diff(a: Path, b: Path) -> tuple[bool, int]:
    if a.read_bytes() == b.read_bytes():
        return True, 0
    la = read_text(a).splitlines()
    lb = read_text(b).splitlines()
    d = sum(1 for x, y in zip(la, lb) if x != y) + abs(len(la) - len(lb))
    return False, d


parts: list[str] = []
A = parts.append

A("# PHỤ LỤC NGHIỆM THU — kiểm chứng số học trên máy tính (không cần bo)\n")
A("Ngày 18–20/10/2026 · Nhóm: Nguyễn Mai Trọng Quý (N22DCDT053), Võ Trung Nhân (N22DCDT043), "
  "Đinh Hữu Phước (N22DCDT047) · GVHD: TS. Nguyễn Thanh Bình\n")
A("File sinh tự động: `python firmware/host/make_evidence_bundle.py` — đừng sửa tay.\n")

A("## 0. Phạm vi tài liệu này\n")
A("- Môi trường: **máy tính của nhóm — Windows gọi qua PowerShell, chương trình chạy trong WSL Ubuntu 24.04, "
  "gcc 13.3, x86-64**. Không có bo nào tham gia.\n")
A("- Kiểm chứng **số học**: đúng/sai kết quả, rò rỉ bộ nhớ, hành vi với đầu vào lỗi, của **đúng mã nguồn C "
  "sẽ nạp lên bo** (cùng bản vendor `firmware/common/`).\n")
A("- **Không thay thế** bài test trên phần cứng: Flash/RAM theo map file, heap Mbed, 1.000 lượt liên tiếp, "
  "thời gian, năng lượng — chỉ số đo trên Portenta H7 mới tính là bằng chứng nghiệm thu.\n")
A("- Thời gian in ra là wall clock của PC, **không phải** thời gian MCU.\n")

A("## 1. Cách tái tạo toàn bộ file này\n")
A("```powershell\n"
  "cd D:\\DoanNhomQuy\n"
  "# 1 lượt (mẫu demo -> báo đầu ra không hợp lệ), 1000 / 4000 lượt (kiểm rò rỉ)\n"
  "powershell -ExecutionPolicy Bypass -File .\\firmware\\host\\run_host_test.ps1 -Iterations 1\n"
  "powershell -ExecutionPolicy Bypass -File .\\firmware\\host\\run_host_test.ps1 -Iterations 1000\n"
  "# chạy lô N mẫu từ file .f32 -> CSV (idx,pred,6 logits)\n"
  "powershell -ExecutionPolicy Bypass -File .\\firmware\\host\\run_host_test.ps1 -Batch .\\firmware\\host\\logs\\batch_demo.f32 -OutName out.csv\n"
  "# ASan + UBSan + LSan (chạy trong WSL)\n"
  "wsl -e bash /mnt/d/DoanNhomQuy/firmware/host/run_asan.sh\n"
  "# UCI HAR: chuyển tập test -> .f32 và chấm điểm\n"
  "python .\\firmware\\host\\uci_har.py to-f32 \"D:\\DoanNhomQuy\\data\\UCI HAR Dataset\" .\\firmware\\host\\logs\\uci_test.f32\n"
  "python .\\firmware\\host\\uci_har.py score .\\firmware\\host\\logs\\uci_test_logits_final.csv \"D:\\DoanNhomQuy\\data\\UCI HAR Dataset\"\n"
  "# đối chiếu bit-exact (cmp khớp từng byte)\n"
  "wsl -e bash -c \"cd /mnt/d/DoanNhomQuy/firmware/host/logs && cmp fixed_logits.csv v2_batch201_logits.csv && echo BIT-EXACT\"\n"
  "```\n")
A("Dataset: UCI HAR Dataset (archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip), "
  "giải nén vào `data/` (không commit, .gitignore).\n")

A("## 2. Kết quả chính\n")
A("### 2.1 Rò rỉ bộ nhớ — trước/sau khi sửa (log 4.1–4.2)\n")
A("| | RSS 1000 lượt | RSS 4000 lượt |\n|---|---|---|\n"
  "| Trước sửa | +8.416 KB (tăng tuyến tính ~8,4 KB/lượt) | +32.460 KB |\n"
  "| Sau sửa | **+496 KB** | **+500 KB** (thêm 4 KB khi gấp 4 lần số lượt) |\n")
A("Mức +496/500 KB là lần chạm trang đầu tiên của glibc (trọng số + allocator), không tăng theo số lượt "
  "-> đạt yêu cầu \"không rò rỉ\". Trước sửa: RAM H7 511 KB sẽ hết sau ~60 lượt -> không thể đạt yêu cầu 1.000 lượt.\n")

A("### 2.2 ASan / LSan / UBSan (log 4.4–4.7)\n")
A("- Trước sửa: `8128 byte(s) leaked in 6 allocation(s)` + `heap-buffer-overflow READ of size 4` tại "
  "`csrc/mamba.c:94`.\n- Sau sửa rò rỉ: hết leak. Sau khi vendor `mamba.c` (sửa 1 dòng vòng chép `xz`): "
  "**sạch hoàn toàn**, không còn report nào.\n")

A("### 2.3 Tập test UCI HAR, bản C tham chiếu (log 4.8–4.9)\n")
A("Toàn bộ **2.947 mẫu test**, trọng số công khai, chấm theo `y_test.txt` (trừ 1 do nhãn gốc 1..6, khớp "
  "`train.py` dòng 39):\n\n"
  "| Chỉ số | Giá trị |\n|---|---|\n"
  "| Accuracy | **0,9267** |\n| Macro-F1 | **0,9265** |\n| F1 theo lớp | 0,937 / 0,913 / 0,949 / 0,879 / 0,904 / 0,978 |\n"
  "| Số mẫu NaN / không hợp lệ | **0 / 0** |\n")
A("Ý nghĩa: pipeline (tiền xử lý -> 6 logits -> argmax) khớp dữ liệu thật; đây **chỉ là điểm tham chiếu cho "
  "kiểm chứng số học MT1/MT3**, không dùng trong bảng so sánh Mamba↔MLP (checkpoint công khai chọn bằng "
  "validation chia ngẫu nhiên).\n")

same1, _ = line_diff(LOGS / "baseline_logits.csv", LOGS / "fixed_logits.csv")
same2, _ = line_diff(LOGS / "fixed_logits.csv", LOGS / "v2_batch201_logits.csv")
same3, _ = line_diff(LOGS / "uci_test_logits_pre_mamba.csv", LOGS / "uci_test_logits_post_mamba.csv")
same4, _ = line_diff(LOGS / "uci_test_logits_post_mamba.csv", LOGS / "uci_test_logits_final.csv")
same5, d5 = line_diff(LOGS / "v2_batch201_logits.csv", LOGS / "v3_batch201_logits.csv")

A("### 2.4 Đối chiếu bit-exact (`cmp`) — sửa code không đổi kết quả\n")
A("| Cặp file | Kết quả |\n|---|---|\n"
  f"| baseline_logits.csv vs fixed_logits.csv (sau sửa rò rỉ) | {'khớp từng byte' if same1 else 'KHÁC'} |\n"
  f"| fixed_logits.csv vs v2_batch201_logits.csv (sau vendor mamba.c) | {'khớp từng byte' if same2 else 'KHÁC'} |\n"
  f"| uci pre_mamba vs post_mamba (2.947 mẫu, sau vendor mamba.c) | {'khớp từng byte' if same3 else 'KHÁC'} |\n"
  f"| uci post_mamba vs final (sau thêm kiểm tra isfinite) | {'khớp từng byte' if same4 else 'KHÁC'} |\n"
  f"| v2 vs v3 (trước/sau thêm kiểm tra isfinite) | khác **{d5} dòng** — đúng dự kiến: cột pred của mẫu demo đổi 0 -> -2 |\n")

A("### 2.5 Mẫu demo sai thang đầu vào -> báo không hợp lệ (log 4.10)\n")
A("Mẫu demo `sample_input.h` (thang thô ~ -39) cho logits NaN; trước đây bị tính thành lớp 0 (argmax trên "
  "NaN luôn sai) — **không phải dự đoán thật**. Bản vendor hiện tại kiểm `isfinite` cả 6 logits -> trả `-2` "
  "và in `Output: INVALID`. Dữ liệu UCI chuẩn hóa không có mẫu NaN nào, xác nhận nguyên nhân là thang đầu vào.\n")

A("## 3. Code kiểm chứng (nguyên văn)\n")
A(block("3.1 `host_main.c` — chương trình tham chiếu chạy trên PC (dùng chung mã nguồn với firmware)",
        HOST / "host_main.c", "c"))
A(block("3.2 `run_host_test.ps1` — điểm vào trên Windows", HOST / "run_host_test.ps1", "powershell"))
A(block("3.3 `run_host_test.sh` — biên dịch + chạy bằng gcc trong WSL", HOST / "run_host_test.sh", "bash"))
A(block("3.4 `run_asan.sh` — ASan + UBSan + LSan", HOST / "run_asan.sh", "bash"))
A(block("3.5 `uci_har.py` — chuyển UCI HAR sang .f32 + chấm điểm", HOST / "uci_har.py", "python"))
A(block("3.6 `make_batch.py` — sinh lô mẫu kiểm thử", HOST / "make_batch.py", "python"))
A(block("3.7 `mamba_vs_upstream.diff` — thay đổi lõi `mamba.c` so với upstream (1 dòng)", ROOT / "firmware" / "common" / "mamba_vs_upstream.diff", "diff"))

A("## 4. Log thô (nguyên văn)\n")
A(block("4.1 Rò rỉ: 1000 lượt trước sửa", LOGS / "baseline_leak_1000runs.txt"))
A(block("4.2 Rò rỉ: 4000 lượt trước sửa", LOGS / "baseline_leak_4000runs.txt"))
A(block("4.3 Baseline 1 mẫu trước sửa", LOGS / "host_20261018_194955.txt"))
A(block("4.4 ASan trước sửa (leak + overflow)", LOGS / "asan_prefix.txt"))
A(block("4.5 ASan sau sửa rò rỉ", LOGS / "asan_fixed.txt"))
A(block("4.6 ASan sau vendor mamba.c", LOGS / "asan_vendored.txt"))
A(block("4.7 ASan cuối (sạch)", LOGS / "asan_final.txt"))
A(block("4.8 Chấm điểm UCI trước vendor mamba.c", LOGS / "uci_test_pre_mamba_score.txt"))
A(block("4.9 Chấm điểm UCI cuối", LOGS / "uci_test_final_score.txt"))
A(block("4.10 Lần chạy 1 mẫu cuối — báo đầu ra không hợp lệ", LOGS / "host_20261018_202535.txt"))
A(tail_block("4.11 Build Portenta H7 (thành công)", ROOT / "firmware" / "mambahar-portenta-h7" / "logs" / "build_20261018_201729.txt"))
A(tail_block("4.12 Build ESP32-S3 (thành công)", ROOT / "firmware" / "mambahar-esp32s3" / "logs" / "build_20261018_202030.txt"))

BIG = [
    LOGS / "baseline_logits.csv", LOGS / "fixed_logits.csv", LOGS / "v2_batch201_logits.csv",
    LOGS / "v3_batch201_logits.csv", LOGS / "uci_test_logits_pre_mamba.csv",
    LOGS / "uci_test_logits_post_mamba.csv", LOGS / "uci_test_logits_final.csv",
    LOGS / "batch_demo.f32", LOGS / "uci_test.f32",
]
A("## 5. File số liệu (nằm trong repo, không in vào phụ lục cho gọn)\n")
A("| File | Bytes | SHA-256 |\n|---|---|---|\n" + "\n".join(
    f"| `{p.relative_to(ROOT).as_posix()}` | {p.stat().st_size:,} | {digest(p)[:32]}… |" for p in BIG) + "\n")

A("## 6. Checksum các file có mặt trong phụ lục này\n")
A("| File | SHA-256 |\n|---|---|\n" + "\n".join(
    f"| `{p.relative_to(ROOT).as_posix()}` | `{digest(p)}` |" for p in EMBEDDED) + "\n")

OUT.write_text("\n".join(parts), encoding="utf-8")
print(f"OK: {OUT.name} ({OUT.stat().st_size:,} bytes, {len(EMBEDDED)} file nhung)")

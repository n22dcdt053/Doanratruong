#!/usr/bin/env python3
"""Sinh phụ lục "kiểm chứng số học trên PC" (1 file markdown) từ code + log thực tế.

    python firmware/host/make_evidence_bundle.py [--no-code]
    -> docs/KIEM_CHUNG_SO_HOC_PC_20261020.md

File sinh tự động — đừng sửa tay; chạy lại script này sau mỗi đợt đo mới.
--no-code: bỏ mục 3 (in nguyên văn mã nguồn) cho bản gọn — mã nguồn + sha256 vẫn ở mục 5/6.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "firmware" / "host"
LOGS = HOST / "logs"
OUT = ROOT / "docs" / "KIEM_CHUNG_SO_HOC_PC_20261020.md"
WITH_CODE = "--no-code" not in sys.argv

EMBEDDED: list[Path] = []


def digest(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def read_text(p: Path) -> str:
    """Đọc text bất kể encoding thực tế (log PowerShell 5.1 là UTF-16 có BOM)."""
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


def same(a: Path, b: Path) -> bool:
    return a.read_bytes() == b.read_bytes()


def verdicts(path: Path) -> list[str]:
    """Các dòng kết luận do script A/B in ra (bắt đầu bằng 'KET QUA:')."""
    if not path.exists():
        return []
    return [l.strip() for l in read_text(path).splitlines() if l.startswith("KET QUA:")]


def csv_rowdiff(a: Path, b: Path) -> str:
    la = read_text(a).splitlines()
    lb = read_text(b).splitlines()
    hdr = la[0].split(",")
    diffs = []
    for x, y in zip(la[1:], lb[1:]):
        fx, fy = x.split(","), y.split(",")
        if fx != fy:
            cols = [f"{hdr[i]} ({fx[i]} → {fy[i]})" for i in range(min(len(fx), len(fy))) if fx[i] != fy[i]]
            diffs.append(f"mẫu {fx[0]}: " + ", ".join(cols))
    sa, sb = a.stat().st_size, b.stat().st_size
    return (f"khác {len(diffs)} dòng; kích thước {sa:,} → {sb:,} B (Δ {sb - sa:+d}) — "
            + "; ".join(diffs))


def git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return r.stdout.strip()


HEAD = git("rev-parse", "--short", "HEAD")
OUT_REL = OUT.relative_to(ROOT).as_posix()
DIRTY = [l for l in git("status", "--porcelain").splitlines() if OUT_REL not in l]
TREE_STATE = "cây sạch (không tính chính file này)" if not DIRTY else f"CHƯA commit: {len(DIRTY)} mục khác file này"

parts: list[str] = []
A = parts.append

A("# KIỂM CHỨNG SỐ HỌC TRÊN PC — phụ lục kèm báo cáo tiến độ\n")
A("Ngày 18–20/10/2026 · Nhóm: Nguyễn Mai Trọng Quý (N22DCDT053), Võ Trung Nhân (N22DCDT043), "
  "Đinh Hữu Phước (N22DCDT047) · GVHD: TS. Nguyễn Thanh Bình\n")
A("File sinh tự động: `python firmware/host/make_evidence_bundle.py` — đừng sửa tay.\n")

A("## 0. Phạm vi tài liệu này\n")
A("- Môi trường: **máy tính của nhóm — Windows gọi qua PowerShell, chương trình chạy trong "
  "WSL Ubuntu 24.04, gcc/g++ 13.3.0, x86-64**. Không có bo nào tham gia.\n")
A(f"- Sinh từ cây làm việc tại commit `{HEAD}` — trạng thái cây khi sinh: **{TREE_STATE}** "
  "(`git rev-parse --short HEAD` + `git status --porcelain`).\n")
A("- Kiểm chứng **số học**: đúng/sai kết quả, rò rỉ bộ nhớ, hành vi với đầu vào lỗi, của cùng "
  "bộ mã nguồn mô hình sẽ nạp lên bo (`firmware/common/`).\n")
A("- **Khác biệt nguồn lệch tầng B (compiler/ngôn ngữ):** firmware Portenta biên dịch mô hình bằng "
  "**C++** (`arm-none-eabi-g++`, newlib, Cortex-M7 FPv5) vì `main.cpp` include các file `.c` trong "
  "`extern \"C\" {}`; host truyền thống dùng **gcc ở chế độ C** (glibc, x86-64 SSE2). Đây là một "
  "nguồn lệch thật của tầng B — đã đo bằng A/B build `g++` vs `gcc` trên cùng bộ nguồn, cùng runner "
  "(mục 2.4, log 4.13). Phần khác biệt còn lại (target, newlib vs glibc, FPU) chỉ chốt được khi đo "
  "trên bo thật.\n")
A("- Firmware gọi `mambahar_forward()` (1 mẫu rồi reset); host gọi `mambahar_forward_logits()`. "
  "Hai hàm **cùng một thân hàm** (`mambahar_forward` gọi `forward_logits(input, NULL)` — "
  "`firmware/common/mambahar.c` dòng 161–164), nên không có nhánh tính toán riêng.\n")
A("- **Không thay thế** bài test trên phần cứng: Flash/RAM theo map file, heap Mbed, 1.000 lượt "
  "liên tiếp, thời gian, năng lượng — chỉ số đo trên Portenta H7 mới tính là bằng chứng nghiệm thu.\n")
A("- Thời gian in ra là wall clock của PC, **không phải** thời gian MCU. Các chỗ ghi "
  "*(ước tính)* / *(giả thuyết)* là suy luận chưa đo, không dùng làm bằng chứng.\n")

A("## 1. Cách tái tạo toàn bộ file này\n")
A("```powershell\n"
  "cd D:\\DoanNhomQuy\n"
  "# Biên dịch + chạy host (1 lượt / 1000 / 4000 lượt, hoặc batch .f32 -> CSV)\n"
  "powershell -ExecutionPolicy Bypass -File .\\firmware\\host\\run_host_test.ps1 -Iterations 1\n"
  "powershell -ExecutionPolicy Bypass -File .\\firmware\\host\\run_host_test.ps1 -Batch .\\firmware\\host\\logs\\batch_demo.f32 -OutName out.csv\n"
  "# A/B: gcc(C) vs g++(C++); upstream 1:1 vs bản dev (cùng runner, 2947 mẫu UCI)\n"
  "wsl -e bash /mnt/d/DoanNhomQuy/firmware/host/run_cpp_vs_c.sh\n"
  "wsl -e bash /mnt/d/DoanNhomQuy/firmware/host/run_upstream_cmp.sh\n"
  "# ASan + UBSan + LSan: 1 mẫu, 1000 lượt, batch UCI\n"
  "wsl -e bash /mnt/d/DoanNhomQuy/firmware/host/run_asan.sh\n"
  "# UCI HAR: chuyển tập test -> .f32 rồi chấm điểm (in cả confusion matrix), và sinh lại phụ lục\n"
  "python .\\firmware\\host\\uci_har.py to-f32 \"D:\\DoanNhomQuy\\data\\UCI HAR Dataset\" .\\firmware\\host\\logs\\uci_test.f32\n"
  "python .\\firmware\\host\\uci_har.py score .\\firmware\\host\\logs\\uci_test_logits_final.csv \"D:\\DoanNhomQuy\\data\\UCI HAR Dataset\"\n"
  "python .\\firmware\\host\\make_evidence_bundle.py\n"
  "```\n")
A("Dataset: UCI HAR Dataset (archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip), "
  "giải nén vào `data/` (không commit, `.gitignore`).\n")

A("## 2. Kết quả chính\n")

A("### 2.1 Rò rỉ bộ nhớ — trước/sau khi sửa (log 4.1–4.2)\n")
A("| | RSS 1000 lượt | RSS 4000 lượt |\n|---|---|---|\n"
  "| Trước sửa | +8.416 KB (tăng theo số lượt) | +32.460 KB |\n"
  "| Sau sửa | **+496 KB** | **+500 KB** |\n")
A("Diễn giải \"+496/500 KB là lần chạm trang đầu tiên của glibc\" và \"RAM H7 (511 KB) sẽ hết sau "
  "khoảng 60 lượt nếu giữ rò rỉ\" là **ước tính/giả thuyết — chưa đo trên bo**; bằng chứng đo được "
  "nằm ở chính các con số RSS trên. Kiểm chứng \"không rò rỉ\" chắc chắn nhất: LSan/ASan ở 2.2.\n")

A("### 2.2 ASan / LSan / UBSan (log 4.4–4.7 cũ + 4.15 mở rộng)\n")
A("- Trước sửa: `8128 byte(s) leaked in 6 allocation(s)` + `heap-buffer-overflow READ of size 4` "
  "tại `csrc/mamba.c:94`.\n")
A("- Sau sửa rò rỉ: hết leak. Sau khi vendor `mamba.c` (sửa 1 dòng vòng chép `xz`): hết report.\n")
A("- **Độ phủ hiện tại (log 4.15):** 4 lượt chạy — 1 mẫu (2 chế độ) + **1.000 lượt liên tiếp** + "
  "**batch đủ 2.947 mẫu UCI hữu hạn** — không còn report ASan/UBSan/LSan nào.\n")
A("- Trong run 3 dưới ASan, RSS tăng **+108 MB** — đó là *artifact của allocator ASan* (redzone + "
  "quarantine giữ các vùng đã free), **không phải rò rỉ**: LSan không in report nào, và bản gcc "
  "thường (mục 2.1) chỉ +500 KB cho 4.000 lượt.\n")
for v in verdicts(LOGS / "asan_extended_20261018.txt"):
    A(f"- {v}\n")

A("### 2.3 Tập test UCI HAR, bản C tham chiếu (log 4.8–4.9)\n")
A("Toàn bộ **2.947 mẫu test**, trọng số công khai, nhãn `y_test.txt` 1..6 trừ 1 (khớp `train.py` "
  "dòng 37/39):\n\n"
  "| Chỉ số | Giá trị |\n|---|---|\n"
  "| Accuracy | **0,9267** |\n| Macro-F1 | **0,9265** |\n"
  "| F1 theo lớp | 0,937 / 0,913 / 0,949 / 0,879 / 0,904 / 0,978 |\n"
  "| Số mẫu NaN / không hợp lệ | **0 / 0** |\n"
  "| Confusion matrix + tên lớp | in ở log 4.9 |\n")
A("Ý nghĩa: pipeline (tiền xử lý → 6 logits → argmax) khớp dữ liệu thật; đây **chỉ là điểm tham "
  "chiếu cho kiểm chứng số học MT1/MT3**, không dùng trong bảng so sánh Mamba↔MLP (checkpoint công "
  "khai chọn bằng validation chia ngẫu nhiên).\n")

A("### 2.4 Đối chiếu bit-exact — phạm vi chính xác\n")
A("Chỉ khẳng định **bit-exact cho các đầu ra hữu hạn** (tập UCI HAR chuẩn hóa: 0 mẫu NaN). "
  "Các cặp đã đối chiếu:\n")
for v in verdicts(LOGS / "cpp_vs_c_cmp_20261018.txt") + verdicts(LOGS / "upstream_vs_final_cmp_20261018.txt"):
    A(f"- {v}\n")
tri_equal = same(LOGS / "uci_test_logits_pre_mamba.csv", LOGS / "uci_test_logits_post_mamba.csv") and \
    same(LOGS / "uci_test_logits_post_mamba.csv", LOGS / "uci_test_logits_final.csv")
A(f"- Ba bản CSV 2.947 mẫu (trước khi vendor `mamba.c` / sau khi vendor / bản cuối): "
  f"**{'trùng khớp từng byte' if tri_equal else 'KHÁC'}** — `uci_test_logits_{{pre_mamba,post_mamba,final}}.csv`.\n")
b201 = same(LOGS / "baseline_logits.csv", LOGS / "fixed_logits.csv") and same(LOGS / "fixed_logits.csv", LOGS / "v2_batch201_logits.csv")
A(f"- Lô 201 mẫu (`baseline` → `fixed` → `v2`): **{'trùng khớp từng byte' if b201 else 'KHÁC'}**. "
  "*Lưu ý phạm vi:* lô này gồm **1 mẫu demo thật (cho NaN) + 200 mẫu ngẫu nhiên**, nên chỉ là bằng "
  "chứng phụ cho lần sửa rò rỉ; kết luận chính dùng cặp 2.947 mẫu thật ở trên.\n")
A(f"- `v2_batch201_logits.csv` vs `v3_batch201_logits.csv` (trước/sau thêm kiểm `isfinite`): "
  f"{csv_rowdiff(LOGS / 'v2_batch201_logits.csv', LOGS / 'v3_batch201_logits.csv')}. "
  "Đúng dự kiến: chỉ mẫu demo (NaN) đổi cách báo; dữ liệu thật hữu hạn không đổi.\n")

A("### 2.5 Mẫu demo sai thang đầu vào → báo không hợp lệ (log 4.10)\n")
A("Mẫu demo `sample_input.h` (thang thô ~ −39) cho logits NaN; trước đây bị tính thành lớp 0 "
  "(argmax trên NaN luôn sai) — **không phải dự đoán thật**. Bản vendor hiện tại kiểm `isfinite` cả "
  "6 logits → trả `-2` và in `Output: INVALID`. Dữ liệu UCI chuẩn hóa không có mẫu NaN nào, xác "
  "nhận nguyên nhân là thang đầu vào.\n")

if WITH_CODE:
    A("## 3. Mã nguồn kiểm chứng (nguyên văn)\n")
    A(block("3.1 `host_main.c` — runner PC (dùng chung mã nguồn với firmware; cờ `-DUPSTREAM_ONLY` cho A/B upstream)",
            HOST / "host_main.c", "c"))
    A(block("3.2 `run_host_test.ps1` — điểm vào trên Windows", HOST / "run_host_test.ps1", "powershell"))
    A(block("3.3 `run_host_test.sh` — biên dịch + chạy bằng gcc trong WSL", HOST / "run_host_test.sh", "bash"))
    A(block("3.4 `run_asan.sh` — ASan + UBSan + LSan (1 mẫu, 1000 lượt, batch UCI)", HOST / "run_asan.sh", "bash"))
    A(block("3.5 `run_cpp_vs_c.sh` — A/B gcc(C) vs g++(C++)", HOST / "run_cpp_vs_c.sh", "bash"))
    A(block("3.6 `run_upstream_cmp.sh` — A/B upstream 1:1 vs bản dev", HOST / "run_upstream_cmp.sh", "bash"))
    A(block("3.7 `uci_har.py` — chuyển UCI HAR sang .f32 + chấm điểm (confusion matrix, tên lớp)",
            HOST / "uci_har.py", "python"))
    A(block("3.8 `make_batch.py` — sinh lô mẫu kiểm thử", HOST / "make_batch.py", "python"))
    A(block("3.9 `mamba_vs_upstream.diff` — thay đổi lõi `mamba.c` (1 dòng)",
            ROOT / "firmware" / "common" / "mamba_vs_upstream.diff", "diff"))
    A(block("3.10 `mambahar_vs_upstream.diff` — thay đổi wrapper",
            ROOT / "firmware" / "common" / "mambahar_vs_upstream.diff", "diff"))
else:
    A("## 3. Mã nguồn kiểm chứng\n")
    A("Mục này lược bỏ theo `--no-code` — xem mã nguồn trong repo + sha256 tại mục 5.\n")

A("## 4. Log thô (nguyên văn)\n")
A("*Ghi chú:* vài log ASan cũ (4.4–4.5) chứa các dòng `NativeCommandError` / `CategoryInfo` — đó "
  "là phần **PowerShell gói stderr của `wsl` khi đọc log**, không phải lỗi của chương trình; báo cáo "
  "ASan thật nằm ngay sau các dòng đó.\n")
A(block("4.1 Rò rỉ: 1000 lượt trước sửa", LOGS / "baseline_leak_1000runs.txt"))
A(block("4.2 Rò rỉ: 4000 lượt trước sửa", LOGS / "baseline_leak_4000runs.txt"))
A(block("4.3 Baseline 1 mẫu trước sửa", LOGS / "host_20261018_194955.txt"))
A(block("4.4 ASan trước sửa (leak + overflow)", LOGS / "asan_prefix.txt"))
A(block("4.5 ASan sau sửa rò rỉ", LOGS / "asan_fixed.txt"))
A(block("4.6 ASan sau vendor mamba.c", LOGS / "asan_vendored.txt"))
A(block("4.7 ASan cuối (1 mẫu)", LOGS / "asan_final.txt"))
A(block("4.8 Chấm điểm UCI trước vendor mamba.c (có confusion matrix)", LOGS / "uci_test_pre_mamba_score.txt"))
A(block("4.9 Chấm điểm UCI cuối (có confusion matrix)", LOGS / "uci_test_final_score.txt"))
A(block("4.10 Lần chạy 1 mẫu cuối — báo đầu ra không hợp lệ", LOGS / "host_20261018_202535.txt"))
A(tail_block("4.11 Build Portenta H7 (thành công)",
             ROOT / "firmware" / "mambahar-portenta-h7" / "logs" / "build_20261018_201729.txt"))
A(tail_block("4.12 Build ESP32-S3 (thành công)",
             ROOT / "firmware" / "mambahar-esp32s3" / "logs" / "build_20261018_202030.txt"))
A(block("4.13 A/B gcc(C) vs g++(C++) trên 2.947 mẫu", LOGS / "cpp_vs_c_cmp_20261018.txt"))
A(block("4.14 A/B upstream 1:1 vs bản dev trên 2.947 mẫu", LOGS / "upstream_vs_final_cmp_20261018.txt"))
A(block("4.15 ASan mở rộng: 1 mẫu + 1.000 lượt + batch 2.947 mẫu", LOGS / "asan_extended_20261018.txt"))

BIG = [
    LOGS / "baseline_logits.csv", LOGS / "fixed_logits.csv", LOGS / "v2_batch201_logits.csv",
    LOGS / "v3_batch201_logits.csv", LOGS / "uci_test_logits_pre_mamba.csv",
    LOGS / "uci_test_logits_post_mamba.csv", LOGS / "uci_test_logits_final.csv",
    LOGS / "batch_demo.f32", LOGS / "uci_test.f32",
    ROOT / "firmware" / "mambahar-portenta-h7" / "logs" / "build_20261018_201729.txt",
    ROOT / "firmware" / "mambahar-esp32s3" / "logs" / "build_20261018_202030.txt",
]
A("## 5. File số liệu (nằm trong repo, không in vào phụ lục cho gọn)\n")
A("| File | Bytes | SHA-256 |\n|---|---|---|\n" + "\n".join(
    f"| `{p.relative_to(ROOT).as_posix()}` | {p.stat().st_size:,} | {digest(p)[:32]}… |" for p in BIG) + "\n")

A("## 6. Checksum các file có mặt trong phụ lục này\n")
A("| File | SHA-256 |\n|---|---|\n" + "\n".join(
    f"| `{p.relative_to(ROOT).as_posix()}` | `{digest(p)}` |" for p in EMBEDDED) + "\n")

OUT.parent.mkdir(exist_ok=True)
OUT.write_text("\n".join(parts), encoding="utf-8")
print(f"OK: {OUT.relative_to(ROOT).as_posix()} ({OUT.stat().st_size:,} bytes, {len(EMBEDDED)} file nhung, "
      f"HEAD {HEAD}, {TREE_STATE})")

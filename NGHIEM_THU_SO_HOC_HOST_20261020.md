# PHỤ LỤC NGHIỆM THU — kiểm chứng số học trên máy tính (không cần bo)

Ngày 18–20/10/2026 · Nhóm: Nguyễn Mai Trọng Quý (N22DCDT053), Võ Trung Nhân (N22DCDT043), Đinh Hữu Phước (N22DCDT047) · GVHD: TS. Nguyễn Thanh Bình

File sinh tự động: `python firmware/host/make_evidence_bundle.py` — đừng sửa tay.

## 0. Phạm vi tài liệu này

- Môi trường: **máy tính của nhóm — Windows gọi qua PowerShell, chương trình chạy trong WSL Ubuntu 24.04, gcc 13.3, x86-64**. Không có bo nào tham gia.

- Kiểm chứng **số học**: đúng/sai kết quả, rò rỉ bộ nhớ, hành vi với đầu vào lỗi, của **đúng mã nguồn C sẽ nạp lên bo** (cùng bản vendor `firmware/common/`).

- **Không thay thế** bài test trên phần cứng: Flash/RAM theo map file, heap Mbed, 1.000 lượt liên tiếp, thời gian, năng lượng — chỉ số đo trên Portenta H7 mới tính là bằng chứng nghiệm thu.

- Thời gian in ra là wall clock của PC, **không phải** thời gian MCU.

## 1. Cách tái tạo toàn bộ file này

```powershell
cd D:\DoanNhomQuy
# 1 lượt (mẫu demo -> báo đầu ra không hợp lệ), 1000 / 4000 lượt (kiểm rò rỉ)
powershell -ExecutionPolicy Bypass -File .\firmware\host\run_host_test.ps1 -Iterations 1
powershell -ExecutionPolicy Bypass -File .\firmware\host\run_host_test.ps1 -Iterations 1000
# chạy lô N mẫu từ file .f32 -> CSV (idx,pred,6 logits)
powershell -ExecutionPolicy Bypass -File .\firmware\host\run_host_test.ps1 -Batch .\firmware\host\logs\batch_demo.f32 -OutName out.csv
# ASan + UBSan + LSan (chạy trong WSL)
wsl -e bash /mnt/d/DoanNhomQuy/firmware/host/run_asan.sh
# UCI HAR: chuyển tập test -> .f32 và chấm điểm
python .\firmware\host\uci_har.py to-f32 "D:\DoanNhomQuy\data\UCI HAR Dataset" .\firmware\host\logs\uci_test.f32
python .\firmware\host\uci_har.py score .\firmware\host\logs\uci_test_logits_final.csv "D:\DoanNhomQuy\data\UCI HAR Dataset"
# đối chiếu bit-exact (cmp khớp từng byte)
wsl -e bash -c "cd /mnt/d/DoanNhomQuy/firmware/host/logs && cmp fixed_logits.csv v2_batch201_logits.csv && echo BIT-EXACT"
```

Dataset: UCI HAR Dataset (archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip), giải nén vào `data/` (không commit, .gitignore).

## 2. Kết quả chính

### 2.1 Rò rỉ bộ nhớ — trước/sau khi sửa (log 4.1–4.2)

| | RSS 1000 lượt | RSS 4000 lượt |
|---|---|---|
| Trước sửa | +8.416 KB (tăng tuyến tính ~8,4 KB/lượt) | +32.460 KB |
| Sau sửa | **+496 KB** | **+500 KB** (thêm 4 KB khi gấp 4 lần số lượt) |

Mức +496/500 KB là lần chạm trang đầu tiên của glibc (trọng số + allocator), không tăng theo số lượt -> đạt yêu cầu "không rò rỉ". Trước sửa: RAM H7 511 KB sẽ hết sau ~60 lượt -> không thể đạt yêu cầu 1.000 lượt.

### 2.2 ASan / LSan / UBSan (log 4.4–4.7)

- Trước sửa: `8128 byte(s) leaked in 6 allocation(s)` + `heap-buffer-overflow READ of size 4` tại `csrc/mamba.c:94`.
- Sau sửa rò rỉ: hết leak. Sau khi vendor `mamba.c` (sửa 1 dòng vòng chép `xz`): **sạch hoàn toàn**, không còn report nào.

### 2.3 Tập test UCI HAR, bản C tham chiếu (log 4.8–4.9)

Toàn bộ **2.947 mẫu test**, trọng số công khai, chấm theo `y_test.txt` (trừ 1 do nhãn gốc 1..6, khớp `train.py` dòng 39):

| Chỉ số | Giá trị |
|---|---|
| Accuracy | **0,9267** |
| Macro-F1 | **0,9265** |
| F1 theo lớp | 0,937 / 0,913 / 0,949 / 0,879 / 0,904 / 0,978 |
| Số mẫu NaN / không hợp lệ | **0 / 0** |

Ý nghĩa: pipeline (tiền xử lý -> 6 logits -> argmax) khớp dữ liệu thật; đây **chỉ là điểm tham chiếu cho kiểm chứng số học MT1/MT3**, không dùng trong bảng so sánh Mamba↔MLP (checkpoint công khai chọn bằng validation chia ngẫu nhiên).

### 2.4 Đối chiếu bit-exact (`cmp`) — sửa code không đổi kết quả

| Cặp file | Kết quả |
|---|---|
| baseline_logits.csv vs fixed_logits.csv (sau sửa rò rỉ) | khớp từng byte |
| fixed_logits.csv vs v2_batch201_logits.csv (sau vendor mamba.c) | khớp từng byte |
| uci pre_mamba vs post_mamba (2.947 mẫu, sau vendor mamba.c) | khớp từng byte |
| uci post_mamba vs final (sau thêm kiểm tra isfinite) | khớp từng byte |
| v2 vs v3 (trước/sau thêm kiểm tra isfinite) | khác **1 dòng** — đúng dự kiến: cột pred của mẫu demo đổi 0 -> -2 |

### 2.5 Mẫu demo sai thang đầu vào -> báo không hợp lệ (log 4.10)

Mẫu demo `sample_input.h` (thang thô ~ -39) cho logits NaN; trước đây bị tính thành lớp 0 (argmax trên NaN luôn sai) — **không phải dự đoán thật**. Bản vendor hiện tại kiểm `isfinite` cả 6 logits -> trả `-2` và in `Output: INVALID`. Dữ liệu UCI chuẩn hóa không có mẫu NaN nào, xác nhận nguyên nhân là thang đầu vào.

## 3. Code kiểm chứng (nguyên văn)

### 3.1 `host_main.c` — chương trình tham chiếu chạy trên PC (dùng chung mã nguồn với firmware)

`firmware/host/host_main.c`

```c
/**
 * @file host_main.c
 * @brief PC (host) build of the C inference chain used by the Portenta H7
 *        firmware (firmware/mambahar-portenta-h7/src/main.cpp).
 *
 * Sources: firmware/common/mamba.c + mambahar.c (vendored dev copies) +
 * upstream csrc/{matrix,tensor}.c + upstream weights/sample headers.
 * Timing here is host wall clock, NOT MCU evidence.
 *
 * Modes (via run_host_test.ps1 / run_host_test.sh):
 *   host_main <iterations>            single-sample: prediction, logits, RSS
 *   host_main --batch IN.f32 OUT.csv  N x 570 float32 (LE) -> idx,pred,6 logits
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

#include "../../MambaLite-Micro/csrc/matrix.c"
#include "../../MambaLite-Micro/csrc/tensor.c"
#include "mamba.c"
#include "mambahar.c"
#include "sample_input.h"

#define N_FEAT (10 * 57)

static double now_us(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e6 + (double)ts.tv_nsec / 1e3;
}

static long rss_kb(void)
{
    FILE *f = fopen("/proc/self/statm", "r");
    long total = 0, resident = 0;
    if (!f)
        return -1;
    if (fscanf(f, "%ld %ld", &total, &resident) != 2)
        resident = -1;
    fclose(f);
    return resident < 0 ? -1 : resident * 4; /* Linux page = 4 KiB */
}

static int run_batch(const char *in_path, const char *out_path)
{
    FILE *fin = fopen(in_path, "rb");
    if (!fin)
    {
        fprintf(stderr, "cannot open input %s\n", in_path);
        return 1;
    }
    FILE *fout = fopen(out_path, "w");
    if (!fout)
    {
        fprintf(stderr, "cannot open output %s\n", out_path);
        fclose(fin);
        return 1;
    }

    float sample[N_FEAT];
    long idx = 0;
    int bad = 0;
    fprintf(fout, "sample_index,pred,logit0,logit1,logit2,logit3,logit4,logit5\n");
    while (fread(sample, sizeof(float), N_FEAT, fin) == N_FEAT)
    {
        float logits[6] = {0};
        int pred = mambahar_forward_logits(sample, logits);
        fprintf(fout, "%ld,%d,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g\n", idx, pred,
                (double)logits[0], (double)logits[1], (double)logits[2],
                (double)logits[3], (double)logits[4], (double)logits[5]);
        idx++;
    }
    if (!feof(fin))
    {
        fprintf(stderr, "trailing partial sample in %s\n", in_path);
        bad = 1;
    }
    fclose(fin);
    fclose(fout);
    printf("Batch: %ld samples -> %s%s\n", idx, out_path,
           bad ? " (PARTIAL TRAILING DATA)" : "");
    return bad;
}

int main(int argc, char **argv)
{
    if (argc == 4 && strcmp(argv[1], "--batch") == 0)
        return run_batch(argv[2], argv[3]);

    int iterations = argc > 1 ? atoi(argv[1]) : 1;
    if (iterations < 1)
        iterations = 1;

    long rss0 = rss_kb();
    double t0 = now_us();
    float logits[6] = {0};
    int pred = mambahar_forward_logits(input_data, logits); /* first 570 floats = [1, 10, 57] */
    for (int i = 1; i < iterations; i++)
        pred = mambahar_forward_logits(input_data, logits);
    double t1 = now_us();
    long rss1 = rss_kb();

    printf("Model_Forward completed.\n");
    printf("Prediction: %d\n", pred);
    if (pred < 0)
        printf("Output: INVALID (%s), pred=%d is not a class\n",
               pred == -2 ? "non-finite logits" : "allocation/kernel failure", pred);
    printf("Logits: %.9g %.9g %.9g %.9g %.9g %.9g\n",
           (double)logits[0], (double)logits[1], (double)logits[2],
           (double)logits[3], (double)logits[4], (double)logits[5]);
    printf("Elapsed time: %.0f us (host wall clock, %d run(s), NOT MCU timing)\n",
           t1 - t0, iterations);
    printf("Host RSS: %ld KB -> %ld KB (delta %ld KB over %d run(s))\n",
           rss0, rss1, rss1 - rss0, iterations);
    return pred == -1 ? 1 : 0; /* -2 = invalid input/output, run itself completed */
}
```

### 3.2 `run_host_test.ps1` — điểm vào trên Windows

`firmware/host/run_host_test.ps1`

```powershell
# Host (PC) test of the Mamba HAR C model — no MCU needed. Compiles and runs
# firmware/host/host_main.c with WSL gcc; evidence lands in firmware/host/logs/.
#   Single sample + timing + RSS:  .\run_host_test.ps1 -Iterations 1000
#   Batch -> logits CSV:           .\run_host_test.ps1 -Batch .\logs\batch_demo.f32 -OutName fixed_logits.csv
param(
    [int]$Iterations = 1,
    [string]$Batch,
    [string]$OutName
)

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$wslRoot = (wsl wslpath -a ($repo -replace '\\', '/') | Select-Object -First 1).Trim()
$logDir = Join-Path $PSScriptRoot "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if ($Batch) {
    if (-not $OutName) { $OutName = "batch_logits.csv" }
    $batchWsl = (wsl wslpath -a ((Resolve-Path $Batch).Path -replace '\\', '/') | Select-Object -First 1).Trim()
    $outWsl = "$wslRoot/firmware/host/logs/$OutName"
    $out = wsl -e bash "$wslRoot/firmware/host/run_host_test.sh" --batch "$batchWsl" "$outWsl" 2>&1
    $code = $LASTEXITCODE
    $out
    if ($code -ne 0) {
        Write-Host "FAILED (exit $code)"
        exit $code
    }
    Write-Host "CSV saved: $(Join-Path $logDir $OutName)"
    return
}

$log = Join-Path $logDir ("host_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".txt")
$out = wsl -e bash "$wslRoot/firmware/host/run_host_test.sh" $Iterations 2>&1
$code = $LASTEXITCODE
$out | Tee-Object -FilePath $log
if ($code -ne 0) {
    Write-Host "FAILED (exit $code)"
    exit $code
}
Write-Host "Log saved: $log"
```

### 3.3 `run_host_test.sh` — biên dịch + chạy bằng gcc trong WSL

`firmware/host/run_host_test.sh`

```bash
#!/usr/bin/env bash
# Host build + run of the repo's dev C model chain (no MCU needed). See host_main.c.
#   bash run_host_test.sh [iterations]
#   bash run_host_test.sh --batch IN.f32 OUT.csv
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
VENDOR="$ROOT/firmware/common"
CSRC="$ROOT/MambaLite-Micro/csrc"
UPSTREAM_INC="$ROOT/MambaLite-Micro/examples/mambahar-arduino-6/include"
BIN="$(mktemp /tmp/mambahar_host.XXXXXX)"
trap 'rm -f "$BIN"' EXIT
# -I order matters: vendored files first, then upstream headers (weights, sample)
gcc -O2 -o "$BIN" "$HERE/host_main.c" -I"$VENDOR" -I"$CSRC" -I"$UPSTREAM_INC" -lm
if [ "$#" -eq 0 ]; then set -- 1; fi
"$BIN" "$@"
```

### 3.4 `run_asan.sh` — ASan + UBSan + LSan

`firmware/host/run_asan.sh`

```bash
#!/usr/bin/env bash
# ASan/UBSan run of the host build (same sources as the firmware), no MCU.
# Run 1 halts at the first finding; run 2 keeps going and reports leaks at exit.
# Usage: bash run_asan.sh   (from anywhere)
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
INC="-I$ROOT/firmware/common -I$ROOT/MambaLite-Micro/csrc -I$ROOT/MambaLite-Micro/examples/mambahar-arduino-6/include"

gcc -O1 -g -fsanitize=address,undefined -o /tmp/asan_hard "$HERE/host_main.c" $INC -lm
echo "=== ASan run 1: default (first error stops the run) ==="
/tmp/asan_hard 1 || true

gcc -O1 -g -fsanitize=address,undefined -fsanitize-recover=all -o /tmp/asan_soft "$HERE/host_main.c" $INC -lm
echo "=== ASan run 2: recover mode (halt_on_error=0), leaks reported at exit ==="
ASAN_OPTIONS=halt_on_error=0:detect_leaks=1 /tmp/asan_soft 1 || true
echo "=== ASan done ==="
```

### 3.5 `uci_har.py` — chuyển UCI HAR sang .f32 + chấm điểm

`firmware/host/uci_har.py`

```python
#!/usr/bin/env python3
"""UCI HAR test-set helpers for the host runner (no numpy needed).

  to-f32 <dataset_root> <out.f32>   X_test.txt (561 feats) -> pad 9 zeros -> 570 -> float32 LE
  score  <logits.csv> <dataset_root>  accuracy, macro-F1, NaN/invalid counts vs y_test.txt

Padding matches MambaLite-Micro/Python/train.py: F.pad(features, (0, 9)) then view(-1, 10, 57).
Dataset: "UCI HAR Dataset" (archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip),
extracted to data/UCI HAR Dataset/ (gitignored).
"""
import argparse
import csv
import math
import struct
from pathlib import Path

N_FEAT = 570


def to_f32(root: Path, out: Path):
    src = root / "test" / "X_test.txt"
    rows = 0
    with open(src) as f, open(out, "wb") as g:
        for line in f:
            vals = [float(v) for v in line.split()]
            if len(vals) != 561:
                raise SystemExit(f"{src}: line {rows + 1} has {len(vals)} features, want 561")
            g.write(struct.pack("<570f", *(vals + [0.0] * 9)))
            rows += 1
    print(f"wrote {rows} samples ({out.stat().st_size} bytes) -> {out}")


def score(csv_path: Path, root: Path):
    # y_test.txt is 1..6; train.py uses sklearn LabelEncoder -> classes are 0-based
    labels = [int(v) - 1 for v in (root / "test" / "y_test.txt").read_text().split()]
    preds, nan_rows, invalid_rows = [], 0, 0
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            logits = [float(r[f"logit{c}"]) for c in range(6)]
            if any(not math.isfinite(v) for v in logits):
                nan_rows += 1
            p = int(r["pred"])
            if p < 0:
                invalid_rows += 1
            preds.append(p)
    if len(preds) != len(labels):
        raise SystemExit(f"{csv_path}: {len(preds)} predictions vs {len(labels)} labels")
    n = len(labels)
    acc = sum(p == y for p, y in zip(preds, labels)) / n
    f1s = []
    for c in range(6):
        tp = sum(p == c and y == c for p, y in zip(preds, labels))
        fp = sum(p == c and y != c for p, y in zip(preds, labels))
        fn = sum(p != c and y == c for p, y in zip(preds, labels))
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    print(f"samples: {n}")
    print(f"nan_rows (non-finite logits): {nan_rows}")
    print(f"invalid_rows (pred < 0): {invalid_rows}")
    print(f"accuracy: {acc:.4f}")
    print(f"macro-F1: {sum(f1s) / 6:.4f}")
    print("F1 per class: " + " ".join(f"c{c}={v:.4f}" for c, v in enumerate(f1s)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("to-f32")
    p1.add_argument("dataset_root", type=Path)
    p1.add_argument("out", type=Path)
    p2 = sub.add_parser("score")
    p2.add_argument("csv_path", type=Path)
    p2.add_argument("dataset_root", type=Path)
    a = ap.parse_args()
    if a.cmd == "to-f32":
        to_f32(a.dataset_root, a.out)
    else:
        score(a.csv_path, a.dataset_root)


main()
```

### 3.6 `make_batch.py` — sinh lô mẫu kiểm thử

`firmware/host/make_batch.py`

```python
#!/usr/bin/env python3
"""Build a batch input file for firmware/host: N x 570 raw float32 (little-endian).

Sample 0 = first 570 values of the upstream sample_input.h (the real demo sample).
Samples 1..N-1 = deterministic pseudo-random values (fixed seed) so numeric A/B
runs are repeatable. Real UCI-HAR batches will come from the dataset loader later.
"""
import argparse
import random
import re
import struct
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SAMPLE_H = REPO / "MambaLite-Micro/examples/mambahar-arduino-6/include/sample_input.h"
N_FEAT = 10 * 57


def real_sample():
    vals = [float(v[:-1]) for v in re.findall(r"[-+]?\d+\.\d+(?:[eE][-+]?\d+)?f", SAMPLE_H.read_text())]
    if len(vals) < N_FEAT:
        raise SystemExit(f"{SAMPLE_H}: found only {len(vals)} floats, need {N_FEAT}")
    return vals[:N_FEAT]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out")
    ap.add_argument("count", type=int, help="number of samples (>=1)")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    if a.count < 1:
        raise SystemExit("count must be >= 1")
    rng = random.Random(a.seed)
    with open(a.out, "wb") as f:
        f.write(struct.pack("<570f", *real_sample()))
        for _ in range(a.count - 1):
            f.write(struct.pack("<570f", *(rng.gauss(0.0, 1.0) for _ in range(N_FEAT))))
    print(f"wrote {a.count} samples ({a.count * N_FEAT * 4} bytes) -> {a.out}")


main()
```

### 3.7 `mamba_vs_upstream.diff` — thay đổi lõi `mamba.c` so với upstream (1 dòng)

`firmware/common/mamba_vs_upstream.diff`

```diff
--- a/MambaLite-Micro/csrc/mamba.c
+++ b/firmware/common/mamba.c
@@ -1,8 +1,17 @@
 /**
  * @file mamba.c
- * @brief mamba inference kernel
+ * @brief mamba inference kernel — dev (vendor) copy for the DATN firmware.
  * Copyright (c) 2025 MambaLite-Micro Authors
  * Licensed under the MIT License.
+ *
+ * Upstream (unmodified, MIT, commit 44d51fc):
+ *   MambaLite-Micro/csrc/mamba.c
+ * Diff vs upstream (1 line), recorded in HUONG_PHAT_TRIEN.md:
+ *   18/10/2026 — xz copy loop read past hidden_states (ASan heap-buffer-overflow
+ *   at upstream line 94): bound is now `di < d` (d_model). Rows >= d_model of xz
+ *   were never consumed by the following projection, so results are unchanged
+ *   (bit-exact, 2947 UCI HAR test samples + 201-sample A/B batch).
+ * Never edit the upstream file.
  */
 #pragma once
 #include "matrix.h"
@@ -87,7 +96,7 @@
     {
         for (int li = 0; li < l; li++)
         {
-            for (int di = 0; di < self->d_inner; di++)
+            for (int di = 0; di < d; di++) /* vendor: was self->d_inner (OOB read) */
             {
                 int in_idx = bi * l * d + li * d + di;
                 int out_idx = di * (b * l) + (bi * l + li);
```

## 4. Log thô (nguyên văn)

### 4.1 Rò rỉ: 1000 lượt trước sửa

`firmware/host/logs/baseline_leak_1000runs.txt`

```text
��M o d e l _ F o r w a r d   c o m p l e t e d . 
 
 P r e d i c t i o n :   0 
 
 E l a p s e d   t i m e :   4 6 2 5 5 1   u s   ( h o s t   w a l l   c l o c k ,   1 0 0 0   r u n ( s ) ,   N O T   M C U   t i m i n g ) 
 
 H o s t   R S S :   1 9 9 6   K B   - >   1 0 4 1 2   K B   ( d e l t a   8 4 1 6   K B   o v e r   1 0 0 0   r u n ( s ) ) 
 
 
```

### 4.2 Rò rỉ: 4000 lượt trước sửa

`firmware/host/logs/baseline_leak_4000runs.txt`

```text
��M o d e l _ F o r w a r d   c o m p l e t e d . 
 
 P r e d i c t i o n :   0 
 
 E l a p s e d   t i m e :   1 9 5 2 8 6 6   u s   ( h o s t   w a l l   c l o c k ,   4 0 0 0   r u n ( s ) ,   N O T   M C U   t i m i n g ) 
 
 H o s t   R S S :   2 0 0 0   K B   - >   3 4 4 6 0   K B   ( d e l t a   3 2 4 6 0   K B   o v e r   4 0 0 0   r u n ( s ) ) 
 
 
```

### 4.3 Baseline 1 mẫu trước sửa

`firmware/host/logs/host_20261018_194955.txt`

```text
��M o d e l _ F o r w a r d   c o m p l e t e d . 
 
 P r e d i c t i o n :   0 
 
 E l a p s e d   t i m e :   4 1 6   u s   ( h o s t   w a l l   c l o c k ,   1   r u n ( s ) ,   N O T   M C U   t i m i n g ) 
 
 H o s t   R S S :   2 0 0 0   K B   - >   2 4 1 2   K B   ( d e l t a   4 1 2   K B   o v e r   1   r u n ( s ) ) 
 
 
```

### 4.4 ASan trước sửa (leak + overflow)

`firmware/host/logs/asan_prefix.txt`

```text
﻿=== ASan run 1: default (first error stops the run) ===
wsl : =================================================================
At line:1 char:6
+ $o = wsl -e bash /mnt/d/DoanNhomQuy/firmware/host/run_asan.sh 2>&1; $ ...
+      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (===============...===============:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
==571==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x51e000000a90 at pc 0x59bf7b5b3ef8 bp 0x7ffc98a55860 
sp 0x7ffc98a55850
READ of size 4 at 0x51e000000a90 thread T0
    #0 0x59bf7b5b3ef7 in Mamba_Forward /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/mamba.c:94
    #1 0x59bf7b5bca11 in mambahar_forward_logits /mnt/d/DoanNhomQuy/firmware/common/mambahar.c:45
    #2 0x59bf7b5bdfb9 in main /mnt/d/DoanNhomQuy/firmware/host/host_main.c:100
    #3 0x7660dee2a1c9 in __libc_start_call_main ../sysdeps/nptl/libc_start_call_main.h:58
    #4 0x7660dee2a28a in __libc_start_main_impl ../csu/libc-start.c:360
    #5 0x59bf7b5b05a4 in _start (/tmp/asan_hard+0x1b5a4) (BuildId: e30f323ae4bca6d2ca85e44a2c1b5eb2d0f702b5)

0x51e000000a90 is located 0 bytes after 2576-byte region [0x51e000000080,0x51e000000a90)
allocated by thread T0 here:
    #0 0x7660dfafd9c7 in malloc ../../../../src/libsanitizer/asan/asan_malloc_linux.cpp:69
    #1 0x59bf7b5b2fa2 in tensor_zeros /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/tensor.c:21

SUMMARY: AddressSanitizer: heap-buffer-overflow /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/mamba.c:94 
in Mamba_Forward
Shadow bytes around the buggy address:
  0x51e000000800: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000880: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000900: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000980: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000a00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
=>0x51e000000a80: 00 00[fa]fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000b00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000b80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000c00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000c80: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000d00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
==571==ABORTING
=== ASan run 2: recover mode (halt_on_error=0), leaks reported at exit ===
=================================================================
==577==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x51e000000a90 at pc 0x5a3fafecf140 bp 0x7fff575e2a00 
sp 0x7fff575e29f0
READ of size 4 at 0x51e000000a90 thread T0
    #0 0x5a3fafecf13f in Mamba_Forward /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/mamba.c:94
    #1 0x5a3fafed8382 in mambahar_forward_logits /mnt/d/DoanNhomQuy/firmware/common/mambahar.c:45
    #2 0x5a3fafed99d9 in main /mnt/d/DoanNhomQuy/firmware/host/host_main.c:100
    #3 0x712b6262a1c9 in __libc_start_call_main ../sysdeps/nptl/libc_start_call_main.h:58
    #4 0x712b6262a28a in __libc_start_main_impl ../csu/libc-start.c:360
    #5 0x5a3fafecb5a4 in _start (/tmp/asan_soft+0x1b5a4) (BuildId: dc40c5c4077a7e88af50768ebe8ce12373c24055)

0x51e000000a90 is located 0 bytes after 2576-byte region [0x51e000000080,0x51e000000a90)
allocated by thread T0 here:
    #0 0x712b632fd9c7 in malloc ../../../../src/libsanitizer/asan/asan_malloc_linux.cpp:69
    #1 0x5a3fafece154 in tensor_zeros /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/tensor.c:21

SUMMARY: AddressSanitizer: heap-buffer-overflow /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/mamba.c:94 
in Mamba_Forward
Shadow bytes around the buggy address:
  0x51e000000800: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000880: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000900: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000980: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000a00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
=>0x51e000000a80: 00 00[fa]fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000b00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000b80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000c00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000c80: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000d00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb

=================================================================
==577==ERROR: LeakSanitizer: detected memory leaks

Direct leak of 7728 byte(s) in 3 object(s) allocated from:
    #0 0x712b632fd9c7 in malloc ../../../../src/libsanitizer/asan/asan_malloc_linux.cpp:69
    #1 0x5a3fafece154 in tensor_zeros /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/tensor.c:21

Direct leak of 312 byte(s) in 2 object(s) allocated from:
    #0 0x712b632fd9c7 in malloc ../../../../src/libsanitizer/asan/asan_malloc_linux.cpp:69
    #1 0x5a3fafecbba7 in matrix_zeros /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/matrix.c:36

Direct leak of 88 byte(s) in 1 object(s) allocated from:
    #0 0x712b632fd9c7 in malloc ../../../../src/libsanitizer/asan/asan_malloc_linux.cpp:69
    #1 0x5a3fafece53b in Mamba_Init /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/mamba.c:52

SUMMARY: AddressSanitizer: 8128 byte(s) leaked in 6 allocation(s).
Model_Forward completed.
Prediction: 0
Logits: -nan -nan -nan -nan -nan -nan
Elapsed time: 129216 us (host wall clock, 1 run(s), NOT MCU timing)
Host RSS: 7892 KB -> 39480 KB (delta 31588 KB over 1 run(s))
=== ASan done ===
```

### 4.5 ASan sau sửa rò rỉ

`firmware/host/logs/asan_fixed.txt`

```text
﻿=== ASan run 1: default (first error stops the run) ===
wsl : =================================================================
At line:1 char:6
+ $o = wsl -e bash /mnt/d/DoanNhomQuy/firmware/host/run_asan.sh 2>&1; $ ...
+      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : NotSpecified: (===============...===============:String) [], RemoteException
    + FullyQualifiedErrorId : NativeCommandError
 
==658==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x51e000000a90 at pc 0x5e74a44c8ef8 bp 0x7fffa2f91f20 
sp 0x7fffa2f91f10
READ of size 4 at 0x51e000000a90 thread T0
    #0 0x5e74a44c8ef7 in Mamba_Forward /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/mamba.c:94
    #1 0x5e74a44d1a56 in mambahar_forward_logits /mnt/d/DoanNhomQuy/firmware/common/mambahar.c:58
    #2 0x5e74a44d3184 in main /mnt/d/DoanNhomQuy/firmware/host/host_main.c:100
    #3 0x784acfa2a1c9 in __libc_start_call_main ../sysdeps/nptl/libc_start_call_main.h:58
    #4 0x784acfa2a28a in __libc_start_main_impl ../csu/libc-start.c:360
    #5 0x5e74a44c55a4 in _start (/tmp/asan_hard+0x1b5a4) (BuildId: 4c275885f80d13793cc9783ae3c16bebda47af14)

0x51e000000a90 is located 0 bytes after 2576-byte region [0x51e000000080,0x51e000000a90)
allocated by thread T0 here:
    #0 0x784ad06fd9c7 in malloc ../../../../src/libsanitizer/asan/asan_malloc_linux.cpp:69
    #1 0x5e74a44c7fa2 in tensor_zeros /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/tensor.c:21

SUMMARY: AddressSanitizer: heap-buffer-overflow /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/mamba.c:94 
in Mamba_Forward
Shadow bytes around the buggy address:
  0x51e000000800: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000880: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000900: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000980: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000a00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
=>0x51e000000a80: 00 00[fa]fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000b00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000b80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000c00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000c80: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000d00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
==658==ABORTING
=== ASan run 2: recover mode (halt_on_error=0), leaks reported at exit ===
=================================================================
==666==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x51e000000a90 at pc 0x5f2fc1d3b140 bp 0x7ffe79b9e960 
sp 0x7ffe79b9e950
READ of size 4 at 0x51e000000a90 thread T0
    #0 0x5f2fc1d3b13f in Mamba_Forward /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/mamba.c:94
    #1 0x5f2fc1d443c5 in mambahar_forward_logits /mnt/d/DoanNhomQuy/firmware/common/mambahar.c:58
    #2 0x5f2fc1d45bff in main /mnt/d/DoanNhomQuy/firmware/host/host_main.c:100
    #3 0x77750122a1c9 in __libc_start_call_main ../sysdeps/nptl/libc_start_call_main.h:58
    #4 0x77750122a28a in __libc_start_main_impl ../csu/libc-start.c:360
    #5 0x5f2fc1d375a4 in _start (/tmp/asan_soft+0x1b5a4) (BuildId: f6467fbfe8d5373aa6f07e3bf4e701e9b4d93a62)

0x51e000000a90 is located 0 bytes after 2576-byte region [0x51e000000080,0x51e000000a90)
allocated by thread T0 here:
    #0 0x777501efd9c7 in malloc ../../../../src/libsanitizer/asan/asan_malloc_linux.cpp:69
    #1 0x5f2fc1d3a154 in tensor_zeros /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/tensor.c:21

SUMMARY: AddressSanitizer: heap-buffer-overflow /mnt/d/DoanNhomQuy/firmware/host/../../MambaLite-Micro/csrc/mamba.c:94 
in Mamba_Forward
Shadow bytes around the buggy address:
  0x51e000000800: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000880: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000900: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000980: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000a00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
=>0x51e000000a80: 00 00[fa]fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000b00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000b80: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000c00: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x51e000000c80: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
  0x51e000000d00: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07 
  Heap left redzone:       fa
  Freed heap region:       fd
  Stack left redzone:      f1
  Stack mid redzone:       f2
  Stack right redzone:     f3
  Stack after return:      f5
  Stack use after scope:   f8
  Global redzone:          f9
  Global init order:       f6
  Poisoned by user:        f7
  Container overflow:      fc
  Array cookie:            ac
  Intra object redzone:    bb
  ASan internal:           fe
  Left alloca redzone:     ca
  Right alloca redzone:    cb
Model_Forward completed.
Prediction: 0
Logits: -nan -nan -nan -nan -nan -nan
Elapsed time: 101071 us (host wall clock, 1 run(s), NOT MCU timing)
Host RSS: 7880 KB -> 39484 KB (delta 31604 KB over 1 run(s))
=== ASan done ===
```

### 4.6 ASan sau vendor mamba.c

`firmware/host/logs/asan_vendored.txt`

```text
﻿=== ASan run 1: default (first error stops the run) ===
Model_Forward completed.
Prediction: 0
Logits: -nan -nan -nan -nan -nan -nan
Elapsed time: 2731 us (host wall clock, 1 run(s), NOT MCU timing)
Host RSS: 7864 KB -> 8816 KB (delta 952 KB over 1 run(s))
=== ASan run 2: recover mode (halt_on_error=0), leaks reported at exit ===
Model_Forward completed.
Prediction: 0
Logits: -nan -nan -nan -nan -nan -nan
Elapsed time: 3305 us (host wall clock, 1 run(s), NOT MCU timing)
Host RSS: 7916 KB -> 8972 KB (delta 1056 KB over 1 run(s))
=== ASan done ===
```

### 4.7 ASan cuối (sạch)

`firmware/host/logs/asan_final.txt`

```text
﻿=== ASan run 1: default (first error stops the run) ===
Model_Forward completed.
Prediction: -2
Output: INVALID (non-finite logits), pred=-2 is not a class
Logits: nan nan nan nan nan nan
Elapsed time: 4770 us (host wall clock, 1 run(s), NOT MCU timing)
Host RSS: 7916 KB -> 8940 KB (delta 1024 KB over 1 run(s))
=== ASan run 2: recover mode (halt_on_error=0), leaks reported at exit ===
Model_Forward completed.
Prediction: -2
Output: INVALID (non-finite logits), pred=-2 is not a class
Logits: nan nan nan nan nan nan
Elapsed time: 3130 us (host wall clock, 1 run(s), NOT MCU timing)
Host RSS: 7884 KB -> 8848 KB (delta 964 KB over 1 run(s))
=== ASan done ===
```

### 4.8 Chấm điểm UCI trước vendor mamba.c

`firmware/host/logs/uci_test_pre_mamba_score.txt`

```text
��s a m p l e s :   2 9 4 7 
 
 n a n _ r o w s   ( n o n - f i n i t e   l o g i t s ) :   0 
 
 i n v a l i d _ r o w s   ( p r e d   <   0 ) :   0 
 
 a c c u r a c y :   0 . 9 2 6 7 
 
 m a c r o - F 1 :   0 . 9 2 6 5 
 
 F 1   p e r   c l a s s :   c 0 = 0 . 9 3 6 5   c 1 = 0 . 9 1 3 2   c 2 = 0 . 9 4 8 9   c 3 = 0 . 8 7 8 6   c 4 = 0 . 9 0 3 5   c 5 = 0 . 9 7 8 2 
 
 
```

### 4.9 Chấm điểm UCI cuối

`firmware/host/logs/uci_test_final_score.txt`

```text
��s a m p l e s :   2 9 4 7 
 
 n a n _ r o w s   ( n o n - f i n i t e   l o g i t s ) :   0 
 
 i n v a l i d _ r o w s   ( p r e d   <   0 ) :   0 
 
 a c c u r a c y :   0 . 9 2 6 7 
 
 m a c r o - F 1 :   0 . 9 2 6 5 
 
 F 1   p e r   c l a s s :   c 0 = 0 . 9 3 6 5   c 1 = 0 . 9 1 3 2   c 2 = 0 . 9 4 8 9   c 3 = 0 . 8 7 8 6   c 4 = 0 . 9 0 3 5   c 5 = 0 . 9 7 8 2 
 
 
```

### 4.10 Lần chạy 1 mẫu cuối — báo đầu ra không hợp lệ

`firmware/host/logs/host_20261018_202535.txt`

```text
��M o d e l _ F o r w a r d   c o m p l e t e d . 
 
 P r e d i c t i o n :   - 2 
 
 O u t p u t :   I N V A L I D   ( n o n - f i n i t e   l o g i t s ) ,   p r e d = - 2   i s   n o t   a   c l a s s 
 
 L o g i t s :   n a n   n a n   n a n   n a n   n a n   n a n 
 
 E l a p s e d   t i m e :   1 2 1 2   u s   ( h o s t   w a l l   c l o c k ,   1   r u n ( s ) ,   N O T   M C U   t i m i n g ) 
 
 H o s t   R S S :   2 0 3 2   K B   - >   2 5 3 6   K B   ( d e l t a   5 0 4   K B   o v e r   1   r u n ( s ) ) 
 
 
```

### 4.11 Build Portenta H7 (thành công)

`firmware/mambahar-portenta-h7/logs/build_20261018_201729.txt` — 8 dòng cuối

```text
 
 F l a s h :   [ = = = =             ]     3 9 . 1 %   ( u s e d   3 0 7 3 6 8   b y t e s   f r o m   7 8 6 4 3 2   b y t e s ) 
 
 B u i l d i n g   . p i o \ b u i l d \ p o r t e n t a _ h 7 _ m 7 \ f i r m w a r e . b i n 
 
 = = = = = = = = = = = = = = = = = = = = = = = = =   [ S U C C E S S ]   T o o k   2 2 . 5 6   s e c o n d s   = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 
```

### 4.12 Build ESP32-S3 (thành công)

`firmware/mambahar-esp32s3/logs/build_20261018_202030.txt` — 8 dòng cuối

```text
 
 M e r g e d   2   E L F   s e c t i o n s 
 
 S u c c e s s f u l l y   c r e a t e d   e s p 3 2 s 3   i m a g e . 
 
 = = = = = = = = = = = = = = = = = = = = = = = = =   [ S U C C E S S ]   T o o k   9 9 . 2 7   s e c o n d s   = = = = = = = = = = = = = = = = = = = = = = = = = 
 
 
```

## 5. File số liệu (nằm trong repo, không in vào phụ lục cho gọn)

| File | Bytes | SHA-256 |
|---|---|---|
| `firmware/host/logs/baseline_logits.csv` | 15,052 | 0DCB8C7A078488283F61D8FC71110897… |
| `firmware/host/logs/fixed_logits.csv` | 15,052 | 0DCB8C7A078488283F61D8FC71110897… |
| `firmware/host/logs/v2_batch201_logits.csv` | 15,052 | 0DCB8C7A078488283F61D8FC71110897… |
| `firmware/host/logs/v3_batch201_logits.csv` | 15,047 | 878D6ABAA6340D9FF8331636E7C7184E… |
| `firmware/host/logs/uci_test_logits_pre_mamba.csv` | 222,906 | 412A94B70EEF472A9620F31CA03324D5… |
| `firmware/host/logs/uci_test_logits_post_mamba.csv` | 222,906 | 412A94B70EEF472A9620F31CA03324D5… |
| `firmware/host/logs/uci_test_logits_final.csv` | 222,906 | 412A94B70EEF472A9620F31CA03324D5… |
| `firmware/host/logs/batch_demo.f32` | 458,280 | C6A81AA2FD7FEEA7AF4043C5B856C261… |
| `firmware/host/logs/uci_test.f32` | 6,719,160 | DE46EDE4BDE1BC4AE6D148428D754AD2… |

## 6. Checksum các file có mặt trong phụ lục này

| File | SHA-256 |
|---|---|
| `firmware/host/host_main.c` | `B63C3DA7CF06A21C0CC9BA827D033F76CA7773A67D9BAAA47BB4E401DEC4DC05` |
| `firmware/host/run_host_test.ps1` | `2DB22C955607B700888BDF007F6CEA831072AC7B2A9DE44A5AA086AD09F1A8B1` |
| `firmware/host/run_host_test.sh` | `E8803361C2BAA757582EB01586BEBF1611453C070760FCE5A668D8C0792053CD` |
| `firmware/host/run_asan.sh` | `A16CDEFEA7053BC46B59C42A0A24583286F9DD9081D1AD2E6E44A6B6E6D76BCA` |
| `firmware/host/uci_har.py` | `741B026DF77EF112790E2E61DA65566313C6108CF103174F2D6F96F82DD04971` |
| `firmware/host/make_batch.py` | `7B2831A54546F0982FDF8242B68C85C9D7C0D53EDCA4FBCDFBA7D991A59969D6` |
| `firmware/common/mamba_vs_upstream.diff` | `3D2E8BCD9DA6539351B26B3428B80BE451C87DA2FE3CB4525CF05A4CFD649E1E` |
| `firmware/host/logs/baseline_leak_1000runs.txt` | `D86DE9FE4C5F767DC0612FD392164AB66DE9B8B9DC458EA7120EA83673ADFFC3` |
| `firmware/host/logs/baseline_leak_4000runs.txt` | `8921AC72B8F1E39B00821399458D70751B362D331B721F8A1319CD7D3D02BED0` |
| `firmware/host/logs/host_20261018_194955.txt` | `8CBEBB6A218F9910BD4A10A669A958225381F4283D2312B701B10CCE4145E9EE` |
| `firmware/host/logs/asan_prefix.txt` | `05F1346058B596368570EBBD354BCD4D1C482116D6E36ECF6A86830782A7D9E8` |
| `firmware/host/logs/asan_fixed.txt` | `8610DEC8FB3331E51470469405F80A99D6246D37F88DFCA74DA31342960D2AF4` |
| `firmware/host/logs/asan_vendored.txt` | `C987904FF8E9CA107231252388E5A27D559A540F0A38E5A7A9ECA4FB558375DB` |
| `firmware/host/logs/asan_final.txt` | `D9E15A18C78A7344166242479EC3F3BB099848539A3E2E6A84AB5E011F79142A` |
| `firmware/host/logs/uci_test_pre_mamba_score.txt` | `BE7904AE295BCBF04FC7247E9BD4253C13D81FAC36C84E982B8BD92B813BB977` |
| `firmware/host/logs/uci_test_final_score.txt` | `BE7904AE295BCBF04FC7247E9BD4253C13D81FAC36C84E982B8BD92B813BB977` |
| `firmware/host/logs/host_20261018_202535.txt` | `614884B3015C73CFF2D02354EB4F7EC5ED6A04694123B7B54262E97A30FF399D` |
| `firmware/mambahar-portenta-h7/logs/build_20261018_201729.txt` | `1A192615A5819275EB8964E66EF80F03780A701FDA9C4725D8241D3C8E173C79` |
| `firmware/mambahar-esp32s3/logs/build_20261018_202030.txt` | `EE5181C5246B7F53415E620251EEF64C20C4C43144E235C212749821FFFFF027` |

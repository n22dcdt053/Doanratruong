# KIỂM CHỨNG SỐ HỌC TRÊN PC — phụ lục kèm báo cáo tiến độ

Ngày 18–20/10/2026 · Nhóm: Nguyễn Mai Trọng Quý (N22DCDT053), Võ Trung Nhân (N22DCDT043), Đinh Hữu Phước (N22DCDT047) · GVHD: TS. Nguyễn Thanh Bình

File sinh tự động: `python firmware/host/make_evidence_bundle.py` — đừng sửa tay.

## 0. Phạm vi tài liệu này

- Môi trường: **máy tính của nhóm — Windows gọi qua PowerShell, chương trình chạy trong WSL Ubuntu 24.04, gcc/g++ 13.3.0, x86-64**. Không có bo nào tham gia.

- Sinh từ cây làm việc tại commit `26bc3d8` — trạng thái cây khi sinh: **cây sạch (không tính file chưa được git theo dõi — gồm chính file này)** (`git rev-parse --short HEAD` + `git status --porcelain --untracked-files=no`).

- Kiểm chứng **số học**: đúng/sai kết quả, rò rỉ bộ nhớ, hành vi với đầu vào lỗi, của cùng bộ mã nguồn mô hình sẽ nạp lên bo (`firmware/common/`).

- **Khác biệt nguồn lệch tầng B (compiler/ngôn ngữ):** firmware Portenta biên dịch mô hình bằng **C++** (`arm-none-eabi-g++`, newlib, Cortex-M7 FPv5) vì `main.cpp` include các file `.c` trong `extern "C" {}`; host truyền thống dùng **gcc ở chế độ C** (glibc, x86-64 SSE2). Đây là một nguồn lệch thật của tầng B — đã đo bằng A/B build `g++` vs `gcc` trên cùng bộ nguồn, cùng runner (mục 2.4, log 4.13). Phần khác biệt còn lại (target, newlib vs glibc, FPU) chỉ chốt được khi đo trên bo thật.

- Firmware gọi `mambahar_forward()` (1 mẫu rồi reset); host gọi `mambahar_forward_logits()`. Hai hàm **cùng một thân hàm** (`mambahar_forward` gọi `forward_logits(input, NULL)` — `firmware/common/mambahar.c` dòng 161–164), nên không có nhánh tính toán riêng.

- **Không thay thế** bài test trên phần cứng: Flash/RAM theo map file, heap Mbed, 1.000 lượt liên tiếp, thời gian, năng lượng — chỉ số đo trên Portenta H7 mới tính là bằng chứng nghiệm thu.

- Thời gian in ra là wall clock của PC, **không phải** thời gian MCU. Các chỗ ghi *(ước tính)* / *(giả thuyết)* là suy luận chưa đo, không dùng làm bằng chứng.

## 1. Cách tái tạo toàn bộ file này

```powershell
cd D:\DoanNhomQuy
# Biên dịch + chạy host (1 lượt / 1000 / 4000 lượt, hoặc batch .f32 -> CSV)
powershell -ExecutionPolicy Bypass -File .\firmware\host\run_host_test.ps1 -Iterations 1
powershell -ExecutionPolicy Bypass -File .\firmware\host\run_host_test.ps1 -Batch .\firmware\host\logs\batch_demo.f32 -OutName out.csv
# A/B: gcc(C) vs g++(C++); upstream 1:1 vs bản dev (cùng runner, 2947 mẫu UCI)
wsl -e bash /mnt/d/DoanNhomQuy/firmware/host/run_cpp_vs_c.sh
wsl -e bash /mnt/d/DoanNhomQuy/firmware/host/run_upstream_cmp.sh
# ASan + UBSan + LSan: 1 mẫu, 1000 lượt, batch UCI
wsl -e bash /mnt/d/DoanNhomQuy/firmware/host/run_asan.sh
# UCI HAR: chuyển tập test -> .f32 rồi chấm điểm (in cả confusion matrix), và sinh lại phụ lục
python .\firmware\host\uci_har.py to-f32 "D:\DoanNhomQuy\data\UCI HAR Dataset" .\firmware\host\logs\uci_test.f32
python .\firmware\host\uci_har.py score .\firmware\host\logs\uci_test_logits_final.csv "D:\DoanNhomQuy\data\UCI HAR Dataset"
python .\firmware\host\make_evidence_bundle.py
```

Dataset: UCI HAR Dataset (archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip), giải nén vào `data/` (không commit, `.gitignore`).

## 2. Kết quả chính

### 2.1 Rò rỉ bộ nhớ — trước/sau khi sửa (log 4.1–4.2)

| | RSS 1000 lượt | RSS 4000 lượt |
|---|---|---|
| Trước sửa | +8.416 KB (tăng theo số lượt) | +32.460 KB |
| Sau sửa | **+496 KB** | **+500 KB** |

Diễn giải "+496/500 KB là lần chạm trang đầu tiên của glibc" và "RAM H7 (511 KB) sẽ hết sau khoảng 60 lượt nếu giữ rò rỉ" là **ước tính/giả thuyết — chưa đo trên bo**; bằng chứng đo được nằm ở chính các con số RSS trên. Kiểm chứng "không rò rỉ" chắc chắn nhất: LSan/ASan ở 2.2.

### 2.2 ASan / LSan / UBSan (log 4.4–4.7 cũ + 4.15 mở rộng)

- Trước sửa: `8128 byte(s) leaked in 6 allocation(s)` + `heap-buffer-overflow READ of size 4` tại `csrc/mamba.c:94`.

- Sau sửa rò rỉ: hết leak. Sau khi vendor `mamba.c` (sửa 1 dòng vòng chép `xz`): hết report.

- **Độ phủ hiện tại (log 4.15):** 4 lượt chạy — 1 mẫu (2 chế độ) + **1.000 lượt liên tiếp** + **batch đủ 2.947 mẫu UCI hữu hạn** — không còn report ASan/UBSan/LSan nào.

- Trong run 3 dưới ASan, RSS tăng **+108 MB** — đó là *artifact của allocator ASan* (redzone + quarantine giữ các vùng đã free), **không phải rò rỉ**: LSan không in report nào, và bản gcc thường (mục 2.1) chỉ +500 KB cho 4.000 lượt.

- KET QUA: ASan build (-O1) == bang chung (-O2) - bit-exact tren 2947 mau

### 2.3 Tập test UCI HAR, bản C tham chiếu (log 4.8–4.9)

Toàn bộ **2.947 mẫu test**, trọng số công khai, nhãn `y_test.txt` 1..6 trừ 1 (khớp `train.py` dòng 37/39):

| Chỉ số | Giá trị |
|---|---|
| Accuracy | **0,9267** |
| Macro-F1 | **0,9265** |
| F1 theo lớp | 0,937 / 0,913 / 0,949 / 0,879 / 0,904 / 0,978 |
| Số mẫu NaN / không hợp lệ | **0 / 0** |
| Confusion matrix + tên lớp | in ở log 4.9 |

Ý nghĩa: pipeline (tiền xử lý → 6 logits → argmax) khớp dữ liệu thật; đây **chỉ là điểm tham chiếu cho kiểm chứng số học MT1/MT3**, không dùng trong bảng so sánh Mamba↔MLP (checkpoint công khai chọn bằng validation chia ngẫu nhiên).

### 2.4 Đối chiếu bit-exact — phạm vi chính xác

Chỉ khẳng định **bit-exact cho các đầu ra hữu hạn** (tập UCI HAR chuẩn hóa: 0 mẫu NaN). Các cặp đã đối chiếu:

- KET QUA: gcc(C) == g++(C++) - bit-exact tren 2947 mau UCI (222906 B)

- KET QUA: build gcc moi == bang chung logs/uci_test_logits_final.csv - bit-exact

- KET QUA: upstream 1:1 == ban dev - pred bit-exact tren 2947 mau UCI

- KET QUA: ban dev (chay moi) == bang chung logs/uci_test_logits_final.csv - bit-exact

- Ba bản CSV 2.947 mẫu (trước khi vendor `mamba.c` / sau khi vendor / bản cuối): **trùng khớp từng byte** — `uci_test_logits_{pre_mamba,post_mamba,final}.csv`.

- Lô 201 mẫu (`baseline` → `fixed` → `v2`): **trùng khớp từng byte**. *Lưu ý phạm vi:* lô này gồm **1 mẫu demo thật (cho NaN) + 200 mẫu ngẫu nhiên**, nên chỉ là bằng chứng phụ cho lần sửa rò rỉ; kết luận chính dùng cặp 2.947 mẫu thật ở trên.

- `v2_batch201_logits.csv` vs `v3_batch201_logits.csv` (trước/sau thêm kiểm `isfinite`): khác 1 dòng; kích thước 15,052 → 15,047 B (Δ -5) — mẫu 0: pred (0 → -2), logit0 (-nan → nan), logit1 (-nan → nan), logit2 (-nan → nan), logit3 (-nan → nan), logit4 (-nan → nan), logit5 (-nan → nan). Đúng dự kiến: chỉ mẫu demo (NaN) đổi cách báo; dữ liệu thật hữu hạn không đổi.

### 2.5 Mẫu demo sai thang đầu vào → báo không hợp lệ (log 4.10)

Mẫu demo `sample_input.h` (thang thô ~ −39) cho logits NaN; trước đây bị tính thành lớp 0 (argmax trên NaN luôn sai) — **không phải dự đoán thật**. Bản vendor hiện tại kiểm `isfinite` cả 6 logits → trả `-2` và in `Output: INVALID`. Dữ liệu UCI chuẩn hóa không có mẫu NaN nào, xác nhận nguyên nhân là thang đầu vào.

## 3. Mã nguồn kiểm chứng (nguyên văn)

### 3.1 `host_main.c` — runner PC (dùng chung mã nguồn với firmware; cờ `-DUPSTREAM_ONLY` cho A/B upstream)

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

/* A/B build (run_upstream_cmp.sh): the 1:1 upstream mambahar.c exposes only the
 * prediction (no logits). Logits columns stay 0 in that CSV — compare pred only. */
#ifdef UPSTREAM_ONLY
static int model_forward(float *input, float *logits)
{
    (void)logits;
    return mambahar_forward(input);
}
#else
static int model_forward(float *input, float *logits)
{
    return mambahar_forward_logits(input, logits);
}
#endif

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
        int pred = model_forward(sample, logits);
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
    int pred = model_forward(input_data, logits); /* first 570 floats = [1, 10, 57] */
    for (int i = 1; i < iterations; i++)
        pred = model_forward(input_data, logits);
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
$out
# UTF-8 (không phải mặc định UTF-16 của Tee-Object) để log đọc/diff được như text
$out | Out-File -FilePath $log -Encoding utf8
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

### 3.4 `run_asan.sh` — ASan + UBSan + LSan (1 mẫu, 1000 lượt, batch UCI)

`firmware/host/run_asan.sh`

```bash
#!/usr/bin/env bash
# ASan/UBSan/LSan runs of the host build (same sources as the firmware), no MCU.
# Coverage: 1 sample (stop-on-first / recover) + 1000 continuous runs + the full
# 2947-sample UCI batch (finite outputs). Usage: bash run_asan.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
INC="-I$ROOT/firmware/common -I$ROOT/MambaLite-Micro/csrc -I$ROOT/MambaLite-Micro/examples/mambahar-arduino-6/include"
UCI="$ROOT/firmware/host/logs/uci_test.f32"
REF="$ROOT/firmware/host/logs/uci_test_logits_final.csv"

gcc -O1 -g -fsanitize=address,undefined -o /tmp/asan_hard "$HERE/host_main.c" $INC -lm
echo "=== ASan run 1: default (first error stops the run), 1 sample ==="
/tmp/asan_hard 1 || true

gcc -O1 -g -fsanitize=address,undefined -fsanitize-recover=all -o /tmp/asan_soft "$HERE/host_main.c" $INC -lm
echo "=== ASan run 2: recover mode (halt_on_error=0), 1 sample, leaks at exit ==="
ASAN_OPTIONS=halt_on_error=0:detect_leaks=1 /tmp/asan_soft 1 || true

echo "=== ASan run 3: recover mode, 1000 continuous runs (same demo sample) ==="
ASAN_OPTIONS=halt_on_error=0:detect_leaks=1 /tmp/asan_soft 1000 || true

if [ -f "$UCI" ]; then
    echo "=== ASan run 4: recover mode, full UCI batch (2947 finite samples) ==="
    ASAN_OPTIONS=halt_on_error=0:detect_leaks=1 /tmp/asan_soft --batch "$UCI" /tmp/asan_uci_batch.csv || true
    if [ -f "$REF" ] && cmp -s /tmp/asan_uci_batch.csv "$REF"; then
        echo "KET QUA: ASan build (-O1) == bang chung (-O2) - bit-exact tren 2947 mau"
    else
        echo "KET QUA: ASan build CSV khac bang chung (kiem tay neu can)"
    fi
else
    echo "=== ASan run 4: SKIP — thieu $UCI (chay uci_har.py to-f32 truoc) ==="
fi
echo "=== ASan done ==="
```

### 3.5 `run_cpp_vs_c.sh` — A/B gcc(C) vs g++(C++)

`firmware/host/run_cpp_vs_c.sh`

```bash
#!/usr/bin/env bash
# A/B: same host sources built with gcc (C) and g++ (C++), outputs compared byte
# for byte. Reason: the Portenta firmware compiles the model sources with a C++
# compiler (arm-none-eabi-g++ via main.cpp + extern "C"), the host runner uses
# gcc C — a tier-B divergence source that must be measured, not assumed.
# Usage: bash run_cpp_vs_c.sh   (needs logs/uci_test.f32, see uci_har.py to-f32)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
VENDOR="$ROOT/firmware/common"
CSRC="$ROOT/MambaLite-Micro/csrc"
UPIN="$ROOT/MambaLite-Micro/examples/mambahar-arduino-6/include"
BATCH="$ROOT/firmware/host/logs/uci_test.f32"
REF="$ROOT/firmware/host/logs/uci_test_logits_final.csv"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ ! -f "$BATCH" ]; then
    echo "Thieu $BATCH — chay truoc: python firmware/host/uci_har.py to-f32 <dataset_root> $BATCH"
    exit 1
fi

gcc -O2 -o "$TMP/run_c" "$HERE/host_main.c" -I"$VENDOR" -I"$CSRC" -I"$UPIN" -lm
g++ -O2 -x c++ -o "$TMP/run_cpp" "$HERE/host_main.c" -I"$VENDOR" -I"$CSRC" -I"$UPIN" -lm

"$TMP/run_c" --batch "$BATCH" "$TMP/out_c.csv" >/dev/null
"$TMP/run_cpp" --batch "$BATCH" "$TMP/out_cpp.csv" >/dev/null

if cmp -s "$TMP/out_c.csv" "$TMP/out_cpp.csv"; then
    echo "KET QUA: gcc(C) == g++(C++) - bit-exact tren 2947 mau UCI ($(stat -c%s "$TMP/out_c.csv") B)"
else
    echo "KET QUA: gcc(C) vs g++(C++) KHAC - diff:"
    diff "$TMP/out_c.csv" "$TMP/out_cpp.csv" | head -20 || true
fi
if [ -f "$REF" ] && cmp -s "$TMP/out_c.csv" "$REF"; then
    echo "KET QUA: build gcc moi == bang chung logs/uci_test_logits_final.csv - bit-exact"
fi
```

### 3.6 `run_upstream_cmp.sh` — A/B upstream 1:1 vs bản dev

`firmware/host/run_upstream_cmp.sh`

```bash
#!/usr/bin/env bash
# A/B: upstream 1:1 model sources vs the dev vendor copies, SAME host runner
# (host_main.c), full UCI test set. Only the two model files differ:
#   upstream: MambaLite-Micro/csrc/mamba.c + examples/mambahar-arduino-6/include/mambahar.c
#   dev:      firmware/common/{mamba.c,mambahar.c}
# Upstream returns the prediction only (no logits) -> built with -DUPSTREAM_ONLY;
# compare the pred columns. Finite outputs only (UCI data has 0 NaN).
# Usage: bash run_upstream_cmp.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
VENDOR="$ROOT/firmware/common"
CSRC="$ROOT/MambaLite-Micro/csrc"
UPIN="$ROOT/MambaLite-Micro/examples/mambahar-arduino-6/include"
BATCH="$ROOT/firmware/host/logs/uci_test.f32"
REF="$ROOT/firmware/host/logs/uci_test_logits_final.csv"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ ! -f "$BATCH" ]; then
    echo "Thieu $BATCH — chay truoc: python firmware/host/uci_har.py to-f32 <dataset_root> $BATCH"
    exit 1
fi

echo "sha256 (upstream / dev):"
sha256sum "$CSRC/mamba.c" "$UPIN/mambahar.c" "$VENDOR/mamba.c" "$VENDOR/mambahar.c"

gcc -O2 -DUPSTREAM_ONLY -o "$TMP/up" "$HERE/host_main.c" -I"$CSRC" -I"$UPIN" -lm
gcc -O2 -o "$TMP/dev" "$HERE/host_main.c" -I"$VENDOR" -I"$CSRC" -I"$UPIN" -lm

"$TMP/up" --batch "$BATCH" "$TMP/up.csv" >/dev/null
"$TMP/dev" --batch "$BATCH" "$TMP/dev.csv" >/dev/null

cut -d, -f1,2 "$TMP/up.csv" > "$TMP/up_pred.csv"
cut -d, -f1,2 "$TMP/dev.csv" > "$TMP/dev_pred.csv"
if cmp -s "$TMP/up_pred.csv" "$TMP/dev_pred.csv"; then
    echo "KET QUA: upstream 1:1 == ban dev - pred bit-exact tren 2947 mau UCI"
else
    echo "KET QUA: upstream 1:1 vs ban dev KHAC pred - diff:"
    diff "$TMP/up_pred.csv" "$TMP/dev_pred.csv" | head -20 || true
fi
if [ -f "$REF" ] && cmp -s "$TMP/dev.csv" "$REF"; then
    echo "KET QUA: ban dev (chay moi) == bang chung logs/uci_test_logits_final.csv - bit-exact"
fi
```

### 3.7 `uci_har.py` — chuyển UCI HAR sang .f32 + chấm điểm (confusion matrix, tên lớp)

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

# UCI HAR activity labels (activity_labels.txt in the dataset root, 1..6)
CLASS_NAMES = ["WALKING", "WALKING_UPSTAIRS", "WALKING_DOWNSTAIRS", "SITTING", "STANDING", "LAYING"]


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
    # y_test.txt holds 1..6; train.py maps labels to 0..5 with `- 1` (lines 37 and 39)
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
    print("classes: " + " ".join(f"{c}={n}" for c, n in enumerate(CLASS_NAMES)))
    cm = [[0] * 6 for _ in range(6)]
    for p, y in zip(preds, labels):
        if 0 <= p < 6:
            cm[y][p] += 1
    print("confusion matrix (rows=true, cols=pred; pred<0 excluded):")
    for y in range(6):
        print(f"true {y}: " + " ".join(f"{v:5d}" for v in cm[y]))


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

### 3.8 `make_batch.py` — sinh lô mẫu kiểm thử

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

### 3.9 `mamba_vs_upstream.diff` — thay đổi lõi `mamba.c` (1 dòng)

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

### 3.10 `mambahar_vs_upstream.diff` — thay đổi wrapper

`firmware/common/mambahar_vs_upstream.diff`

```diff
--- a/MambaLite-Micro/examples/mambahar-arduino-6/include/mambahar.c
+++ b/firmware/common/mambahar.c
@@ -1,17 +1,39 @@
 /**
  * @file mambahar.c
- * @brief mambahar model
+ * @brief mambahar model — dev (vendor) copy for the DATN firmware.
  * Copyright (c) 2025 MambaLite-Micro Authors
  * Licensed under the MIT License.
+ *
+ * Upstream (unmodified, MIT, commit 44d51fc):
+ *   MambaLite-Micro/examples/mambahar-arduino-6/include/mambahar.c
+ * Every change vs upstream is recorded with its diff in HUONG_PHAT_TRIEN.md,
+ * section "Diff cua ban vendor so voi upstream". Never edit the upstream file.
  */
+#include <stdlib.h> /* free(): the csrc headers do not pull in <stdlib.h> */
+
 #define B 1
 #define T 10
 #define F 57
 #define H 64
 #define C 6
-int mambahar_forward(float *input)
+
+/**
+ * Same computation as upstream mambahar_forward(), plus the six pre-softmax
+ * logits (MT2). logits may be NULL.
+ * Return: argmax 0..C-1; -1 = allocation/kernel failure; -2 = non-finite
+ * logits (invalid output — must NOT be counted as class 0).
+ */
+int mambahar_forward_logits(float *input, float *logits)
 {
-    Tensor *mamba_input = tensor_zeros(B, T, H);
+    Tensor *mamba_input = NULL, *output = NULL, *output_T = NULL;
+    Matrix *pooled = NULL, *y = NULL;
+    Mamba_Variables *model = NULL;
+    int pred = -1;
+    int max_idx = 0;
+
+    mamba_input = tensor_zeros(B, T, H);
+    if (!mamba_input)
+        goto cleanup;
     for (int b = 0; b < B; b++)
     {
         for (int t = 0; t < T; t++)
@@ -30,10 +52,17 @@
             }
         }
     }
-    Mamba_Variables *model = Mamba_Init();
-    Tensor *output = tensor_zeros(B, T, H);
-    Mamba_Forward(model, mamba_input, output);
-    Tensor *output_T = tensor_zeros(B, T, H);
+    model = Mamba_Init();
+    if (!model)
+        goto cleanup;
+    output = tensor_zeros(B, T, H);
+    if (!output)
+        goto cleanup;
+    if (Mamba_Forward(model, mamba_input, output) != Mamba_OK)
+        goto cleanup;
+    output_T = tensor_zeros(B, T, H);
+    if (!output_T)
+        goto cleanup;
     for (int b = 0; b < B; b++)
     {
         for (int t = 0; t < T; t++)
@@ -47,7 +76,9 @@
         }
     }
 
-    Matrix *pooled = matrix_zeros(B, H);
+    pooled = matrix_zeros(B, H);
+    if (!pooled)
+        goto cleanup;
     for (int b = 0; b < B; b++)
     {
         for (int h = 0; h < H; h++)
@@ -61,7 +92,9 @@
             pooled->data[b * H + h] = sum / T;
         }
     }
-    Matrix *y = matrix_zeros(B, C);
+    y = matrix_zeros(B, C);
+    if (!y)
+        goto cleanup;
     for (int b_idx = 0; b_idx < B; b_idx++)
     {
         for (int c = 0; c < C; c++)
@@ -74,7 +107,18 @@
             y->data[b_idx * C + c] = sum;
         }
     }
-    int max_idx = 0;
+    for (int c = 0; c < C; c++)
+    {
+        if (logits)
+        {
+            logits[c] = y->data[c];
+        }
+        if (!isfinite(y->data[c]))
+        {
+            pred = -2; /* non-finite logits: report invalid, never a class */
+            goto cleanup;
+        }
+    }
     for (int b = 0; b < B; b++)
     {
         max_idx = 0;
@@ -89,5 +133,32 @@
             }
         }
     }
-    return max_idx;
-}
\ No newline at end of file
+    pred = max_idx;
+
+cleanup:
+    if (y)
+        matrix_free(y);
+    if (pooled)
+        matrix_free(pooled);
+    if (output_T)
+        tensor_free(output_T);
+    if (output)
+        tensor_free(output);
+    if (model)
+        free(model);
+    if (mamba_input)
+        tensor_free(mamba_input);
+    if (pred < 0 && logits)
+    {
+        for (int c = 0; c < C; c++)
+        {
+            logits[c] = NAN;
+        }
+    }
+    return pred;
+}
+
+int mambahar_forward(float *input)
+{
+    return mambahar_forward_logits(input, NULL);
+}
```

## 4. Log thô (nguyên văn)

*Ghi chú:* vài log ASan cũ (4.4–4.5) chứa các dòng `NativeCommandError` / `CategoryInfo` — đó là phần **PowerShell gói stderr của `wsl` khi đọc log**, không phải lỗi của chương trình; báo cáo ASan thật nằm ngay sau các dòng đó.

### 4.1 Rò rỉ: 1000 lượt trước sửa

`firmware/host/logs/baseline_leak_1000runs.txt`

```text
Model_Forward completed.
Prediction: 0
Elapsed time: 462551 us (host wall clock, 1000 run(s), NOT MCU timing)
Host RSS: 1996 KB -> 10412 KB (delta 8416 KB over 1000 run(s))
```

### 4.2 Rò rỉ: 4000 lượt trước sửa

`firmware/host/logs/baseline_leak_4000runs.txt`

```text
Model_Forward completed.
Prediction: 0
Elapsed time: 1952866 us (host wall clock, 4000 run(s), NOT MCU timing)
Host RSS: 2000 KB -> 34460 KB (delta 32460 KB over 4000 run(s))
```

### 4.3 Baseline 1 mẫu trước sửa

`firmware/host/logs/host_20261018_194955.txt`

```text
Model_Forward completed.
Prediction: 0
Elapsed time: 416 us (host wall clock, 1 run(s), NOT MCU timing)
Host RSS: 2000 KB -> 2412 KB (delta 412 KB over 1 run(s))
```

### 4.4 ASan trước sửa (leak + overflow)

`firmware/host/logs/asan_prefix.txt`

```text
=== ASan run 1: default (first error stops the run) ===
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
=== ASan run 1: default (first error stops the run) ===
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
=== ASan run 1: default (first error stops the run) ===
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

### 4.7 ASan cuối (1 mẫu)

`firmware/host/logs/asan_final.txt`

```text
=== ASan run 1: default (first error stops the run) ===
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

### 4.8 Chấm điểm UCI trước vendor mamba.c (có confusion matrix)

`firmware/host/logs/uci_test_pre_mamba_score.txt`

```text
samples: 2947
nan_rows (non-finite logits): 0
invalid_rows (pred < 0): 0
accuracy: 0.9267
macro-F1: 0.9265
F1 per class: c0=0.9365 c1=0.9132 c2=0.9489 c3=0.8786 c4=0.9035 c5=0.9782
classes: 0=WALKING 1=WALKING_UPSTAIRS 2=WALKING_DOWNSTAIRS 3=SITTING 4=STANDING 5=LAYING
confusion matrix (rows=true, cols=pred; pred<0 excluded):
true 0:   487     3     6     0     0     0
true 1:    39   426     6     0     0     0
true 2:    18    12   390     0     0     0
true 3:     0     3     0   398    89     1
true 4:     0     0     0    17   515     0
true 5:     0    18     0     0     4   515
```

### 4.9 Chấm điểm UCI cuối (có confusion matrix)

`firmware/host/logs/uci_test_final_score.txt`

```text
samples: 2947
nan_rows (non-finite logits): 0
invalid_rows (pred < 0): 0
accuracy: 0.9267
macro-F1: 0.9265
F1 per class: c0=0.9365 c1=0.9132 c2=0.9489 c3=0.8786 c4=0.9035 c5=0.9782
classes: 0=WALKING 1=WALKING_UPSTAIRS 2=WALKING_DOWNSTAIRS 3=SITTING 4=STANDING 5=LAYING
confusion matrix (rows=true, cols=pred; pred<0 excluded):
true 0:   487     3     6     0     0     0
true 1:    39   426     6     0     0     0
true 2:    18    12   390     0     0     0
true 3:     0     3     0   398    89     1
true 4:     0     0     0    17   515     0
true 5:     0    18     0     0     4   515
```

### 4.10 Lần chạy 1 mẫu cuối — báo đầu ra không hợp lệ

`firmware/host/logs/host_20261018_202535.txt`

```text
Model_Forward completed.
Prediction: -2
Output: INVALID (non-finite logits), pred=-2 is not a class
Logits: nan nan nan nan nan nan
Elapsed time: 1212 us (host wall clock, 1 run(s), NOT MCU timing)
Host RSS: 2032 KB -> 2536 KB (delta 504 KB over 1 run(s))
```

### 4.11 Build Portenta H7 (thành công)

`firmware/mambahar-portenta-h7/logs/build_20261018_201729.txt` — 8 dòng cuối

```text
Indexing .pio\build\portenta_h7_m7\libFrameworkArduino.a
Linking .pio\build\portenta_h7_m7\firmware.elf
Checking size .pio\build\portenta_h7_m7\firmware.elf
Advanced Memory Usage is available via "PlatformIO Home > Project Inspect"
RAM:   [=         ]  14.8% (used 77256 bytes from 523624 bytes)
Flash: [====      ]  39.1% (used 307368 bytes from 786432 bytes)
Building .pio\build\portenta_h7_m7\firmware.bin
========================= [SUCCESS] Took 22.56 seconds =========================
```

### 4.12 Build ESP32-S3 (thành công)

`firmware/mambahar-esp32s3/logs/build_20261018_202030.txt` — 8 dòng cuối

```text
Building .pio\build\esp32s3\firmware.bin with action:
  "$PYTHONEXE" "$OBJCOPY" --chip esp32s3 elf2image --flash_mode ${__get_board_flash_mode(__env__)} --flash_freq ${__get_board_f_image(__env__)} --flash_size 8MB --elf-sha256-offset 0xb0 -o $TARGET $SOURCES
Building .pio\build\esp32s3\firmware.bin
esptool.py v4.5.1
Creating esp32s3 image...
Merged 2 ELF sections
Successfully created esp32s3 image.
========================= [SUCCESS] Took 99.27 seconds =========================
```

### 4.13 A/B gcc(C) vs g++(C++) trên 2.947 mẫu

`firmware/host/logs/cpp_vs_c_cmp_20261018.txt`

```text
KET QUA: gcc(C) == g++(C++) - bit-exact tren 2947 mau UCI (222906 B)
KET QUA: build gcc moi == bang chung logs/uci_test_logits_final.csv - bit-exact
```

### 4.14 A/B upstream 1:1 vs bản dev trên 2.947 mẫu

`firmware/host/logs/upstream_vs_final_cmp_20261018.txt`

```text
sha256 (upstream / dev):
ba59a6af7f93027087f608d0351971bda685509c347d2f3d905a7d8b9e970da9  /mnt/d/DoanNhomQuy/MambaLite-Micro/csrc/mamba.c
84ac465df0310dd09deac4423f11f625c6f352c4f3db6ccf03b947085bfe7957  /mnt/d/DoanNhomQuy/MambaLite-Micro/examples/mambahar-arduino-6/include/mambahar.c
a4a2aebb3d77cc5e5d8e8457cbfb8abb6f80e0f5ae54a38b5d31de41554fb5e3  /mnt/d/DoanNhomQuy/firmware/common/mamba.c
c4e20633eceffaf8839611a81c63bf33706903ca09987091d900f0859d4ee19d  /mnt/d/DoanNhomQuy/firmware/common/mambahar.c
KET QUA: upstream 1:1 == ban dev - pred bit-exact tren 2947 mau UCI
KET QUA: ban dev (chay moi) == bang chung logs/uci_test_logits_final.csv - bit-exact
```

### 4.15 ASan mở rộng: 1 mẫu + 1.000 lượt + batch 2.947 mẫu

`firmware/host/logs/asan_extended_20261018.txt`

```text
=== ASan run 1: default (first error stops the run), 1 sample ===
Model_Forward completed.
Prediction: -2
Output: INVALID (non-finite logits), pred=-2 is not a class
Logits: nan nan nan nan nan nan
Elapsed time: 3272 us (host wall clock, 1 run(s), NOT MCU timing)
Host RSS: 7924 KB -> 8944 KB (delta 1020 KB over 1 run(s))
=== ASan run 2: recover mode (halt_on_error=0), 1 sample, leaks at exit ===
Model_Forward completed.
Prediction: -2
Output: INVALID (non-finite logits), pred=-2 is not a class
Logits: nan nan nan nan nan nan
Elapsed time: 2882 us (host wall clock, 1 run(s), NOT MCU timing)
Host RSS: 7864 KB -> 8848 KB (delta 984 KB over 1 run(s))
=== ASan run 3: recover mode, 1000 continuous runs (same demo sample) ===
Model_Forward completed.
Prediction: -2
Output: INVALID (non-finite logits), pred=-2 is not a class
Logits: nan nan nan nan nan nan
Elapsed time: 2870100 us (host wall clock, 1000 run(s), NOT MCU timing)
Host RSS: 7884 KB -> 116176 KB (delta 108292 KB over 1000 run(s))
=== ASan run 4: recover mode, full UCI batch (2947 finite samples) ===
Batch: 2947 samples -> /tmp/asan_uci_batch.csv
KET QUA: ASan build (-O1) == bang chung (-O2) - bit-exact tren 2947 mau
=== ASan done ===
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
| `firmware/mambahar-portenta-h7/logs/build_20261018_201729.txt` | 4,477 | C5C075C2A17B35ADBE5FEAF35090E485… |
| `firmware/mambahar-esp32s3/logs/build_20261018_202030.txt` | 60,407 | 6C185C994B196C7CEB4003C7C19FD1D0… |

## 6. Checksum các file có mặt trong phụ lục này

| File | SHA-256 |
|---|---|
| `firmware/host/host_main.c` | `56E8E389AFB8F921EBC0E1CBB2D6217413EDDEE89D1A62EA248269813AFD2E44` |
| `firmware/host/run_host_test.ps1` | `0732498B413B28F725A76CE491D62BDFE43ACD8A25F9109A9449A762F3607334` |
| `firmware/host/run_host_test.sh` | `E8803361C2BAA757582EB01586BEBF1611453C070760FCE5A668D8C0792053CD` |
| `firmware/host/run_asan.sh` | `7DF1B6FF38D5919EAECF81FE95046B84F024DFC7210051B3F208BA89DDB0DF09` |
| `firmware/host/run_cpp_vs_c.sh` | `11C283188942EB033208D04114BCE13261DB0494404CC9A75CDEA95A32ACFE10` |
| `firmware/host/run_upstream_cmp.sh` | `8A7E358BD0081089338762E409F4163C60C09F2DF20CF83CD8C5839FEB7C7CC2` |
| `firmware/host/uci_har.py` | `C6E8D3A3F2FD855187F63B90BE4F0D2565BC4BF6075ED5851B7ED3194F6AA374` |
| `firmware/host/make_batch.py` | `7B2831A54546F0982FDF8242B68C85C9D7C0D53EDCA4FBCDFBA7D991A59969D6` |
| `firmware/common/mamba_vs_upstream.diff` | `3D2E8BCD9DA6539351B26B3428B80BE451C87DA2FE3CB4525CF05A4CFD649E1E` |
| `firmware/common/mambahar_vs_upstream.diff` | `39CC03ED53E72AA5944F3498F5BA5423CEC4F3CEA13CBF8CE7DA5FAF6B96FA6F` |
| `firmware/host/logs/baseline_leak_1000runs.txt` | `528672FDBADEDE64A863F221CBBF84A7A8CB8F9005934CD6AA3D3808BA2B2D39` |
| `firmware/host/logs/baseline_leak_4000runs.txt` | `E7A3C2CFEF486069426ED8D845C0641E217AC5B1F63FCFF627D6A190F0572522` |
| `firmware/host/logs/host_20261018_194955.txt` | `5FF14369A00BFCAC2EB98C21D8841F98A19594115CE4E6E4605DF5E2DCE0F828` |
| `firmware/host/logs/asan_prefix.txt` | `05F1346058B596368570EBBD354BCD4D1C482116D6E36ECF6A86830782A7D9E8` |
| `firmware/host/logs/asan_fixed.txt` | `8610DEC8FB3331E51470469405F80A99D6246D37F88DFCA74DA31342960D2AF4` |
| `firmware/host/logs/asan_vendored.txt` | `C987904FF8E9CA107231252388E5A27D559A540F0A38E5A7A9ECA4FB558375DB` |
| `firmware/host/logs/asan_final.txt` | `D9E15A18C78A7344166242479EC3F3BB099848539A3E2E6A84AB5E011F79142A` |
| `firmware/host/logs/uci_test_pre_mamba_score.txt` | `26AAC468ABDD22B451AE28F323D72138B053D2D4F7BEB78E729DFEEFE22497B0` |
| `firmware/host/logs/uci_test_final_score.txt` | `26AAC468ABDD22B451AE28F323D72138B053D2D4F7BEB78E729DFEEFE22497B0` |
| `firmware/host/logs/host_20261018_202535.txt` | `A6B9269A4299DDB53F7EBB8AE7D793D80D2AF83693E62055AAE944032629FB0F` |
| `firmware/mambahar-portenta-h7/logs/build_20261018_201729.txt` | `C5C075C2A17B35ADBE5FEAF35090E485752CAB2CFD5F10C0DDA8D22DE6555054` |
| `firmware/mambahar-esp32s3/logs/build_20261018_202030.txt` | `6C185C994B196C7CEB4003C7C19FD1D04837CC9963D33C86DFBBE8DF5942851C` |
| `firmware/host/logs/cpp_vs_c_cmp_20261018.txt` | `B30CD56BCA36E64AFCF77BD659E4E7AE25203F2145A83230DDCB0C355E727E6D` |
| `firmware/host/logs/upstream_vs_final_cmp_20261018.txt` | `836DFAA6F13FF1D4121E10F135B8E64B22E2B20B7FC37F2750CD51FEF0193AAA` |
| `firmware/host/logs/asan_extended_20261018.txt` | `EA946CEB686AFE4FA5FB52339869E6291E6227DFD8F244E5D6BF67C24393F450` |

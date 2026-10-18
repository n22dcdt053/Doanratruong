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
        echo "KET QUA: ASan build (-O1) == bang chung (-O2) — bit-exact tren 2947 mau"
    else
        echo "KET QUA: ASan build CSV khac bang chung (kiem tay neu can)"
    fi
else
    echo "=== ASan run 4: SKIP — thieu $UCI (chay uci_har.py to-f32 truoc) ==="
fi
echo "=== ASan done ==="

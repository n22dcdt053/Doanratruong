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
    echo "KET QUA: gcc(C) == g++(C++) — bit-exact tren 2947 mau UCI ($(stat -c%s "$TMP/out_c.csv") B)"
else
    echo "KET QUA: gcc(C) vs g++(C++) KHAC — diff:"
    diff "$TMP/out_c.csv" "$TMP/out_cpp.csv" | head -20 || true
fi
if [ -f "$REF" ] && cmp -s "$TMP/out_c.csv" "$REF"; then
    echo "KET QUA: build gcc moi == bang chung logs/uci_test_logits_final.csv — bit-exact"
fi

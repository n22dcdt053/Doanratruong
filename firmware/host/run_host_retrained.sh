#!/usr/bin/env bash
# Build va chay runner host voi trong so Mamba huan luyen lai (ml/results/mamba_retrained).
#
#   bash firmware/host/run_host_retrained.sh --batch IN.f32 OUT.csv
#
# -I ml/results/mamba_retrained dat TRUOC cac duong dan include upstream de
# mamba_weights.h moi thang ban cong khai. Script in sha256 header va dung
# danh sach header ma gcc thuc su doc (gcc -MM) de xac nhan header nao duoc dung.
# Khong sua host_main.c hay run_host_test.sh.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
VENDOR="$ROOT/firmware/common"
CSRC="$ROOT/MambaLite-Micro/csrc"
UPSTREAM_INC="$ROOT/MambaLite-Micro/examples/mambahar-arduino-6/include"
RETRAINED="$ROOT/ml/results/mamba_retrained"
HEADER="$RETRAINED/mamba_weights.h"
BIN="$(mktemp /tmp/mambahar_retrained.XXXXXX)"
trap 'rm -f "$BIN"' EXIT

if [ ! -f "$HEADER" ]; then
    echo "khong thay $HEADER (chay ml/export_mamba_c.py truoc)" >&2
    exit 2
fi

INCLUDES=(-I"$RETRAINED" -I"$VENDOR" -I"$CSRC" -I"$UPSTREAM_INC")

echo "header: $HEADER"
sha256sum "$HEADER"

gcc -O2 -o "$BIN" "$HERE/host_main.c" "${INCLUDES[@]}" -lm

USED="$(gcc -MM "$HERE/host_main.c" "${INCLUDES[@]}" | tr ' \\' '\n\n' | grep -m1 'mamba_weights\.h$' || true)"
echo "header ma gcc doc: $USED"
if [ "$USED" != "$HEADER" ]; then
    echo "CANH BAO: header dung khong phai ban huan luyen lai" >&2
    exit 3
fi

if [ "$#" -eq 0 ]; then set -- 1; fi
"$BIN" "$@"

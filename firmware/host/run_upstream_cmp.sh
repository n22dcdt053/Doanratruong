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

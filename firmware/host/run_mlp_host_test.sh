#!/usr/bin/env bash
# Build va chay runner MLP tren PC (WSL/Linux).
#
#   bash firmware/host/run_mlp_host_test.sh --batch IN.f32 OUT.csv
#
# IN.f32: N x 570 float32 LE (561 dac trung + 9 so 0 dem).
# OUT.csv: sample_index,pred,logit0..logit5 (giong host_main --batch).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BIN="${TMPDIR:-/tmp}/host_main_mlp_bin"

gcc -O2 -std=c11 -I "$ROOT/firmware/common" \
    -o "$BIN" \
    "$ROOT/firmware/host/host_main_mlp.c" \
    "$ROOT/firmware/common/mlp_har.c" \
    -lm

exec "$BIN" "$@"

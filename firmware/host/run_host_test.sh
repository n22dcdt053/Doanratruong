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

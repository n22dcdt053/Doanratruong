#!/usr/bin/env bash
# Host build + run of the same C model code used by the Portenta H7 firmware.
# Usage: bash run_host_test.sh [iterations]   (default 1)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"                                  # repo root
INC="$ROOT/MambaLite-Micro/examples/mambahar-arduino-6/include"
ITER="${1:-1}"
BIN="$(mktemp /tmp/mambahar_host.XXXXXX)"
trap 'rm -f "$BIN"' EXIT
gcc -O2 -o "$BIN" "$HERE/host_main.c" -I"$INC" -lm
"$BIN" "$ITER"

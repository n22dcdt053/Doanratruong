#!/usr/bin/env bash
# ASan/UBSan run of the host build (same sources as the firmware), no MCU.
# Run 1 halts at the first finding; run 2 keeps going and reports leaks at exit.
# Usage: bash run_asan.sh   (from anywhere)
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
INC="-I$ROOT/firmware/common -I$ROOT/MambaLite-Micro/examples/mambahar-arduino-6/include"

gcc -O1 -g -fsanitize=address,undefined -o /tmp/asan_hard "$HERE/host_main.c" $INC -lm
echo "=== ASan run 1: default (first error stops the run) ==="
/tmp/asan_hard 1 || true

gcc -O1 -g -fsanitize=address,undefined -fsanitize-recover=all -o /tmp/asan_soft "$HERE/host_main.c" $INC -lm
echo "=== ASan run 2: recover mode (halt_on_error=0), leaks reported at exit ==="
ASAN_OPTIONS=halt_on_error=0:detect_leaks=1 /tmp/asan_soft 1 || true
echo "=== ASan done ==="

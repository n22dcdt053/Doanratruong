#!/usr/bin/env bash
# Build va chay test lap lich tren PC (gcc, khong ESP-IDF).
#   bash firmware/energy-esp32s3/test/run_sched_host.sh            # chay + so voi sched_expected.txt
#   bash firmware/energy-esp32s3/test/run_sched_host.sh --update   # ghi lai sched_expected.txt
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/../src"
BIN="$(mktemp "${TMPDIR:-/tmp}/sched_host.XXXXXX")"
OUT="$(mktemp "${TMPDIR:-/tmp}/sched_out.XXXXXX")"
trap 'rm -f "$BIN" "$BIN.exe" "$OUT"' EXIT

gcc -std=c11 -Wall -Wextra -Werror -O2 -o "$BIN" "$HERE/sched_host.c" "$SRC/energy_sched.c"
"$BIN" > "$OUT"

if [ "${1:-}" = "--update" ]; then
    cp "$OUT" "$HERE/sched_expected.txt"
    echo "da ghi $HERE/sched_expected.txt"
elif cmp -s "$OUT" "$HERE/sched_expected.txt"; then
    echo "KHOP sched_expected.txt ($(wc -l < "$OUT") dong)"
else
    echo "KHAC sched_expected.txt" >&2
    diff "$OUT" "$HERE/sched_expected.txt" | head -40 >&2 || true
    exit 1
fi

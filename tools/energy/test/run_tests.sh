#!/usr/bin/env bash
# Chay toan bo kiem thu cong cu do nang luong (du lieu tong hop, khong can bo/COM).
#   bash tools/energy/test/run_tests.sh
# Chon Python: bien PYTHON (neu dat), neu khong thi "py -3" (Windows), roi python3. Khong dung "python" tran.
set -euo pipefail
# -I -B: isolated, khong ghi __pycache__ (repo khong ignore thu muc nay)
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "${PYTHON:-}" ]; then
    PY=("$PYTHON")
elif command -v py >/dev/null 2>&1 && py -3 -c "pass" >/dev/null 2>&1; then
    PY=(py -3)
elif command -v python3 >/dev/null 2>&1 && python3 -c "pass" >/dev/null 2>&1; then
    PY=(python3)
else
    echo "khong tim thay Python 3 (dat bien PYTHON)" >&2
    exit 2
fi

fail=0
for t in test_schedule test_capture test_merge; do
    echo "=== $t ==="
    if "${PY[@]}" -I -B "$HERE/$t.py"; then
        :
    else
        echo "THAT BAI: $t" >&2
        fail=1
    fi
done

echo "=== schedule.py --selftest ==="
"${PY[@]}" -I -B "$HERE/../schedule.py" --selftest >/dev/null || fail=1

if [ "$fail" -ne 0 ]; then
    echo "run_tests: CO CA THAT BAI" >&2
    exit 1
fi
echo "run_tests: toan bo ca pass"

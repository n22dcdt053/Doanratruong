#!/usr/bin/env python3
"""Kiem thu schedule.py (ban Python cua energy_sched.c, Brief 07). Chay: py -3 -I tools/energy/test/test_schedule.py

Neu firmware/energy-esp32s3/test/sched_expected.txt co trong cay thi so tung byte; neu vang thi in
'bo qua: chua co sched_expected.txt (Brief 07)' (khong tu tao tep do)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import schedule as sc  # noqa: E402


def main():
    # gia tri co dinh tu Brief 07 / sched_expected.txt
    s, outs = 1, []
    for _ in range(5):
        s = sc.xorshift32(s)
        outs.append(s)
    assert outs == [270369, 67634689, 2647435461, 307599695, 2398689233], outs
    assert sc.xorshift32(0xFFFFFFFF) < 2 ** 32
    print("PASS xorshift32_seed1")

    for seed in (0, 1, 42, 123456789, 4294967295):
        p = sc.permutation(seed)
        assert sorted(p) == list(range(60)), seed
        assert p == sc.permutation(seed)
    assert sc.permutation(0) == sc.permutation(1)
    assert sc.permutation(1)[:5] == [3, 52, 2, 6, 20]
    assert sc.permutation(42)[:5] == [10, 2, 19, 56, 37]
    print("PASS permutation")

    for order in ("MF", "LF"):
        plan = sc.pulse_plan(order)
        assert len(plan) == 32 and [p["pulse"] for p in plan] == list(range(1, 33))
        first = "mamba" if order == "MF" else "mlp"
        assert all(p["cfg"] == first for p in plan[:16]) and all(p["cfg"] != first for p in plan[16:])
        for c in (0, 16):
            assert [p["kind"] for p in plan[c:c + 16]] == ["EMP"] * 10 + ["BLK"] * 6
            assert [p["block"] for p in plan[c + 10:c + 16]] == list(range(6))
    print("PASS pulse_plan")

    for line, why in [("", "cmd"), ("START", "argc"), ("START 1 MF", "argc"), ("STOP 1 MF 1", "cmd"),
                      ("START 0 MF 1", "session"), ("START 6 MF 1", "session"), ("START 1 mf 1", "order"),
                      ("START 1 MF -5", "seed"), ("START 1 MF 4294967296", "seed"), ("START 1 MF 1 x", "argc"),
                      ("START 1 MF 00000000042", "seed")]:
        assert sc.parse_start(line)[3] == why, (line, sc.parse_start(line))
    assert sc.parse_start("START 3 LF 4294967295") == (3, "LF", 4294967295, None)
    assert sc.parse_start("START\t2\tMF  7") == (2, "MF", 7, None)     # tach bang dau cach/tab nhu ban C
    print("PASS parse_start")

    # selftest() in ra stdout noi dung; chay qua main() de kiem tra ma thoat va tin nhan
    import io
    from contextlib import redirect_stderr, redirect_stdout
    err = io.StringIO()
    with redirect_stderr(err), redirect_stdout(io.TextIOWrapper(io.BytesIO())):
        rc = sc.main(["--selftest"])
    msg = err.getvalue().strip()
    assert rc == 0, msg
    assert msg.startswith("KHOP") or msg.startswith("bo qua: chua co sched_expected.txt (Brief 07)"), msg
    print("PASS selftest: " + msg.splitlines()[0][:80])
    print("test_schedule: 5 ca PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

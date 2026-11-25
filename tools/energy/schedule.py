#!/usr/bin/env python3
"""Lap lich phien do nang luong (Brief 08, muc H2) - ban Python cua firmware/energy-esp32s3/src/energy_sched.c.

Hop dong voi Brief 07, muc 3 ("Lap lich"). Chi dung thu vien chuan.

  xorshift32(s): s ^= (s << 13) & 0xFFFFFFFF; s ^= s >> 17; s ^= (s << 5) & 0xFFFFFFFF; return s   (seed 0 -> 1)
  permutation(seed): perm = list(range(60)); i tu 59 xuong 1: j = xorshift32() % (i+1); doi perm[i], perm[j]
  pulse_plan(order): 32 muc theo thu tu thuc te; MF: mamba roi mlp; LF: mlp roi mamba;
                     moi cfg: 10 muc EMP roi 6 muc BLK (block 0..5); pulse danh so lien tuc tu 1.

Dung lam thu vien (merge_blocks.py import) hoac chay:
  py -3 -I tools/energy/schedule.py --selftest [--expected <tep>]

--selftest in ra stdout noi dung theo dung dinh dang test/sched_expected.txt cua Brief 07; ket qua so sanh
(KHOP / KHONG KHOP / bo qua) in ra stderr. Tep sched_expected.txt khong duoc tu tao o day.
"""
import argparse
import re
import sys
from pathlib import Path

N_PERM = 60
BLOCK_INF = 10
N_BLOCKS = 6
N_EMPTY = 10
PULSES_PER_CFG = N_EMPTY + N_BLOCKS
PULSES_PER_SESSION = 2 * PULSES_PER_CFG  # 32

MASK32 = 0xFFFFFFFF

DEFAULT_EXPECTED = (Path(__file__).resolve().parents[2] / "firmware" / "energy-esp32s3" / "test"
                    / "sched_expected.txt")


def xorshift32(s):
    """Mot buoc xorshift32 (uint32). Gia tri tra ve cung la trang thai moi."""
    s &= MASK32
    s ^= (s << 13) & MASK32
    s ^= s >> 17
    s ^= (s << 5) & MASK32
    return s


def permutation(seed):
    """Hoan vi 60 mau (Fisher-Yates tu cuoi, xorshift32). seed 0 dung nhu seed 1."""
    s = (seed & MASK32) or 1
    perm = list(range(N_PERM))
    for i in range(N_PERM - 1, 0, -1):
        s = xorshift32(s)
        j = s % (i + 1)
        perm[i], perm[j] = perm[j], perm[i]
    return perm


def pulse_plan(order):
    """Ke hoach 32 xung. order = 'MF' hoac 'LF'. Moi muc: dict(pulse, cfg, kind, block)
    (block = None voi EMP). pulse bat dau tu 1."""
    if order not in ("MF", "LF"):
        raise ValueError("order phai la MF hoac LF: %r" % (order,))
    cfgs = ("mamba", "mlp") if order == "MF" else ("mlp", "mamba")
    plan = []
    n = 0
    for cfg in cfgs:
        for _ in range(N_EMPTY):
            n += 1
            plan.append({"pulse": n, "cfg": cfg, "kind": "EMP", "block": None})
        for b in range(N_BLOCKS):
            n += 1
            plan.append({"pulse": n, "cfg": cfg, "kind": "BLK", "block": b})
    return plan


def block_indices(perm, block):
    """10 chi so mau cua khoi `block` (0..5): vi tri 10b..10b+9 cua hoan vi."""
    return perm[BLOCK_INF * block: BLOCK_INF * block + BLOCK_INF]


_TOKEN = re.compile(r"[^ \t]+")


def parse_start(line):
    """Phan tich 'START <session 1..5> <order MF|LF> <seed uint32>' dung nhu energy_parse_start (C).
    Tach token bang dau cach/tab (khong phai moi khoang trang). Tra ve (session, order, seed, None)
    hoac (None, None, None, ly_do) voi ly_do trong cmd/argc/session/order/seed."""
    toks = _TOKEN.findall(line)
    if not toks or toks[0] != "START":
        return None, None, None, "cmd"
    if len(toks) != 4:
        return None, None, None, "argc"
    t_session, t_order, t_seed = toks[1], toks[2], toks[3]
    if len(t_session) != 1 or not ("1" <= t_session <= "5"):
        return None, None, None, "session"
    if t_order not in ("MF", "LF"):
        return None, None, None, "order"
    if len(t_seed) == 0 or len(t_seed) > 10 or any(c < "0" or c > "9" for c in t_seed):
        return None, None, None, "seed"
    v = int(t_seed)
    if v > MASK32:
        return None, None, None, "seed"
    return int(t_session), t_order, v, None


def render_expected():
    """Noi dung giong het stdout cua firmware/energy-esp32s3/test/sched_host.c (moi dong ket thuc LF)."""
    out = []
    out.append("# energy_sched host test (Brief 07, muc 3). Dinh dang co dinh; Brief 08 so tung byte.")
    s = 1
    outs = []
    for _ in range(5):
        s = xorshift32(s)
        outs.append(str(s))
    out.append("# xorshift32 seed=1 five outputs: " + " ".join(outs))

    for seed in (1, 42, 123456789):
        out.append("# permutation seed=%d" % seed)
        out.append(" ".join(str(v) for v in permutation(seed)))
    out.append("# seed 0 == seed 1: %s" % ("yes" if permutation(0) == permutation(1) else "no"))

    out.append("# START hop le (seed 42), 5 phien x 2 thu tu; ke hoach xung khong phu thuoc phien")
    for ss in range(1, 6):
        for o in ("MF", "LF"):
            out.append(_start_line("START %d %s 42" % (ss, o)))
    out.append("# START sai/bien")
    bad = ["", "START", "START 1 MF", "STOP 1 MF 1", "START 0 MF 1", "START 6 MF 1",
           "START 10 MF 1", "START 1 XX 1", "START 1 mf 1", "START 1 MF -5",
           "START 1 MF 4294967296", "START 1 MF 4294967295", "START 1 MF 0",
           "START 1 MF 1 extra", "START 1 MF 12ab", "START 1 MF 00000000042"]
    for b in bad:
        out.append(_start_line(b))

    for order in ("MF", "LF"):
        out.append("# pulse_plan order=%s pulses=%d" % (order, PULSES_PER_SESSION))
        for p in pulse_plan(order):
            blk = "-" if p["block"] is None else str(p["block"])
            out.append("pulse=%d cfg=%s kind=%s block=%s" % (p["pulse"], p["cfg"], p["kind"], blk))
    return "\n".join(out) + "\n"


def _start_line(line):
    s, o, seed, why = parse_start(line)
    if why is None:
        return "%s -> ACK session=%d order=%s seed=%d pulses=%d plan=%s" % (
            line, s, o, seed, PULSES_PER_SESSION, o)
    return "%s -> ERR %s" % (line, why)


def _first_diff(a, b):
    la, lb = a.split(b"\n"), b.split(b"\n")
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else None
        y = lb[i] if i < len(lb) else None
        if x != y:
            return i + 1, x, y
    return None


def selftest(expected_path):
    text = render_expected()
    data = text.encode("ascii")
    sys.stdout.buffer.write(data)  # nhi phan: giu LF tren Windows
    sys.stdout.flush()
    if not expected_path.is_file():
        print("bo qua: chua co sched_expected.txt (Brief 07)", file=sys.stderr)
        return 0
    exp = expected_path.read_bytes()
    if exp == data:
        print("KHOP %s (%d dong, %d byte)" % (expected_path, data.count(b"\n"), len(data)), file=sys.stderr)
        return 0
    print("KHONG KHOP %s" % expected_path, file=sys.stderr)
    d = _first_diff(data, exp)
    if d:
        print("dong khac dau tien: %d\n  python  : %r\n  expected: %r" % d, file=sys.stderr)
    if b"\r\n" in exp:
        print("luu y: tep expected co CRLF; kiem tra core.autocrlf / checkout (shell script yeu cau LF)",
              file=sys.stderr)
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true",
                    help="in hoan vi/START/pulse_plan theo dinh dang sched_expected.txt va so voi tep neu co")
    ap.add_argument("--expected", type=Path, default=DEFAULT_EXPECTED,
                    help="tep sched_expected.txt (mac dinh: %s)" % DEFAULT_EXPECTED)
    ap.add_argument("--perm", type=lambda x: int(x, 0), metavar="SEED", help="in hoan vi cho seed")
    ap.add_argument("--plan", choices=("MF", "LF"), help="in ke hoach xung cho order")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest(a.expected)
    if a.perm is not None:
        print(" ".join(str(v) for v in permutation(a.perm)))
        return 0
    if a.plan:
        for p in pulse_plan(a.plan):
            print("pulse=%d cfg=%s kind=%s block=%s" % (
                p["pulse"], p["cfg"], p["kind"], "-" if p["block"] is None else p["block"]))
        return 0
    ap.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

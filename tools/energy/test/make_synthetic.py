#!/usr/bin/env python3
"""Dung mot phien do GIA (du lieu tong hop) dung dinh dang logger + log UART devkit cua Brief 07/08.

Chi de kiem thu code ghep (merge_blocks.py). KHONG phai so do. Cong suat nen va cong suat khoi la hang so da biet
nen test co the kiem tra E_raw/E_net khoi phuc duoc gia tri da dung. Hai dong ho (logger, devkit) lech nhau mot hang so.

  py -3 -I tools/energy/test/make_synthetic.py --order MF --session 1 --out-dir <thu muc>
"""
import argparse
import bisect
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import schedule  # noqa: E402

V_BUS = 5.0                 # V (bus_raw = 4000)
R_SHUNT = 0.1               # ohm (danh nghia)
I_IDLE = 0.060              # A
I_CFG = {"mamba": 0.120, "mlp": 0.100}                # A trong khi suy luan
BLOCK_US = {"mamba": 1_200_000, "mlp": 107_000}      # do dai khoi 10 suy luan
DEVKIT_CLOCK_OFFSET_US = 777_000_000                 # devkit va logger la hai dong ho khac nhau
EMP_WIDTH_US = 1000


class Synth:
    """Mot phien tong hop. Cac truong deu sua duoc truoc khi render (test dung de gay loi)."""

    def __init__(self):
        self.order = "MF"
        self.session = 1
        self.seed = 42
        self.samples = []        # (t_us, shunt_raw, bus_raw)
        self.edges = []          # (t_us, level)
        self.errors = []         # (t_us, code)
        self.dev = []            # dict moi xung devkit
        self.truth = []          # dict moi xung: e_raw_mj, e_net_mj
        self.p_idle_w = V_BUS * I_IDLE
        self.period_us = 2200
        self.lines_extra = []    # dong logger them vao cuoi (dong rac)


def build(order="MF", session=1, seed=42, period_us=2200, rng_seed=1, i_cfg=None, block_us=None, conv="instant"):
    """conv="instant": mau = gia tri tuc thoi tai thoi diem mau (kiem thu code tich phan, khong co tre chuyen doi);
    conv="window": mau = trung binh dong dien trong 1,1 ms chuyen doi ket thuc 0,2 ms truoc thoi diem mau
    (mo phong tre/lam tron cua INA226 - la tinh chat cua phep do, gay sai so he thong o hai bien khoi)."""
    i_cfg = dict(I_CFG, **(i_cfg or {}))
    block_us = dict(BLOCK_US, **(block_us or {}))
    rng = random.Random(rng_seed)
    s = Synth()
    s.order, s.session, s.seed, s.period_us = order, session, seed, period_us
    plan = schedule.pulse_plan(order)
    perm = schedule.permutation(seed)

    seg = []                       # (t0, t1, dong dien A) khoang co tai
    t = 3_000_000                  # ACK tai t = 3 s (logger bat dau o 0)
    t_ack = t
    t += 10_000_000                # nghi nen 10 s
    pulses = []
    for cfg in ("mamba", "mlp") if order == "MF" else ("mlp", "mamba"):
        w = 2 * block_us[cfg]      # 20 luot on dinh ~ 2 khoi (CPU dang tinh)
        seg.append((t, t + w, i_cfg[cfg]))
        t += w + 2_000_000         # + nghi 2 s
        for _ in range(schedule.N_EMPTY):
            pulses.append((t, t + EMP_WIDTH_US, "EMP", cfg, None))
            t += EMP_WIDTH_US + 100_000
        t += 2_000_000 - 100_000   # nghi them 2 s sau xung rong cuoi (firmware Brief 07)
        for b in range(schedule.N_BLOCKS):
            pulses.append((t, t + block_us[cfg], "BLK", cfg, b))
            seg.append((t, t + block_us[cfg], i_cfg[cfg]))
            t += block_us[cfg] + (2_000_000 if b < schedule.N_BLOCKS - 1 else 0)
        t += 5_000_000             # nghi 5 s sau cau hinh
    t_done = t
    t_end = t + 3_000_000

    # dong dien theo thoi gian: hang so tung doan -> tich phan luy ke de lay trung binh chuyen doi
    bp = sorted({0, t_end} | {x for a, b, _ in seg for x in (a, b)})
    cum, acc = [0.0], 0.0
    for a, b in zip(bp, bp[1:]):
        cur = I_IDLE
        for s0, s1, ii in seg:
            if s0 <= a and b <= s1:
                cur = ii
        acc += cur * (b - a)
        cum.append(acc)

    def cur_at(a, b):
        def F(x):
            k = bisect.bisect_right(bp, x) - 1
            k = min(max(k, 0), len(bp) - 2)
            a0, a1 = bp[k], bp[k + 1]
            cur = (cum[k + 1] - cum[k]) / (a1 - a0)
            return cum[k] + cur * (x - a0)
        return (F(b) - F(a)) / (b - a)

    tt = 500_000
    while tt < t_end:
        ts = tt + rng.randint(-20, 20)
        cur = cur_at(ts - 1300, ts - 200) if conv == "window" else cur_at(ts - 20, ts)
        sh = int(round(cur * R_SHUNT / 2.5e-6)) + rng.randint(-2, 2)
        bus = int(round(V_BUS / 1.25e-3)) + rng.randint(-1, 1)
        s.samples.append((ts, sh, bus))
        tt += period_us

    for k, (r, f, kind, cfg, b) in enumerate(pulses):
        s.edges.append((r, 1))
        s.edges.append((f, 0))
        pulse = k + 1
        d = {"kind": kind, "s": session, "cfg": cfg, "pulse": pulse,
             "t_rise_us": r + DEVKIT_CLOCK_OFFSET_US + 3, "t_fall_us": f + DEVKIT_CLOCK_OFFSET_US - 2}
        if kind == "BLK":
            d["b"] = b
            d["idx"] = schedule.block_indices(perm, b)
            d["pred"] = [rng.randint(0, 5) for _ in range(10)]
            d["ref"] = list(d["pred"])
            d["maxdl"] = "1.%02de-07" % rng.randint(0, 99)
            d["invalid"] = 0
            dur = f - r
            e_raw = V_BUS * i_cfg[cfg] * dur * 1e-3          # W*us = uJ -> mJ
            s.truth.append({"pulse": pulse, "cfg": cfg, "kind": kind, "block": b,
                            "e_raw_mj": e_raw, "e_net_mj": (V_BUS * (i_cfg[cfg] - I_IDLE)) * dur * 1e-3})
        else:
            s.truth.append({"pulse": pulse, "cfg": cfg, "kind": kind, "block": None,
                            "e_raw_mj": None, "e_net_mj": None})
        s.dev.append(d)
    s.t_ack, s.t_done = t_ack, t_done
    s.t_end = t_end
    return s


def render_logger(s, with_stat=True):
    lines = ["# fw=synthetic cfg=0x4127 avg=1 vct_us=1100 rshunt_nominal_ohm=0.1 marker_gpio=1",
             "# host_time_utc=1970-01-01T00:00:00Z (du lieu tong hop)"]
    recs = [(t, 0, "S,%d,%d,%d" % (t, a, b)) for t, a, b in s.samples]
    recs += [(t, 1, "E,%d,%d" % (t, lv)) for t, lv in s.edges]
    recs += [(t, 2, "X,%d,%d" % (t, c)) for t, c in s.errors]
    if with_stat:
        t = 5_000_000
        while t < s.t_end:
            n = bisect.bisect_right([x[0] for x in s.samples], t)
            recs.append((t, 3, "STAT,%d,samples=%d,edges=%d,drops=0,i2c_err=%d"
                         % (t, n, sum(1 for e in s.edges if e[0] <= t), sum(1 for e in s.errors if e[0] <= t))))
            t += 5_000_000
    recs.sort(key=lambda r: (r[0], r[1]))
    lines += [r[2] for r in recs]
    lines += s.lines_extra
    return "\n".join(lines) + "\n"


def render_devkit(s):
    out = ["boot: dong rac truoc READY", "READY fw=synthetic gpio=4",
           "ACK session=%d order=%s seed=%d" % (s.session, s.order, s.seed)]
    for d in s.dev:
        if d["kind"] == "EMP":
            out.append("EMP s=%d cfg=%s pulse=%d t_rise_us=%d t_fall_us=%d"
                       % (d["s"], d["cfg"], d["pulse"], d["t_rise_us"], d["t_fall_us"]))
        else:
            out.append("BLK s=%d b=%d cfg=%s pulse=%d t_rise_us=%d t_fall_us=%d n=10 idx=%s pred=%s ref=%s "
                       "maxdl=%s invalid=%d"
                       % (d["s"], d["b"], d["cfg"], d["pulse"], d["t_rise_us"], d["t_fall_us"],
                          ",".join(map(str, d["idx"])), ",".join(map(str, d["pred"])),
                          ",".join(map(str, d["ref"])), d["maxdl"], d["invalid"]))
    out.append("SESSION_DONE session=%d" % s.session)
    out.append("READY fw=synthetic gpio=4")
    return "\n".join(out) + "\n"


def write_files(s, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    lp, dp = outdir / "synthetic_logger.csv", outdir / "synthetic_devkit.txt"
    lp.write_bytes(render_logger(s).encode("utf-8"))
    dp.write_bytes(render_devkit(s).encode("utf-8"))
    return lp, dp


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--order", choices=("MF", "LF"), default="MF")
    ap.add_argument("--session", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out-dir", type=Path, required=True)
    a = ap.parse_args(argv)
    lp, dp = write_files(build(a.order, a.session, a.seed), a.out_dir)
    print("ghi %s va %s (du lieu tong hop, khong phai so do)" % (lp, dp))
    return 0


if __name__ == "__main__":
    sys.exit(main())

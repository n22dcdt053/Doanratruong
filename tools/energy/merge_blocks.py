#!/usr/bin/env python3
"""Ghep du lieu logger (INA226 + canh marker, XIAO) voi log UART devkit thanh nang luong theo khoi (Brief 08, H3).

  py -3 -I tools/energy/merge_blocks.py --logger logger.csv --devkit devkit.txt --session 1 --rshunt 0.1 --outdir out

Vao : logger.csv  - tep do capture.py ghi (dong S/E/X/STAT, '#' la chu thich);
      devkit.txt  - log UART cua devkit (dong ACK/EMP/BLK/SESSION_DONE, Brief 07 muc 3).
Ra  : measurements_session<N>.csv, merge_report_session<N>.md. Ma thoat: 0 phien hop le, 1 phien khong hop le
      (van ghi tep ra), 2 loi dau vao.

Chi dung thu vien chuan. Gia tri INA226 la MA THO; quy doi o day:
  V_shunt = raw * 2.5 uV (so co dau 16 bit), V_bus = raw * 1.25 mV (khong dau), I = V_shunt / R_shunt.
R_shunt la THAM SO, mac dinh 0.1 ohm la gia tri DANH NGHIA, CHUA DO. Ket qua la so do chua hieu chinh.

Dong ho: thoi gian logger (t_us cua XIAO) va thoi gian devkit (t_rise_us/t_fall_us cua devkit) la hai dong ho
khac nhau. Hai nguon duoc ghep bang SO THU TU xung (xung thu k cua logger <-> pulse=k cua devkit), khong bang
gia tri thoi gian. Cot t_rise_us/t_fall_us trong CSV la thoi gian cua LOGGER.
"""
import argparse
import bisect
import hashlib
import math
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schedule  # noqa: E402

LSB_SHUNT_V = 2.5e-6
LSB_BUS_V = 1.25e-3
SAT_CODE = 32767            # |shunt_raw| >= 32767 coi la bao hoa
FEW_SAMPLES = 20            # khoi < 20 mau INA226 -> few_samples
GAP_FACTOR = 3.0            # khoang cach mau > 3 x chu ky trung vi -> i2c_gap
WIDTH_TOL = 0.20            # +-20% do rong xung so voi devkit
INTERVAL_TOL_ABS_US = 2000  # lech khoang cach giua hai xung lien tiep (logger vs devkit): 2 ms + 0.1%
INTERVAL_TOL_REL = 0.001
IDLE_MARGIN_US = 300_000    # bo 300 ms sau canh xuong / truoc canh len
MIN_GAP_US = 1_600_000      # khoang nghi giua hai xung chi dung lam nen khi >= 1.6 s (2 s - 2 x 0.3 s)
IDLE_MIN_SAMPLES = 100
REST_BEFORE_EMP_US = 2_000_000   # Brief 07 muc 3.a: nghi 2 s sau 20 luot on dinh, truoc xung rong dau
INIT_IDLE_US = 10_000_000        # Brief 07 muc 3.1: nghi nen 10 s sau ACK

COLUMNS = ["session", "block", "cfg", "kind", "pulse", "t_rise_us", "t_fall_us", "dur_ms", "n_samples",
           "V_mean", "I_mean_A", "P_mean_W", "I_max_A", "E_raw_mJ", "E_net_mJ", "E_per_inf_raw_mJ",
           "E_per_inf_net_mJ", "P_idle_W", "devkit_maxdl", "devkit_invalid", "valid", "flags"]


# --------------------------------------------------------------------------- doc dau vao

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_lines(path):
    # errors="replace": log UART co the lan byte rac luc boot; khong bao gio chet vi giai ma.
    with open(path, "r", encoding="utf-8", errors="replace", newline=None) as f:
        return f.read().split("\n")


def parse_logger(path):
    """Phan tich tep logger. Dong khong khop mau -> bad_lines (khong sua, khong bo qua im lang)."""
    d = {"header": [], "samples": [], "edges": [], "errors": [], "stats": [], "bad_lines": [], "other": []}
    for ln, raw in enumerate(read_lines(path), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            d["header"].append(line)
            continue
        f = line.split(",")
        try:
            if f[0] == "S" and len(f) == 4:
                d["samples"].append((int(f[1]), int(f[2]), int(f[3])))
            elif f[0] == "E" and len(f) == 3 and f[2] in ("0", "1"):
                d["edges"].append((int(f[1]), int(f[2])))
            elif f[0] == "X" and len(f) == 3:
                d["errors"].append((int(f[1]), int(f[2], 0)))
            elif f[0] == "STAT" and len(f) == 6:
                kv = dict(x.split("=", 1) for x in f[2:])
                d["stats"].append((int(f[1]), int(kv["samples"]), int(kv["edges"]), int(kv["drops"]),
                                   int(kv["i2c_err"])))
            elif f[0] == "PING" or line == "SELFTEST_DONE" or line.startswith("ERR "):
                d["other"].append((ln, line))
            else:
                d["bad_lines"].append((ln, line))
        except (ValueError, KeyError):
            d["bad_lines"].append((ln, line))
    return d


_KV = re.compile(r"(\w+)=(\S*)")


def parse_devkit(path, session):
    """Lay phien `session` tu log UART devkit: ACK cuoi cung cua phien do va cac dong EMP/BLK sau no."""
    lines = read_lines(path)
    ack_idx = None
    for i, raw in enumerate(lines):
        t = raw.strip()
        if t.startswith("ACK "):
            kv = dict(_KV.findall(t))
            if kv.get("session") == str(session):
                ack_idx = i
    d = {"ack": None, "pulses": [], "session_done": False, "problems": [], "ignored": 0, "ack_line": None}
    if ack_idx is None:
        d["problems"].append("khong co dong ACK cho session=%d trong log devkit" % session)
        return d
    kv = dict(_KV.findall(lines[ack_idx].strip()))
    try:
        d["ack"] = {"session": int(kv["session"]), "order": kv["order"], "seed": int(kv["seed"])}
    except (KeyError, ValueError):
        d["problems"].append("dong ACK sai dinh dang: %r" % lines[ack_idx].strip())
        return d
    d["ack_line"] = lines[ack_idx].strip()
    if d["ack"]["order"] not in ("MF", "LF"):
        d["problems"].append("ACK order=%r khong phai MF/LF" % d["ack"]["order"])
        return d
    for raw in lines[ack_idx + 1:]:
        t = raw.strip()
        if t.startswith("SESSION_DONE"):
            kv = dict(_KV.findall(t))
            if kv.get("session") == str(session):
                d["session_done"] = True
                break
            continue
        if t.startswith("ACK ") or t.startswith("READY"):
            # phien moi / reset: ket thuc doan cua phien nay
            d["problems"].append("gap %r truoc SESSION_DONE (log bi cat hoac devkit reset)" % t.split()[0])
            break
        if t.startswith("EMP ") or t.startswith("BLK "):
            kv = dict(_KV.findall(t))
            try:
                p = {"kind": t[:3], "s": int(kv["s"]), "cfg": kv["cfg"], "pulse": int(kv["pulse"]),
                     "t_rise_us": int(kv["t_rise_us"]), "t_fall_us": int(kv["t_fall_us"]), "raw": t}
                if p["kind"] == "BLK":
                    p["b"] = int(kv["b"])
                    p["n"] = int(kv["n"])
                    p["idx"] = [int(x) for x in kv["idx"].split(",")]
                    p["pred"] = kv["pred"].split(",")
                    p["ref"] = kv["ref"].split(",")
                    p["maxdl"] = kv["maxdl"]
                    p["invalid"] = int(kv["invalid"])
            except (KeyError, ValueError):
                d["problems"].append("dong %s sai dinh dang: %r" % (t[:3], t))
                continue
            d["pulses"].append(p)
        else:
            d["ignored"] += 1
    return d


# --------------------------------------------------------------------------- xung logger

def build_pulses(edges):
    """Ghep canh thanh xung (len roi xuong). Tra ve (pulses, anomalies); khong tu sua."""
    pulses, anomalies = [], []
    rise = None
    for t, lv in edges:
        if lv == 1:
            if rise is not None:
                anomalies.append("hai canh len lien tiep: t=%d va t=%d" % (rise, t))
            rise = t
        else:
            if rise is None:
                anomalies.append("canh xuong khong co canh len truoc: t=%d" % t)
            else:
                pulses.append((rise, t))
                rise = None
    if rise is not None:
        anomalies.append("canh len cuoi khong co canh xuong: t=%d" % rise)
    return pulses, anomalies


# --------------------------------------------------------------------------- tinh toan

def convert(samples, rshunt):
    """samples [(t, shunt, bus)] -> (ts, V, I, P) theo thu tu thoi gian."""
    ts = [s[0] for s in samples]
    v = [s[2] * LSB_BUS_V for s in samples]
    i = [s[1] * LSB_SHUNT_V / rshunt for s in samples]
    p = [a * b for a, b in zip(v, i)]
    return ts, v, i, p


def integrate_mj(ts, p, t_rise, t_fall):
    """Tich phan hinh thang theo thoi gian giua cac mau trong khoi + hai doan bien giu gia tri mau gan nhat.
    ts [us] tang dan, p [W]; ket qua mJ. ts rong -> None."""
    n = len(ts)
    if n == 0:
        return None
    e = p[0] * (ts[0] - t_rise) + p[-1] * (t_fall - ts[-1])   # W*us = uJ
    for k in range(n - 1):
        e += 0.5 * (p[k] + p[k + 1]) * (ts[k + 1] - ts[k])
    return e * 1e-3                                              # uJ -> mJ


def idle_windows(lpulses, plan, devrows):
    """Cac cua so nen (us, dong ho logger): (nhan, bat_dau, ket_thuc).
    - init : nghi nen 10 s dau phien. Thoi diem ACK khong co trong dong ho logger nen suy tu xung dau tien:
             [T1 - 2 s - W - 10 s + 2 s, T1 - 2 s - W - 1 s], W = thoi gian 20 luot on dinh ~ 2 x do dai khoi 0
             cua cau hinh dau (suy tu devkit). Doan 20 luot on dinh (CPU dang tinh) bi loai khoi cua so nen.
    - rest : 2 s nghi truoc xung rong dau cua moi cau hinh.
    - gap  : khoang nghi >= 1.6 s giua hai xung lien tiep cung cau hinh (nghi 2 s giua cac khoi, ...).
    Moi doan bo 300 ms moi dau (tru init theo cong thuc tren)."""
    wins = []
    first_cfg = plan[0]["cfg"]
    blk0 = next((r for r in devrows if r["kind"] == "BLK" and r["cfg"] == first_cfg and r["b"] == 0), None)
    if blk0 is not None:
        w = 2 * (blk0["t_fall_us"] - blk0["t_rise_us"])
        t1 = lpulses[0][0]
        idle_end = t1 - REST_BEFORE_EMP_US - w
        idle_start = idle_end - INIT_IDLE_US
        wins.append(("init", idle_start + 2_000_000, idle_end - 1_000_000))
    for k, p in enumerate(plan):
        if p["kind"] == "EMP" and (k == 0 or plan[k - 1]["cfg"] != p["cfg"]):
            rise = lpulses[k][0]
            wins.append(("rest", rise - REST_BEFORE_EMP_US + IDLE_MARGIN_US, rise - IDLE_MARGIN_US))
    for k in range(len(plan) - 1):
        if plan[k]["cfg"] != plan[k + 1]["cfg"]:
            continue
        gap = lpulses[k + 1][0] - lpulses[k][1]
        if gap >= MIN_GAP_US:
            wins.append(("gap", lpulses[k][1] + IDLE_MARGIN_US, lpulses[k + 1][0] - IDLE_MARGIN_US))
    return wins


def fmt(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    if isinstance(x, float):
        return "%.9g" % x
    return str(x)


# --------------------------------------------------------------------------- ghep

def merge(logger_path, devkit_path, session, rshunt, outdir):
    lg = parse_logger(logger_path)
    dk = parse_devkit(devkit_path, session)
    checks = []     # (muc, ket_qua: ok/loi/canh_bao, noi_dung)
    invalid = []    # ly do phien khong hop le

    def add(kind, text):
        checks.append((kind, text))
        if kind == "loi":
            invalid.append(text)

    # ---- header logger
    hdr = next((h for h in lg["header"] if h.startswith("# fw=")), None)
    if hdr is None:
        add("canh_bao", "logger khong co dong tieu de '# fw=... cfg=...' (khong biet cau hinh INA226)")
    else:
        add("ok", "tieu de logger: " + hdr)
        m = re.search(r"rshunt_nominal_ohm=(\S+)", hdr)
        if m and abs(float(m.group(1)) - rshunt) > 1e-12:
            add("canh_bao", "--rshunt=%g khac rshunt_nominal_ohm=%s trong tieu de logger (tham so tinh toan)"
                % (rshunt, m.group(1)))
    if lg["bad_lines"]:
        add("canh_bao", "%d dong logger khong khop mau (ghi nguyen, khong dung); dong dau: %r"
            % (len(lg["bad_lines"]), lg["bad_lines"][0]))

    # ---- devkit
    for p in dk["problems"]:
        add("loi", "devkit: " + p)
    order = dk["ack"]["order"] if dk["ack"] else None
    seed = dk["ack"]["seed"] if dk["ack"] else None
    plan = schedule.pulse_plan(order) if order else None
    devrows = dk["pulses"]
    if dk["ack"]:
        add("ok", "devkit ACK: " + dk["ack_line"])
        if len(devrows) == schedule.PULSES_PER_SESSION:
            add("ok", "devkit: %d dong EMP/BLK" % len(devrows))
        else:
            add("loi", "devkit: %d dong EMP/BLK, can %d" % (len(devrows), schedule.PULSES_PER_SESSION))
        if not dk["session_done"]:
            add("loi", "devkit: khong thay SESSION_DONE session=%d" % session)
        else:
            add("ok", "devkit: co SESSION_DONE session=%d" % session)
        if [r["pulse"] for r in devrows] == list(range(1, len(devrows) + 1)):
            add("ok", "devkit: pulse lien tuc tu 1")
        else:
            add("loi", "devkit: pulse khong lien tuc tu 1: %s" % [r["pulse"] for r in devrows])
        # cfg/kind/block theo pulse_plan
        bad = []
        perm = schedule.permutation(seed)
        for r in devrows:
            k = r["pulse"] - 1
            if not 0 <= k < len(plan):
                bad.append("pulse=%d ngoai 1..32" % r["pulse"])
                continue
            e = plan[k]
            blk = r.get("b") if r["kind"] == "BLK" else None
            if (r["kind"], r["cfg"], blk) != (e["kind"], e["cfg"], e["block"]):
                bad.append("pulse=%d devkit(%s,%s,%s) != ke hoach(%s,%s,%s)"
                           % (r["pulse"], r["kind"], r["cfg"], blk, e["kind"], e["cfg"], e["block"]))
            if r["s"] != session:
                bad.append("pulse=%d co s=%d != session %d" % (r["pulse"], r["s"], session))
            if r["kind"] == "BLK":
                if r["n"] != schedule.BLOCK_INF or len(r["idx"]) != r["n"] or len(r["pred"]) != r["n"] \
                        or len(r["ref"]) != r["n"]:
                    bad.append("pulse=%d: n/idx/pred/ref khong du %d phan tu" % (r["pulse"], schedule.BLOCK_INF))
                elif r["idx"] != schedule.block_indices(perm, r["b"]):
                    bad.append("pulse=%d: idx khong khop hoan vi seed=%d (khoi %d)" % (r["pulse"], seed, r["b"]))
        if bad:
            for b in bad:
                add("loi", "devkit/ke hoach: " + b)
        else:
            add("ok", "devkit: cfg/kind/block + idx khop pulse_plan(%s) va hoan vi seed=%d (schedule.py)"
                % (order, seed))

    # ---- canh marker logger
    edges = list(lg["edges"])
    if edges != sorted(edges, key=lambda e: e[0]):
        add("canh_bao", "canh E khong sap theo thoi gian trong tep; da sap xep on dinh theo t_us (khong doi so)")
        edges = sorted(edges, key=lambda e: e[0])
    lpulses, anomalies = build_pulses(edges)
    for a in anomalies:
        add("loi", "logger: " + a)
    if len(lpulses) == schedule.PULSES_PER_SESSION:
        add("ok", "logger: %d xung (len+xuong)" % len(lpulses))
    else:
        add("loi", "logger: %d xung, can %d (thua/thieu -> phien khong hop le, khong tu sua)"
            % (len(lpulses), schedule.PULSES_PER_SESSION))

    paired = (plan is not None and len(lpulses) == schedule.PULSES_PER_SESSION and not anomalies
              and len(devrows) == schedule.PULSES_PER_SESSION)

    # ---- mau INA226
    samples = sorted(lg["samples"], key=lambda s: s[0])
    if samples != lg["samples"]:
        add("canh_bao", "mau S khong sap theo thoi gian; da sap xep on dinh theo t_us")
    ts, vs, is_, ps = convert(samples, rshunt)
    if len(ts) >= 2:
        med = statistics.median(b - a for a, b in zip(ts, ts[1:]))
        add("ok", "%d mau S, chu ky trung vi %.0f us" % (len(ts), med))
    else:
        med = None
        add("loi", "logger co %d mau S (can >= 2)" % len(ts))
    errs_t = sorted(e[0] for e in lg["errors"])
    # STAT la bo dem TICH LUY tu luc logger khoi dong; drops truoc khi capture mo cong la binh thuong
    # (USB chua co ben doc), nen chi tinh phan TANG giua dong STAT dau va cuoi trong tep.
    logger_drops = False
    if len(lg["stats"]) >= 2:
        first, last = lg["stats"][0], lg["stats"][-1]
        dd, de = last[3] - first[3], last[4] - first[4]
        logger_drops = dd > 0
        add("canh_bao" if dd > 0 or de > 0 else "ok",
            "STAT dau->cuoi: samples %d->%d, edges %d->%d, drops tang %d, i2c_err tang %d"
            % (first[1], last[1], first[2], last[2], dd, de))
    elif lg["stats"]:
        add("canh_bao", "chi co 1 dong STAT (drops=%d tich luy): khong tinh duoc drops tang trong luc capture"
            % lg["stats"][0][3])
    else:
        add("canh_bao", "logger khong co dong STAT")

    # ---- nen
    wins = idle_windows(lpulses, plan, devrows) if paired else []
    idle_p, idle_by_win = [], []
    for label, a, b in wins:
        lo, hi = bisect.bisect_left(ts, a), bisect.bisect_right(ts, b)
        covered = lo < len(ts) and ts and ts[0] <= a
        pw = ps[lo:hi]
        idle_by_win.append((label, a, b, len(pw), statistics.fmean(pw) if pw else None, bool(covered)))
        idle_p.extend(pw)
    p_idle = statistics.fmean(idle_p) if len(idle_p) >= IDLE_MIN_SAMPLES else None
    p_idle_sd = statistics.stdev(idle_p) if len(idle_p) >= 2 else None
    if paired:
        if p_idle is None:
            add("canh_bao", "chi co %d mau nen (< %d): khong tinh P_idle/E_net" % (len(idle_p), IDLE_MIN_SAMPLES))
        else:
            add("ok", "P_idle = %.6g W (%d mau, do lech chuan %.3g W)" % (p_idle, len(idle_p), p_idle_sd))
        if not any(w[0] == "init" and w[5] and w[3] > 0 for w in idle_by_win):
            add("canh_bao", "khong co mau trong cua so nen dau phien (capture bat dau muon?)")

    # ---- tung xung
    rows = []
    emp_info = []
    for k, d in enumerate(devrows if plan else []):
        e = plan[d["pulse"] - 1] if 0 <= d["pulse"] - 1 < len(plan) else None
        row = {c: "" for c in COLUMNS}
        row.update({"session": session, "cfg": d["cfg"], "kind": d["kind"], "pulse": d["pulse"],
                    "block": d.get("b", "") if d["kind"] == "BLK" else "-"})
        flags = []
        if d["kind"] == "BLK":
            row["devkit_maxdl"] = d["maxdl"]
            row["devkit_invalid"] = d["invalid"]
        valid = 1
        if invalid:
            flags.append("session_invalid")
            valid = 0
        if paired and e is not None and 0 <= k < len(lpulses):
            rise, fall = lpulses[k]
            row["t_rise_us"], row["t_fall_us"] = rise, fall
            row["dur_ms"] = (fall - rise) / 1000.0
            dev_w = d["t_fall_us"] - d["t_rise_us"]
            if dev_w <= 0 or abs((fall - rise) - dev_w) > WIDTH_TOL * dev_w:
                flags.append("width_mismatch")
            if k > 0:
                dl = rise - lpulses[k - 1][0]
                dd = d["t_rise_us"] - devrows[k - 1]["t_rise_us"]
                if abs(dl - dd) > INTERVAL_TOL_ABS_US + INTERVAL_TOL_REL * abs(dd):
                    flags.append("interval_mismatch")
            lo, hi = bisect.bisect_left(ts, rise), bisect.bisect_right(ts, fall)
            n = hi - lo
            row["n_samples"] = n
            if d["kind"] == "BLK" and n < FEW_SAMPLES:
                flags.append("few_samples")
            if n == 0:
                flags.append("no_samples")
                valid = 0
            else:
                seg_t, seg_p = ts[lo:hi], ps[lo:hi]
                e_raw = integrate_mj(seg_t, seg_p, rise, fall)
                row["V_mean"] = statistics.fmean(vs[lo:hi])
                row["I_mean_A"] = statistics.fmean(is_[lo:hi])
                row["I_max_A"] = max(is_[lo:hi])
                row["E_raw_mJ"] = e_raw
                row["P_mean_W"] = e_raw * 1e-3 / ((fall - rise) * 1e-6)
                if p_idle is not None:
                    row["P_idle_W"] = p_idle
                    row["E_net_mJ"] = e_raw - p_idle * (fall - rise) * 1e-3
                else:
                    flags.append("no_idle")
                if d["kind"] == "BLK":
                    row["E_per_inf_raw_mJ"] = e_raw / schedule.BLOCK_INF
                    if row["E_net_mJ"] != "":
                        row["E_per_inf_net_mJ"] = row["E_net_mJ"] / schedule.BLOCK_INF
                if any(abs(s[1]) >= SAT_CODE for s in samples[lo:hi]):
                    flags.append("saturated")
                    valid = 0
            # khoang trong lien tiep cua mau trong/chong len khoi
            if med is not None:
                a, b = max(lo - 1, 0), min(hi, len(ts) - 1)
                gap = any(ts[q + 1] - ts[q] > GAP_FACTOR * med for q in range(a, b))
                xerr = any(rise <= t <= fall for t in errs_t)
                if gap or xerr:
                    flags.append("i2c_gap")
                    valid = 0
            if logger_drops:
                flags.append("logger_drops")
            if d["kind"] == "EMP":
                emp_info.append((d["pulse"], d["cfg"], (fall - rise) / 1000.0, n, row["E_raw_mJ"], row["E_net_mJ"]))
        else:
            valid = 0
            if "session_invalid" not in flags:
                flags.append("unpaired")
        row["valid"] = valid
        row["flags"] = ";".join(flags)
        rows.append(row)

    res = {"valid": not invalid, "rows": rows, "checks": checks, "invalid": invalid, "order": order,
           "seed": seed, "p_idle": p_idle, "p_idle_sd": p_idle_sd, "n_idle": len(idle_p),
           "idle_by_win": idle_by_win, "emp": emp_info, "lpulses": lpulses, "n_samples": len(ts),
           "header": lg["header"], "bad_lines": lg["bad_lines"], "median_period_us": med}
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    write_csv(outdir / ("measurements_session%d.csv" % session), res, session, rshunt, hdr)
    write_report(outdir / ("merge_report_session%d.md" % session), res, session, rshunt,
                 logger_path, devkit_path)
    return res


def write_csv(path, res, session, rshunt, hdr):
    lines = [
        "# measurements_session%d.csv - nang luong theo xung/khoi, CHUA HIEU CHINH, khong ket luan gi ve do chinh xac"
        % session,
        "# R_shunt = %g ohm (DANH NGHIA, CHUA DO) - doi R thi I, P, E doi theo ti le" % rshunt,
        "# don vi: t_*_us [us, dong ho LOGGER]; dur_ms [ms]; V_mean [V]; I_*_A [A]; P_*_W [W]; E_*_mJ [mJ]",
        "# E_raw = tich phan hinh thang P(t) tu canh len den canh xuong (hai doan bien giu mau gan nhat);"
        " E_net = E_raw - P_idle*thoi_luong; E_per_inf = /10",
        "# valid=1: hang co phep do dung duoc (phien hop le, co mau, khong bao hoa, khong khoang trong I2C)",
        "# order=%s seed=%s" % (res["order"], res["seed"]),
    ]
    if hdr:
        lines.append("# logger: " + hdr.lstrip("# "))
    lines.append(",".join(COLUMNS))
    for r in res["rows"]:
        lines.append(",".join(fmt(r[c]) for c in COLUMNS))
    Path(path).write_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def write_report(path, res, session, rshunt, logger_path, devkit_path):
    L = []
    L.append("# Bao cao ghep - phien %d" % session)
    L.append("")
    L.append("**Trang thai phien: %s.** Day la so do CHUA HIEU CHINH; khong co danh gia do chinh xac."
             % ("HOP LE (qua cac kiem tra duoi day)" if res["valid"] else "KHONG HOP LE"))
    L.append("")
    L.append("- logger: `%s` (sha256 `%s`)" % (logger_path, sha256_file(logger_path)))
    L.append("- devkit: `%s` (sha256 `%s`)" % (devkit_path, sha256_file(devkit_path)))
    L.append("- R_shunt dung de tinh: **%g ohm, danh nghia, chua do**" % rshunt)
    L.append("- order=%s seed=%s" % (res["order"], res["seed"]))
    L.append("")
    L.append("## Kiem tra")
    L.append("")
    tag = {"ok": "[ok]", "loi": "[LOI]", "canh_bao": "[canh bao]"}
    for kind, text in res["checks"]:
        L.append("- %s %s" % (tag[kind], text))
    L.append("")
    if res["invalid"]:
        L.append("## Ly do phien khong hop le")
        L.append("")
        for t in res["invalid"]:
            L.append("- " + t)
        L.append("")
    L.append("## Cua so nen")
    L.append("")
    if res["idle_by_win"]:
        L.append("| loai | bat dau us | ket thuc us | so mau | P_mean W | co mau tu bat dau |")
        L.append("|---|---|---|---|---|---|")
        for label, a, b, n, m, cov in res["idle_by_win"]:
            L.append("| %s | %d | %d | %d | %s | %s |" % (label, a, b, n, fmt(m), "co" if cov else "khong"))
        L.append("")
        L.append("P_idle_mean = %s W, do lech chuan = %s W, %d mau." % (
            fmt(res["p_idle"]), fmt(res["p_idle_sd"]), res["n_idle"]))
    else:
        L.append("Khong dung duoc cua so nen (phien khong ghep duoc).")
    L.append("")
    L.append("## Xung rong (EMP)")
    L.append("")
    if res["emp"]:
        L.append("Xung rong ~1 ms voi chu ky INA226 ~2.2 ms: nhieu xung co 0-1 mau. Day chi la so do, khong tru vao dau ca.")
        L.append("")
        L.append("| pulse | cfg | do rong ms | so mau | E_raw mJ | E_net mJ |")
        L.append("|---|---|---|---|---|---|")
        for p, c, w, n, er, en in res["emp"]:
            L.append("| %d | %s | %.3f | %d | %s | %s |" % (p, c, w, n, fmt(er), fmt(en)))
    else:
        L.append("(khong co)")
    L.append("")
    L.append("## Gia dinh va cach tinh")
    L.append("")
    L.append("- Hai dong ho khac nhau (XIAO va devkit): ghep bang so thu tu xung, khong bang thoi gian. "
             "Do rong xung logger so voi devkit (+-20%%) va khoang cach hai xung lien tiep (2 ms + 0.1%%) la kiem tra lech timer/GPIO.")
    L.append("- Phien duoc coi la toan bo doan capture: capture phai bat dau truoc lenh START va dung sau SESSION_DONE; "
             "xung thua ben ngoai phien se bi bao la thua.")
    L.append("- Thoi diem mau = ngay sau khi doc xong thanh ghi bus; chua bu tre chuyen doi (<= ~1 chu ky + thoi gian doc I2C).")
    L.append("- E: tich phan hinh thang P(t) giua cac mau trong [canh len, canh xuong]; hai doan bien giu gia tri mau gan nhat; "
             "P_mean = E_raw / thoi luong; V_mean, I_mean la trung binh mau.")
    L.append("- Cua so nen: (init) 10 s nghi dau phien suy tu xung dau tien va do dai khoi 0 (20 luot on dinh ~ 2 x khoi 0 "
             "bi loai vi CPU dang tinh), bo 2 s dau va 1 s cuoi; (rest) 2 s truoc xung rong dau moi cau hinh; "
             "(gap) khoang nghi >= 1.6 s giua hai xung cung cau hinh. Moi doan bo 300 ms hai dau. "
             "Brief 08 viet cua so dau la 'ACK+2 s den xung dau - 1 s'; cua so do chua 20 luot on dinh (CPU dang tinh) "
             "nen khong dung lam nen.")
    L.append("- few_samples: khoi < 20 mau; saturated: |shunt_raw| >= 32767; i2c_gap: dong X trong khoi hoac "
             "khoang cach hai mau lien tiep > 3 x chu ky trung vi.")
    L.append("- Cac nguong tren la quy uoc cua code ghep, khong phai nguong cua phep do.")
    L.append("")
    Path(path).write_bytes(("\n".join(L) + "\n").encode("utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logger", required=True, type=Path)
    ap.add_argument("--devkit", required=True, type=Path)
    ap.add_argument("--session", required=True, type=int, choices=range(1, 6))
    ap.add_argument("--rshunt", type=float, default=0.1, help="ohm, danh nghia chua do (mac dinh 0.1)")
    ap.add_argument("--outdir", type=Path, default=Path("."))
    a = ap.parse_args(argv)
    for p in (a.logger, a.devkit):
        if not p.is_file():
            print("khong thay tep: %s" % p, file=sys.stderr)
            return 2
    if a.rshunt <= 0:
        print("--rshunt phai > 0", file=sys.stderr)
        return 2
    res = merge(a.logger, a.devkit, a.session, a.rshunt, a.outdir)
    print("phien %d: %s; %d hang; %d mau S; %d xung logger"
          % (a.session, "hop le" if res["valid"] else "KHONG HOP LE", len(res["rows"]), res["n_samples"],
             len(res["lpulses"])))
    for t in res["invalid"]:
        print("  loi: " + t)
    print("ghi %s va %s" % (a.outdir / ("measurements_session%d.csv" % a.session),
                            a.outdir / ("merge_report_session%d.md" % a.session)))
    return 0 if res["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())

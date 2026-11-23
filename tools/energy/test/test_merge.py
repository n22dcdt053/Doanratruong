#!/usr/bin/env python3
"""Kiem thu merge_blocks.py bang du lieu TONG HOP (make_synthetic.py). Khong can bo.

Nguong 1% la nguong KIEM THU CODE (E_raw/E_net khoi phuc duoc gia tri da dung), khong phai nguong cua phep do.
Chay: py -3 -I tools/energy/test/test_merge.py
"""
import copy
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import make_synthetic as ms  # noqa: E402
import merge_blocks as mb    # noqa: E402

TOL = 0.01
_passed = []


def read_csv(path):
    lines = [l for l in Path(path).read_text(encoding="utf-8").split("\n") if l and not l.startswith("#")]
    cols = lines[0].split(",")
    assert cols == mb.COLUMNS, cols
    return [dict(zip(cols, l.split(","))) for l in lines[1:]]


def run(sess, name):
    """Ghi tep tong hop, chay merge, tra ve (ket qua, cac hang CSV, thu muc)."""
    d = Path(tempfile.mkdtemp(prefix="energy_test_%s_" % name))
    lp, dp = ms.write_files(sess, d)
    res = mb.merge(lp, dp, sess.session, 0.1, d / "out")
    rows = read_csv(d / "out" / ("measurements_session%d.csv" % sess.session))
    assert (d / "out" / ("merge_report_session%d.md" % sess.session)).is_file()
    return res, rows, d


def ok(name):
    _passed.append(name)
    print("PASS " + name)


def flags(row):
    return set(filter(None, row["flags"].split(";")))


def test_clean(order, session):
    name = "sach_%s_s%d" % (order, session)
    sess = ms.build(order=order, session=session, seed=42 + session, rng_seed=session)
    res, rows, _ = run(sess, name)
    assert res["valid"], res["invalid"]
    assert len(rows) == 32 and [int(r["pulse"]) for r in rows] == list(range(1, 33))
    plan = ms.schedule.pulse_plan(order)
    for r, p in zip(rows, plan):
        assert r["cfg"] == p["cfg"] and r["kind"] == p["kind"], r
    assert abs(res["p_idle"] - ms.V_BUS * ms.I_IDLE) / (ms.V_BUS * ms.I_IDLE) < 1e-3, res["p_idle"]
    nblk = 0
    for r, t in zip(rows, sess.truth):
        if r["kind"] != "BLK":
            continue
        nblk += 1
        assert r["valid"] == "1", r
        assert not (flags(r) - {"few_samples"}), r["flags"]
        er, en = float(r["E_raw_mJ"]), float(r["E_net_mJ"])
        assert abs(er - t["e_raw_mj"]) / t["e_raw_mj"] <= TOL, (r["pulse"], er, t["e_raw_mj"])
        assert abs(en - t["e_net_mj"]) / t["e_net_mj"] <= TOL, (r["pulse"], en, t["e_net_mj"])
        assert abs(float(r["E_per_inf_raw_mJ"]) * 10 - er) < 1e-6 * er
        assert abs(float(r["E_per_inf_net_mJ"]) * 10 - en) < 1e-6 * abs(en)
        assert r["devkit_invalid"] == "0" and r["devkit_maxdl"].endswith("e-07")
    assert nblk == 12
    for r in rows:
        if r["kind"] == "EMP":
            assert r["P_idle_W"] != "" or r["n_samples"] == "0"
            assert r["devkit_maxdl"] == ""
    ok(name)
    return sess, res, rows


def test_conversion_lag_model():
    """Mo phong tre/lam tron chuyen doi INA226 (mau = trung binh 1,1 ms ket thuc 0,2 ms truoc t).
    Day la tinh chat cua phep do chu khong phai loi code: chi kiem E_raw trong 1%, in sai so E_net de tham khao."""
    sess = ms.build(order="MF", conv="window", rng_seed=5)
    res, rows, _ = run(sess, "tre_chuyen_doi")
    assert res["valid"], res["invalid"]
    worst_net = 0.0
    for r, t in zip(rows, sess.truth):
        if r["kind"] != "BLK":
            continue
        er, en = float(r["E_raw_mJ"]), float(r["E_net_mJ"])
        assert abs(er - t["e_raw_mj"]) / t["e_raw_mj"] <= TOL, (r["pulse"], er, t["e_raw_mj"])
        worst_net = max(worst_net, abs(en - t["e_net_mj"]) / t["e_net_mj"])
    print("INFO tre_chuyen_doi: sai so E_net lon nhat %.2f%% (khoi MLP 107 ms; tinh chat cua mo hinh tre, khong co nguong)"
          % (100 * worst_net))
    ok("mo_hinh_tre_chuyen_doi_E_raw")


def test_clean_independent_of_devkit_clock():
    sess = ms.build(order="MF")
    sess_b = copy.deepcopy(sess)
    for d in sess_b.dev:
        d["t_rise_us"] += 123_456_789
        d["t_fall_us"] += 123_456_789
    res_a, rows_a, _ = run(sess, "clk_a")
    res_b, rows_b, _ = run(sess_b, "clk_b")
    assert res_a["valid"] and res_b["valid"]
    assert [r["E_raw_mJ"] for r in rows_a] == [r["E_raw_mJ"] for r in rows_b]
    ok("ghep_khong_phu_thuoc_offset_dong_ho_devkit")


def test_missing_pulse(base):
    s = copy.deepcopy(base)
    drop = [e for e in s.edges if e[0] in {s.dev[4]["t_rise_us"] - ms.DEVKIT_CLOCK_OFFSET_US - 3,
                                           s.dev[4]["t_fall_us"] - ms.DEVKIT_CLOCK_OFFSET_US + 2}]
    assert len(drop) == 2
    s.edges = [e for e in s.edges if e not in drop]
    res, rows, _ = run(s, "thieu_xung")
    assert not res["valid"]
    assert any("31 xung" in t for t in res["invalid"]), res["invalid"]
    assert all(r["valid"] == "0" for r in rows) and all("session_invalid" in flags(r) for r in rows)
    ok("thieu_mot_xung_phien_khong_hop_le")


def test_extra_pulse(base):
    s = copy.deepcopy(base)
    s.edges += [(6_000_000, 1), (6_001_000, 0)]    # xung thua trong luc nghi nen
    s.edges.sort()
    res, rows, _ = run(s, "thua_xung")
    assert not res["valid"]
    assert any("33 xung" in t for t in res["invalid"]), res["invalid"]
    assert all(r["valid"] == "0" for r in rows)
    ok("thua_mot_xung_phien_khong_hop_le")


def test_edge_anomaly(base):
    s = copy.deepcopy(base)
    k = s.edges.index(next(e for e in s.edges if e[1] == 0))    # bo canh xuong dau tien
    del s.edges[k]
    res, rows, _ = run(s, "canh_le")
    assert not res["valid"] and any("canh len" in t for t in res["invalid"]), res["invalid"]
    ok("thieu_mot_canh_phien_khong_hop_le")


def pulse_window(s, pulse):
    d = s.dev[pulse - 1]
    off = ms.DEVKIT_CLOCK_OFFSET_US
    return d["t_rise_us"] - off - 3, d["t_fall_us"] - off + 2


def test_sample_loss(base):
    s = copy.deepcopy(base)
    r, f = pulse_window(s, 13)        # khoi mamba 1,2 s
    mid = (r + f) // 2
    before = len(s.samples)
    s.samples = [x for x in s.samples if not (mid - 60_000 <= x[0] <= mid + 60_000)]
    assert before - len(s.samples) > 40
    res, rows, _ = run(s, "mat_mau")
    assert res["valid"]               # phien hop le; chi khoi nay bi danh dau
    bad = rows[12]
    assert "i2c_gap" in flags(bad) and bad["valid"] == "0", bad
    others = [x for i, x in enumerate(rows) if i != 12 and x["kind"] == "BLK"]
    assert all(x["valid"] == "1" and "i2c_gap" not in flags(x) for x in others)
    ok("mat_mau_giua_khoi_i2c_gap")


def test_i2c_error_line(base):
    s = copy.deepcopy(base)
    r, f = pulse_window(s, 14)
    s.errors.append(((r + f) // 2, 263))
    res, rows, _ = run(s, "dong_X")
    assert "i2c_gap" in flags(rows[13]) and rows[13]["valid"] == "0"
    assert "i2c_gap" not in flags(rows[12]) and rows[12]["valid"] == "1"
    ok("dong_X_trong_khoi_i2c_gap")


def test_saturated(base):
    s = copy.deepcopy(base)
    r, f = pulse_window(s, 28)        # khoi MLP (MF: mamba 1-16, mlp 17-32; khoi MLP = pulse 27-32)
    s.samples = [(t, 32767 if r <= t <= f else a, b) for t, a, b in s.samples]
    res, rows, _ = run(s, "bao_hoa")
    assert "saturated" in flags(rows[27]) and rows[27]["valid"] == "0", rows[27]
    assert all("saturated" not in flags(x) for i, x in enumerate(rows) if i != 27)
    ok("shunt_bao_hoa")


def test_few_samples():
    s = ms.build(order="MF", period_us=8000)          # khoi MLP 107 ms -> 13 mau
    res, rows, _ = run(s, "it_mau")
    mlp = [r for r in rows if r["kind"] == "BLK" and r["cfg"] == "mlp"]
    assert mlp and all("few_samples" in flags(r) for r in mlp), [r["flags"] for r in mlp]
    assert all(int(r["n_samples"]) < 20 for r in mlp)
    mamba = [r for r in rows if r["kind"] == "BLK" and r["cfg"] == "mamba"]
    assert all("few_samples" not in flags(r) for r in mamba)
    ok("it_mau_few_samples")


def test_width_mismatch(base):
    s = copy.deepcopy(base)
    d = s.dev[27]                      # pulse 28: khoi MLP 107 ms
    d["t_fall_us"] += int(0.30 * (d["t_fall_us"] - d["t_rise_us"]))
    res, rows, _ = run(s, "lech_rong")
    assert "width_mismatch" in flags(rows[27]), rows[27]["flags"]
    assert rows[27]["valid"] == "1"                     # canh bao, khong vo hieu
    assert all("width_mismatch" not in flags(x) for i, x in enumerate(rows) if i != 27)
    ok("do_rong_xung_lech_hon_20pct_canh_bao")


def test_devkit_inconsistent(base):
    s = copy.deepcopy(base)
    s.dev[11]["cfg"] = "mlp"            # sai cfg so voi ke hoach MF
    res, rows, _ = run(s, "sai_cfg")
    assert not res["valid"] and any("ke hoach" in t for t in res["invalid"]), res["invalid"]
    s = copy.deepcopy(base)
    s.dev[12]["idx"] = list(reversed(s.dev[12]["idx"]))
    res, rows, _ = run(s, "sai_idx")
    assert not res["valid"] and any("hoan vi" in t for t in res["invalid"]), res["invalid"]
    s = copy.deepcopy(base)
    del s.dev[7]                        # thieu dong devkit
    res, rows, _ = run(s, "thieu_dong")
    assert not res["valid"]
    ok("devkit_khong_khop_ke_hoach_phien_khong_hop_le")


def test_missing_ack_and_done(base):
    s = copy.deepcopy(base)
    d = Path(tempfile.mkdtemp(prefix="energy_test_ack_"))
    lp, dp = ms.write_files(s, d)
    res = mb.merge(lp, dp, 2, 0.1, d / "out")            # devkit chi co session 1
    assert not res["valid"] and any("ACK" in t for t in res["invalid"]), res["invalid"]
    txt = dp.read_text().replace("SESSION_DONE session=1\n", "")
    dp.write_text(txt)
    res = mb.merge(lp, dp, 1, 0.1, d / "out1")
    assert not res["valid"] and any("SESSION_DONE" in t for t in res["invalid"]), res["invalid"]
    ok("thieu_ACK_hoac_SESSION_DONE")


def test_junk_lines(base):
    s = copy.deepcopy(base)
    s.lines_extra = ["ESP-ROM:esp32s3-20210327", "S,1,2", "E,5,7"]
    res, rows, _ = run(s, "dong_rac")
    assert res["valid"] and len(res["bad_lines"]) == 3
    ok("dong_rac_logger_dem_bad_lines_khong_pha_phien")


def test_drops_delta(base):
    d = Path(tempfile.mkdtemp(prefix="energy_test_drops_"))
    lp, dp = ms.write_files(base, d)
    lines = lp.read_text().split("\n")
    stat_idx = [i for i, l in enumerate(lines) if l.startswith("STAT,")]
    # drops tich luy truoc capture (hang so 7) -> khong co flag
    for i in stat_idx:
        lines[i] = lines[i].replace("drops=0", "drops=7")
    lp.write_text("\n".join(lines))
    res = mb.merge(lp, dp, 1, 0.1, d / "o1")
    rows = read_csv(d / "o1" / "measurements_session1.csv")
    assert res["valid"] and all("logger_drops" not in flags(r) for r in rows)
    # drops tang trong luc capture -> flag logger_drops (canh bao, khong vo hieu hoa hang)
    lines[stat_idx[-1]] = lines[stat_idx[-1]].replace("drops=7", "drops=9")
    lp.write_text("\n".join(lines))
    res = mb.merge(lp, dp, 1, 0.1, d / "o2")
    rows = read_csv(d / "o2" / "measurements_session1.csv")
    assert all("logger_drops" in flags(r) for r in rows if r["kind"] == "BLK")
    assert any(r["valid"] == "1" for r in rows)
    ok("drops_tich_luy_chi_tinh_phan_tang")


def test_cli_exit_codes(base):
    d = Path(tempfile.mkdtemp(prefix="energy_test_cli_"))
    lp, dp = ms.write_files(base, d)
    rc = mb.main(["--logger", str(lp), "--devkit", str(dp), "--session", "1", "--rshunt", "0.1",
                  "--outdir", str(d / "o")])
    assert rc == 0
    rc = mb.main(["--logger", str(lp), "--devkit", str(dp), "--session", "2", "--outdir", str(d / "o2")])
    assert rc == 1
    rc = mb.main(["--logger", str(d / "khong_co.csv"), "--devkit", str(dp), "--session", "1"])
    assert rc == 2
    ok("ma_thoat_0_1_2")


def main():
    base, _, _ = test_clean("MF", 1)
    test_clean("LF", 2)
    test_clean_independent_of_devkit_clock()
    test_conversion_lag_model()
    test_missing_pulse(base)
    test_extra_pulse(base)
    test_edge_anomaly(base)
    test_sample_loss(base)
    test_i2c_error_line(base)
    test_saturated(base)
    test_few_samples()
    test_width_mismatch(base)
    test_devkit_inconsistent(base)
    test_missing_ack_and_done(base)
    test_junk_lines(base)
    test_drops_delta(base)
    test_cli_exit_codes(base)
    print("test_merge: %d ca PASS" % len(_passed))
    return 0


if __name__ == "__main__":
    sys.exit(main())

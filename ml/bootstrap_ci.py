#!/usr/bin/env python3
"""Bootstrap CI 95% theo cum nguoi: Mamba (huan luyen lai) va MLP tren tap test.

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\bootstrap_ci.py
    .venv-ml\\Scripts\\python ml\\bootstrap_ci.py --out-dir <thu muc tam>

Chi doc (khong doc data/UCI HAR Dataset/, khong nap checkpoint, khong chay lai mo hinh):
    ml/results/predictions_test.csv
    ml/results/mamba_retrained/predictions_test.csv
    ml/results/test_metrics.json
    ml/results/mamba_retrained/test_metrics.json

Tham so bootstrap co dinh (khong chinh sau khi xem ket qua):
    seed 42, B = 2000, moi lan rut 9 ma nguoi CO HOAN LAI (numpy default_rng),
    toan bo 2000 hang lay mot lan bang rng.integers(0, 9, size=(2000, 9)).
    Chi so: accuracy va macro-F1 (6 lop, F1 = 2TP/(2TP+FP+FN), mau so 0 -> F1 = 0
    va dem so lan gap). Khoang 95%: percentile 2,5 / 97,5, method="linear".

Ghi vao --out-dir (mac dinh ml/results/bootstrap/):
    bootstrap_results.json, bootstrap_draws.csv, per_subject_metrics.csv,
    loso_delta.csv, bootstrap_summary.md
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parents[1]
MLP_CSV = ROOT / "ml" / "results" / "predictions_test.csv"
MAMBA_CSV = ROOT / "ml" / "results" / "mamba_retrained" / "predictions_test.csv"
MLP_METRICS = ROOT / "ml" / "results" / "test_metrics.json"
MAMBA_METRICS = ROOT / "ml" / "results" / "mamba_retrained" / "test_metrics.json"
DEFAULT_OUT = ROOT / "ml" / "results" / "bootstrap"

N_CLASSES = 6
SEED = 42
B_DRAWS = 2000
EXPECTED_ROWS = 2947
SUBJECT_WINDOWS = {2: 302, 4: 317, 9: 288, 10: 294, 12: 320,
                   13: 327, 18: 364, 20: 354, 24: 381}
CHECK_TOL = 1e-12
MC_SEEDS = (43, 44)

HEADER = ["sample_id", "subject_id", "label", "pred"] + [f"logit{c}" for c in range(N_CLASSES)]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_predictions(path: Path) -> dict:
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            raise SystemExit(f"{path}: file rong")
        rows = list(reader)
    if header != HEADER:
        raise SystemExit(f"{path}: header {header} khac {HEADER}")
    if len(rows) != EXPECTED_ROWS:
        raise SystemExit(f"{path}: {len(rows)} dong, mong doi {EXPECTED_ROWS}")
    sample_id = [r[0] for r in rows]
    subject = np.array([int(r[1]) for r in rows], dtype=np.int64)
    label = np.array([int(r[2]) for r in rows], dtype=np.int64)
    pred = np.array([int(r[3]) for r in rows], dtype=np.int64)
    return {"path": path, "sample_id": sample_id, "subject": subject,
            "label": label, "pred": pred}


def confusion(labels: np.ndarray, preds: np.ndarray) -> np.ndarray:
    cm = np.zeros((N_CLASSES, N_CLASSES), dtype=np.int64)
    for t, p in zip(labels, preds):
        cm[t, p] += 1
    return cm


def metrics_from_cm(cm: np.ndarray) -> tuple[float, float, int]:
    """Tra ve (accuracy, macro_f1, so lop co mau so 0)."""
    total = int(cm.sum())
    tp = np.diag(cm).astype(np.float64)
    fp = cm.sum(axis=0).astype(np.float64) - tp
    fn = cm.sum(axis=1).astype(np.float64) - tp
    denom = 2.0 * tp + fp + fn
    zero = int(np.count_nonzero(denom == 0))
    f1 = np.zeros(N_CLASSES, dtype=np.float64)
    nz = denom > 0
    f1[nz] = 2.0 * tp[nz] / denom[nz]
    acc = float(np.trace(cm)) / total
    return acc, float(f1.mean()), zero


def metrics_from_cm_batch(cms: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    """cms: [B, 6, 6] -> (acc[B], macro_f1[B], tong so lop co mau so 0)."""
    total = cms.sum(axis=(1, 2)).astype(np.float64)
    tp = np.diagonal(cms, axis1=1, axis2=2).astype(np.float64)
    fp = cms.sum(axis=1).astype(np.float64) - tp
    fn = cms.sum(axis=2).astype(np.float64) - tp
    denom = 2.0 * tp + fp + fn
    zero = int(np.count_nonzero(denom == 0))
    f1 = np.zeros_like(tp)
    nz = denom > 0
    f1[nz] = 2.0 * tp[nz] / denom[nz]
    acc = tp.sum(axis=1) / total
    return acc, f1.mean(axis=1), zero


def macro_f1_sklearn(labels: np.ndarray, preds: np.ndarray) -> float:
    return float(f1_score(labels, preds, average="macro", labels=list(range(N_CLASSES)),
                          zero_division=0))


def counts_from_draws(draws: np.ndarray, n_subjects: int) -> np.ndarray:
    counts = np.zeros((draws.shape[0], n_subjects), dtype=np.int64)
    for b in range(draws.shape[0]):
        for j in draws[b]:
            counts[b, int(j)] += 1
    return counts


def packed_cms(counts: np.ndarray, cm_stack: np.ndarray) -> np.ndarray:
    """counts [B, S], cm_stack [S, 6, 6] -> cms [B, 6, 6] (so cua so co boi so)."""
    return np.einsum("bs,sij->bij", counts, cm_stack)


def summarize(values: np.ndarray) -> dict:
    lo, hi = np.percentile(values, [2.5, 97.5], method="linear")
    return {
        "ci95_low": float(lo),
        "ci95_high": float(hi),
        "mean": float(values.mean()),
        "sd": float(values.std(ddof=1)),
        "n": int(values.size),
    }


def fmt(x: float, digits: int = 4) -> str:
    return f"{x:.{digits}f}"


def fmt_pp(x: float) -> str:
    return f"{x * 100.0:.2f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT),
                    help="thu muc ghi ket qua (dung thu muc tam khi kiem tinh tat dinh)")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mamba = read_predictions(MAMBA_CSV)
    mlp = read_predictions(MLP_CSV)
    mamba_metrics_file = json.loads(MAMBA_METRICS.read_text(encoding="utf-8"))
    mlp_metrics_file = json.loads(MLP_METRICS.read_text(encoding="utf-8"))

    print("=" * 78)
    print("BOOTSTRAP CI 95% THEO CUM NGUOI — Mamba (huan luyen lai) vs MLP")
    print("=" * 78)

    # ------------------------------------------------------------------ check 1
    ok = True
    problems = []
    if mamba["sample_id"] != mlp["sample_id"]:
        problems.append("sample_id khac nhau")
    if not np.array_equal(mamba["subject"], mlp["subject"]):
        problems.append("subject_id khac nhau")
    if not np.array_equal(mamba["label"], mlp["label"]):
        problems.append("label khac nhau")
    subjects = np.unique(mamba["subject"])
    if subjects.size != len(SUBJECT_WINDOWS):
        problems.append(f"{subjects.size} nguoi, mong doi {len(SUBJECT_WINDOWS)}")
    for s in subjects:
        n = int(np.count_nonzero(mamba["subject"] == s))
        want = SUBJECT_WINDOWS.get(int(s))
        if want is None:
            problems.append(f"nguoi {int(s)} khong co trong bang ky vong")
        elif n != want:
            problems.append(f"nguoi {int(s)}: {n} cua so, mong doi {want}")
    for name, arr in (("label", mamba["label"]), ("pred Mamba", mamba["pred"]),
                      ("pred MLP", mlp["pred"])):
        bad = int(np.count_nonzero((arr < 0) | (arr >= N_CLASSES)))
        if bad:
            problems.append(f"{name} co {bad} gia tri ngoai 0..5")
    ok = not problems
    print(f"CHECK 1 {'OK' if ok else 'FAIL'}: 2 file du doan khop tung hang "
          f"({EXPECTED_ROWS} dong, {subjects.size} nguoi, so cua so theo nguoi dung bang)")
    if problems:
        for p in problems:
            print("   -", p)
        raise SystemExit("DUNG: check 1 that bai")

    # --------------------------------------------------- bang chi so theo nguoi
    subject_list = [int(s) for s in subjects]  # da sap tang dan
    n_subjects = len(subject_list)
    cm_mamba = np.zeros((n_subjects, N_CLASSES, N_CLASSES), dtype=np.int64)
    cm_mlp = np.zeros((n_subjects, N_CLASSES, N_CLASSES), dtype=np.int64)
    subject_rows = []
    for i, s in enumerate(subject_list):
        mask = mamba["subject"] == s
        cm_mamba[i] = confusion(mamba["label"][mask], mamba["pred"][mask])
        cm_mlp[i] = confusion(mlp["label"][mask], mlp["pred"][mask])
        subject_rows.append({
            "subject_id": s,
            "n_windows": int(np.count_nonzero(mask)),
            "rows": np.nonzero(mask)[0],
            "cm_mamba": cm_mamba[i],
            "cm_mlp": cm_mlp[i],
        })

    # ------------------------------------------------------------------ check 3
    full_mamba = cm_mamba.sum(axis=0)
    full_mlp = cm_mlp.sum(axis=0)
    acc_m, f1_m, zero_full_m = metrics_from_cm(full_mamba)
    acc_p, f1_p, zero_full_p = metrics_from_cm(full_mlp)
    diffs = [
        abs(acc_m - float(mamba_metrics_file["accuracy"])),
        abs(f1_m - float(mamba_metrics_file["macro_f1"])),
        abs(acc_p - float(mlp_metrics_file["accuracy"])),
        abs(f1_p - float(mlp_metrics_file["macro_f1"])),
    ]
    worst = max(diffs)
    print(f"CHECK 3 {'OK' if worst <= CHECK_TOL else 'FAIL'}: chi so toan test tinh lai "
          f"bang ma tran nham lan khop test_metrics.json (sai khac tuyet doi lon nhat "
          f"{worst:.1e} <= {CHECK_TOL:.0e})")
    print(f"   Mamba: acc={acc_m:.12f} macro_f1={f1_m:.12f} | "
          f"MLP: acc={acc_p:.12f} macro_f1={f1_p:.12f}")
    if worst > CHECK_TOL:
        raise SystemExit("DUNG: check 3 that bai, xem output nguyen van")

    # -------------------------------------------------------------- bootstrap
    rng = np.random.default_rng(SEED)
    draws = rng.integers(0, n_subjects, size=(B_DRAWS, n_subjects))
    counts = counts_from_draws(draws, n_subjects)
    if not np.all(counts.sum(axis=1) == n_subjects):
        raise SystemExit("DUNG: so nguoi rut moi lan khac 9")

    def run_bootstrap(cm_a: np.ndarray, cm_b: np.ndarray):
        cms_a = packed_cms(counts, cm_a)
        cms_b = packed_cms(counts, cm_b)
        acc_a, f1_a, zero_a = metrics_from_cm_batch(cms_a)
        acc_b, f1_b, zero_b = metrics_from_cm_batch(cms_b)
        return {
            "acc_a": acc_a, "f1_a": f1_a, "acc_b": acc_b, "f1_b": f1_b,
            "delta_acc": acc_a - acc_b, "delta_f1": f1_a - f1_b,
            "zero_classes": zero_a + zero_b,
        }

    boot = run_bootstrap(cm_mamba, cm_mlp)

    # ------------------------------------------------------------------ check 2
    z = 0
    worst_eq = 0.0
    n_eq = 200
    for b in range(n_eq):
        idx = np.concatenate(
            [subject_rows[int(j)]["rows"] for j in draws[b]])
        for model_name, preds in (("mamba", mamba["pred"]), ("mlp", mlp["pred"])):
            acc_x = float(np.mean(preds[idx] == mamba["label"][idx]))
            f1_x = macro_f1_sklearn(mamba["label"][idx], preds[idx])
            acc_c = boot["acc_a" if model_name == "mamba" else "acc_b"][b]
            f1_c = boot["f1_a" if model_name == "mamba" else "f1_b"][b]
            worst_eq = max(worst_eq, abs(acc_x - float(acc_c)),
                           abs(f1_x - float(f1_c)))
    print(f"CHECK 2 {'OK' if worst_eq <= CHECK_TOL else 'FAIL'}: {n_eq} lan rut dau, resample "
          f"cua so tuong minh (sklearn) == tinh tu ma tran nham lan, sai khac tuyet doi "
          f"lon nhat {worst_eq:.1e} <= {CHECK_TOL:.0e}")
    if worst_eq > CHECK_TOL:
        raise SystemExit("DUNG: check 2 that bai")

    # ------------------------------------------------------------------ check 4
    zero_total = int(boot["zero_classes"])
    print(f"CHECK 4 {'OK' if zero_total == 0 else 'NOTE'}: so lan gap lop co mau so 0 trong "
          f"{B_DRAWS} lan bootstrap (ca 2 mo hinh) = {zero_total}")

    # ------------------------------------------------------------------ check 5
    neg = run_bootstrap(cm_mlp, cm_mlp)
    neg_max = max(float(np.max(np.abs(neg["delta_acc"]))),
                  float(np.max(np.abs(neg["delta_f1"]))))
    neg_lo_acc, neg_hi_acc = np.percentile(neg["delta_acc"], [2.5, 97.5], method="linear")
    neg_lo_f1, neg_hi_f1 = np.percentile(neg["delta_f1"], [2.5, 97.5], method="linear")
    neg_ok = (neg_max == 0.0 and neg_lo_acc == 0.0 and neg_hi_acc == 0.0
              and neg_lo_f1 == 0.0 and neg_hi_f1 == 0.0)
    print(f"CHECK 5 {'OK' if neg_ok else 'FAIL'}: doi chung am tinh (MLP vs MLP) — "
          f"max|delta| = {neg_max:.1e}, CI delta_acc = [{neg_lo_acc:.1f}, {neg_hi_acc:.1f}], "
          f"CI delta_macro_f1 = [{neg_lo_f1:.1f}, {neg_hi_f1:.1f}] (decimal, chua nhan 100)")
    if not neg_ok:
        raise SystemExit("DUNG: check 5 that bai")

    # ------------------------------------------------------------ ket qua chinh
    point = {
        "mamba": {"accuracy": acc_m, "macro_f1": f1_m},
        "mlp": {"accuracy": acc_p, "macro_f1": f1_p},
        "delta": {"accuracy": acc_m - acc_p, "macro_f1": f1_m - f1_p},
    }
    summary_models = {
        "mamba": {
            "accuracy": summarize(boot["acc_a"]),
            "macro_f1": summarize(boot["f1_a"]),
        },
        "mlp": {
            "accuracy": summarize(boot["acc_b"]),
            "macro_f1": summarize(boot["f1_b"]),
        },
        "delta": {
            "accuracy": summarize(boot["delta_acc"]),
            "macro_f1": summarize(boot["delta_f1"]),
        },
    }
    # cac lan delta theo dau
    d_f1 = boot["delta_f1"]
    d_acc = boot["delta_acc"]
    fractions = {
        "delta_macro_f1": {
            "lt0": float(np.mean(d_f1 < 0)),
            "eq0": float(np.mean(d_f1 == 0)),
            "gt0": float(np.mean(d_f1 > 0)),
            "n": int(d_f1.size),
        },
        "delta_accuracy": {
            "lt0": float(np.mean(d_acc < 0)),
            "eq0": float(np.mean(d_acc == 0)),
            "gt0": float(np.mean(d_acc > 0)),
            "n": int(d_acc.size),
        },
    }

    # --------------------------------------------------------------- LOSO
    loso_rows = []
    for i, s in enumerate(subject_list):
        keep = np.arange(n_subjects) != i
        cm_a = cm_mamba[keep].sum(axis=0)
        cm_b = cm_mlp[keep].sum(axis=0)
        a_a, f_a, _ = metrics_from_cm(cm_a)
        a_b, f_b, _ = metrics_from_cm(cm_b)
        loso_rows.append({
            "subject_excluded": s,
            "n_windows_remaining": int(sum(subject_rows[k]["n_windows"]
                                           for k in range(n_subjects) if keep[k])),
            "mamba_acc": a_a, "mamba_macro_f1": f_a,
            "mlp_acc": a_b, "mlp_macro_f1": f_b,
            "delta_acc": a_a - a_b, "delta_macro_f1": f_a - f_b,
        })
    loso_f1 = np.array([r["delta_macro_f1"] for r in loso_rows])
    loso_i_min = int(np.argmin(loso_f1))
    loso_i_max = int(np.argmax(loso_f1))

    # ------------------------------------------- do on dinh Monte Carlo (43, 44)
    mc = {}
    for seed in MC_SEEDS:
        rng_s = np.random.default_rng(seed)
        draws_s = rng_s.integers(0, n_subjects, size=(B_DRAWS, n_subjects))
        counts_s = counts_from_draws(draws_s, n_subjects)
        cms_a = packed_cms(counts_s, cm_mamba)
        cms_b = packed_cms(counts_s, cm_mlp)
        acc_a, f1_a, _ = metrics_from_cm_batch(cms_a)
        acc_b, f1_b, _ = metrics_from_cm_batch(cms_b)
        d1 = f1_a - f1_b
        d2 = acc_a - acc_b
        lo1, hi1 = np.percentile(d1, [2.5, 97.5], method="linear")
        lo2, hi2 = np.percentile(d2, [2.5, 97.5], method="linear")
        lo_m, hi_m = np.percentile(f1_a, [2.5, 97.5], method="linear")
        lo_p, hi_p = np.percentile(f1_b, [2.5, 97.5], method="linear")
        mc[str(seed)] = {
            "delta_macro_f1_ci95": [float(lo1), float(hi1)],
            "delta_accuracy_ci95": [float(lo2), float(hi2)],
            "mamba_macro_f1_ci95": [float(lo_m), float(hi_m)],
            "mlp_macro_f1_ci95": [float(lo_p), float(hi_p)],
        }

    # --------------------------------------------------------------- ghi file
    per_class = {}
    for name, cm in (("mamba", full_mamba), ("mlp", full_mlp)):
        tp = np.diag(cm).astype(np.float64)
        fp = cm.sum(axis=0).astype(np.float64) - tp
        fn = cm.sum(axis=1).astype(np.float64) - tp
        denom = 2.0 * tp + fp + fn
        f1 = np.where(denom > 0, 2.0 * tp / np.where(denom > 0, denom, 1.0), 0.0)
        per_class[name] = {str(i): float(f1[i]) for i in range(N_CLASSES)}

    results = {
        "config": {
            "seed": SEED,
            "B": B_DRAWS,
            "n_subjects": n_subjects,
            "n_windows": int(mamba["label"].size),
            "subject_ids": subject_list,
            "resample": "9 ma nguoi rut co hoan lai moi lan; giu toan bo cua so cua tung nguoi",
            "draws": "numpy.random.default_rng(42).integers(0, 9, size=(2000, 9)), thu tu C",
            "metrics": "accuracy + macro-F1 (labels 0..5, zero_division=0)",
            "ci": "percentile 2.5 / 97.5, numpy.percentile(method='linear')",
            "delta_unit_csv": "decimal (nhan 100 = diem phan tram)",
            "inputs": {
                "mamba_predictions": "ml/results/mamba_retrained/predictions_test.csv",
                "mamba_predictions_sha256": sha256_file(MAMBA_CSV),
                "mlp_predictions": "ml/results/predictions_test.csv",
                "mlp_predictions_sha256": sha256_file(MLP_CSV),
                "mamba_test_metrics": "ml/results/mamba_retrained/test_metrics.json",
                "mamba_test_metrics_sha256": sha256_file(MAMBA_METRICS),
                "mlp_test_metrics": "ml/results/test_metrics.json",
                "mlp_test_metrics_sha256": sha256_file(MLP_METRICS),
            },
        },
        "checks": {
            "1_predictions_consistent": {"ok": True, "rows": EXPECTED_ROWS,
                                         "subjects": subject_list},
            "2_resample_equivalence": {"ok": True, "draws_checked": n_eq,
                                       "max_abs_diff": worst_eq, "tolerance": CHECK_TOL},
            "3_test_metrics_recomputed": {"ok": True, "max_abs_diff": worst,
                                          "tolerance": CHECK_TOL},
            "4_zero_denominator_classes": zero_total,
            "5_negative_control_mlp_vs_mlp": {
                "max_abs_delta": neg_max,
                "delta_acc_ci95": [float(neg_lo_acc), float(neg_hi_acc)],
                "delta_macro_f1_ci95": [float(neg_lo_f1), float(neg_hi_f1)],
            },
            "6_determinism": "so sha256 cua hai lan chay trong bao cao, khong phai trong script",
        },
        "test_metrics": {
            "mamba": {"accuracy": acc_m, "macro_f1": f1_m,
                      "per_class_f1": per_class["mamba"]},
            "mlp": {"accuracy": acc_p, "macro_f1": f1_p,
                    "per_class_f1": per_class["mlp"]},
            "delta": {"accuracy": acc_m - acc_p, "macro_f1": f1_m - f1_p},
        },
        "bootstrap": summary_models,
        "delta_fractions": fractions,
        "loso": loso_rows,
        "monte_carlo_seeds": mc,
    }
    (out_dir / "bootstrap_results.json").write_text(
        json.dumps(results, indent=2) + "\n", encoding="utf-8", newline="\n")

    with open(out_dir / "bootstrap_draws.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["b"] + [f"subj_{j}" for j in range(n_subjects)]
                   + ["mamba_acc", "mamba_macro_f1", "mlp_acc", "mlp_macro_f1",
                      "delta_acc", "delta_macro_f1"])
        for b in range(B_DRAWS):
            w.writerow([b] + [subject_list[int(j)] for j in draws[b]]
                       + [f"{boot['acc_a'][b]:.9g}", f"{boot['f1_a'][b]:.9g}",
                          f"{boot['acc_b'][b]:.9g}", f"{boot['f1_b'][b]:.9g}",
                          f"{boot['delta_acc'][b]:.9g}", f"{boot['delta_f1'][b]:.9g}"])

    with open(out_dir / "per_subject_metrics.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["subject_id", "n_windows", "mamba_acc", "mamba_macro_f1",
                    "mlp_acc", "mlp_macro_f1", "delta_acc", "delta_macro_f1"])
        for r in subject_rows:
            a_a, f_a, _ = metrics_from_cm(r["cm_mamba"])
            a_b, f_b, _ = metrics_from_cm(r["cm_mlp"])
            w.writerow([r["subject_id"], r["n_windows"], f"{a_a:.9g}", f"{f_a:.9g}",
                        f"{a_b:.9g}", f"{f_b:.9g}",
                        f"{a_a - a_b:.9g}", f"{f_a - f_b:.9g}"])

    with open(out_dir / "loso_delta.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["subject_excluded", "n_windows_remaining", "mamba_acc",
                    "mamba_macro_f1", "mlp_acc", "mlp_macro_f1", "delta_acc",
                    "delta_macro_f1"])
        for r in loso_rows:
            w.writerow([r["subject_excluded"], r["n_windows_remaining"],
                        f"{r['mamba_acc']:.9g}", f"{r['mamba_macro_f1']:.9g}",
                        f"{r['mlp_acc']:.9g}", f"{r['mlp_macro_f1']:.9g}",
                        f"{r['delta_acc']:.9g}", f"{r['delta_macro_f1']:.9g}"])

    # ------------------------------------------------------------ summary.md
    lines = []
    lines.append("# Bootstrap CI 95% theo cum nguoi — Mamba (huan luyen lai) va MLP")
    lines.append("")
    lines.append(f"- Tap test: **{EXPECTED_ROWS} cua so, {n_subjects} nguoi** "
                 f"(ma nguoi tang dan: {', '.join(str(s) for s in subject_list)}).")
    lines.append(f"- Bootstrap: **B = {B_DRAWS}**, seed **{SEED}**, moi lan rut 9 ma nguoi co "
                 "hoan lai (giu toan bo cua so cua nguoi duoc rut), hai mo hinh tinh tren "
                 "cung mot tap cua so (ghep cap).")
    lines.append("- Khoang 95%: percentile 2,5 / 97,5 (`numpy.percentile`, "
                 "`method=\"linear\"`). Diem uoc luong la chi so tren toan bo tap test, "
                 "khong phai trung binh bootstrap.")
    lines.append("- Don vi: chi so tung mo hinh ghi thap phan 4 chu so; Δ ghi theo "
                 "**diem phan tram** (2 chu so thap phan). Trong cac file CSV, Δ ghi dang "
                 "thap phan (nhan 100 de ra diem phan tram).")
    lines.append("")
    lines.append("## 1. Chi so toan test va khoang 95%")
    lines.append("")
    lines.append("| Mo hinh | Chi so | Toan test | Khoang 95% | Trung binh bootstrap | SD bootstrap |")
    lines.append("|---|---|---|---|---|---|")
    for model, label in (("mamba", "Mamba (huan luyen lai)"), ("mlp", "MLP 561-64-6")):
        for metric, mlabel in (("accuracy", "accuracy"), ("macro_f1", "macro-F1")):
            s = summary_models[model][metric]
            lines.append(f"| {label} | {mlabel} | {fmt(point[model][metric])} | "
                         f"[{fmt(s['ci95_low'])}, {fmt(s['ci95_high'])}] | "
                         f"{fmt(s['mean'])} | {s['sd']:.4f} |")
    lines.append("")
    lines.append("## 2. Chenh lech Δ = Mamba − MLP")
    lines.append("")
    lines.append("| Chi so | Δ toan test (diem %) | Khoang 95% Δ (diem %) | "
                 "Trung binh bootstrap (diem %) | SD (diem %) | Ti le Δ<0 | Ti le Δ=0 | Ti le Δ>0 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for metric, mlabel in (("accuracy", "Δaccuracy"), ("macro_f1", "Δmacro-F1")):
        s = summary_models["delta"][metric]
        fr = fractions["delta_accuracy" if metric == "accuracy" else "delta_macro_f1"]
        lines.append(f"| {mlabel} | {fmt_pp(point['delta'][metric])} | "
                     f"[{fmt_pp(s['ci95_low'])}, {fmt_pp(s['ci95_high'])}] | "
                     f"{fmt_pp(s['mean'])} | {s['sd'] * 100.0:.2f} | "
                     f"{fr['lt0']:.4f} | {fr['eq0']:.4f} | {fr['gt0']:.4f} |")
    lines.append("")
    lines.append(f"(Ti le tinh tren {B_DRAWS} lan bootstrap; Δ<0 nghia la Mamba thap hon MLP "
                 "trong lan rut do, Δ>0 nghia la nguoc lai.)")
    lines.append("")
    lines.append("## 3. Phan bo theo nguoi")
    lines.append("")
    lines.append("| Nguoi | So cua so | acc Mamba | macro-F1 Mamba | acc MLP | macro-F1 MLP | "
                 "Δacc (diem %) | ΔF1 (diem %) |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in subject_rows:
        a_a, f_a, z_a = metrics_from_cm(r["cm_mamba"])
        a_b, f_b, z_b = metrics_from_cm(r["cm_mlp"])
        lines.append(f"| {r['subject_id']} | {r['n_windows']} | {fmt(a_a)} | {fmt(f_a)} | "
                     f"{fmt(a_b)} | {fmt(f_b)} | {fmt_pp(a_a - a_b)} | {fmt_pp(f_a - f_b)} |")
    lines.append("")
    lines.append("Ghi chu: moi nguoi trong tap test deu co du 6 lop, nen macro-F1 trong nguoi "
                 "xac dinh duoc; so lop co mau so 0 khi tinh trong tung nguoi: "
                 f"Mamba={sum(metrics_from_cm(r['cm_mamba'])[2] for r in subject_rows)}, "
                 f"MLP={sum(metrics_from_cm(r['cm_mlp'])[2] for r in subject_rows)}.")
    lines.append("")
    lines.append("## 4. Bo-mot-nguoi (leave-one-subject-out)")
    lines.append("")
    lines.append("| Nguoi bi bo | So cua so con lai | Δacc (diem %) | ΔF1 (diem %) |")
    lines.append("|---|---|---|---|")
    for r in loso_rows:
        lines.append(f"| {r['subject_excluded']} | {r['n_windows_remaining']} | "
                     f"{fmt_pp(r['delta_acc'])} | {fmt_pp(r['delta_macro_f1'])} |")
    lines.append("")
    lines.append(f"- ΔF1 khi bo-mot-nguoi: nho nhat {fmt_pp(loso_f1[loso_i_min])} diem % "
                 f"(bo nguoi {subject_list[loso_i_min]}), lon nhat "
                 f"{fmt_pp(loso_f1[loso_i_max])} diem % (bo nguoi {subject_list[loso_i_max]}); "
                 f"khoang {fmt_pp(loso_f1[loso_i_min])} … {fmt_pp(loso_f1[loso_i_max])} diem %.")
    lines.append("")
    lines.append("## 5. F1 theo lop tren toan bo tap test (khong co khoang tin cay)")
    lines.append("")
    lines.append("| Lop | F1 Mamba | F1 MLP |")
    lines.append("|---|---|---|")
    names = ["WALKING", "WALKING_UPSTAIRS", "WALKING_DOWNSTAIRS", "SITTING",
             "STANDING", "LAYING"]
    for i in range(N_CLASSES):
        lines.append(f"| {i} {names[i]} | {fmt(per_class['mamba'][str(i)])} | "
                     f"{fmt(per_class['mlp'][str(i)])} |")
    lines.append("")
    lines.append("## 6. Do on dinh Monte Carlo cua chinh bootstrap (seed 43, 44)")
    lines.append("")
    lines.append("Chay lai bootstrap voi seed 43 va 44 **chi de xem dau mut khoang 95% dich "
                 "bao nhieu**. Day **khong phai** bien thien do khoi tao/huan luyen va "
                 "**khong** duoc dung de chon seed; ket qua chinh thuc van la seed 42.")
    lines.append("")
    lines.append("| Seed | CI ΔF1 (diem %) | CI Δacc (diem %) | CI F1 Mamba | CI F1 MLP |")
    lines.append("|---|---|---|---|---|")
    for seed in (SEED, 43, 44):
        if seed == SEED:
            d1 = summary_models["delta"]["macro_f1"]
            d2 = summary_models["delta"]["accuracy"]
            m1 = summary_models["mamba"]["macro_f1"]
            p1 = summary_models["mlp"]["macro_f1"]
            lines.append(f"| {seed} (chinh thuc) | "
                         f"[{fmt_pp(d1['ci95_low'])}, {fmt_pp(d1['ci95_high'])}] | "
                         f"[{fmt_pp(d2['ci95_low'])}, {fmt_pp(d2['ci95_high'])}] | "
                         f"[{fmt(m1['ci95_low'])}, {fmt(m1['ci95_high'])}] | "
                         f"[{fmt(p1['ci95_low'])}, {fmt(p1['ci95_high'])}] |")
        else:
            s = mc[str(seed)]
            lines.append(f"| {seed} | [{fmt_pp(s['delta_macro_f1_ci95'][0])}, "
                         f"{fmt_pp(s['delta_macro_f1_ci95'][1])}] | "
                         f"[{fmt_pp(s['delta_accuracy_ci95'][0])}, "
                         f"{fmt_pp(s['delta_accuracy_ci95'][1])}] | "
                         f"[{fmt(s['mamba_macro_f1_ci95'][0])}, "
                         f"{fmt(s['mamba_macro_f1_ci95'][1])}] | "
                         f"[{fmt(s['mlp_macro_f1_ci95'][0])}, "
                         f"{fmt(s['mlp_macro_f1_ci95'][1])}] |")
    lines.append("")
    lines.append("## 7. Kiem tra tu dong")
    lines.append("")
    lines.append(f"1. Hai file du doan khop tung hang (sample_id, subject_id, label), "
                 f"{EXPECTED_ROWS} dong, {n_subjects} nguoi, so cua so theo nguoi dung bang "
                 f"o muc 0 cua brief.")
    lines.append(f"2. Tuong duong resample: {n_eq} lan rut dau, sai khac tuyet doi lon nhat "
                 f"giua resample cua so tuong minh (sklearn) va tinh tu ma tran nham lan la "
                 f"{worst_eq:.1e} (<= {CHECK_TOL:.0e}).")
    lines.append(f"3. Chi so toan test tinh lai bang ma tran nham lan khop hai "
                 f"test_metrics.json: sai khac tuyet doi lon nhat {worst:.1e} "
                 f"(<= {CHECK_TOL:.0e}).")
    lines.append(f"4. So lan gap lop co mau so 0 trong {B_DRAWS} lan bootstrap (ca 2 mo hinh): "
                 f"{zero_total}.")
    lines.append(f"5. Doi chung am tinh (MLP vs MLP): max|Δ| = {neg_max:.1e}, CI Δacc = "
                 f"[{neg_lo_acc:.1f}, {neg_hi_acc:.1f}], CI Δmacro-F1 = "
                 f"[{neg_lo_f1:.1f}, {neg_hi_f1:.1f}] (thap phan).")
    lines.append("6. Tinh tat dinh: chay lai cung dau vao va seed cho sha256 tung file "
                 "ket qua giong het nhau.")
    lines.append("")
    lines.append("## 8. Ghi chu bat buoc")
    lines.append("")
    lines.append("- Tap test chi co **9 nguoi** -> phan phoi bootstrap chi co 9 phan tu goc de "
                 "lay lai; khoang 95% bang percentile voi so cum nho co the qua hep hoac khong "
                 "on dinh. Dien giai than trong.")
    lines.append("- Moi mo hinh huan luyen **mot seed (42)** -> khoang nay **khong** mo ta bien "
                 "thien do khoi tao/huan luyen.")
    lines.append("- Nguong sai so (neu co) chua duoc GVHD chot; tai lieu nay khong dung nguong "
                 "nao.")
    lines.append("- Mamba huan luyen lai bang PyTorch thuan (khong `mamba_ssm`), cung "
                 "`ml/split_manifest.csv` voi MLP; trong so Mamba cong khai **khong** tham gia.")
    lines.append("- Khong xep hang hai mo hinh; tai lieu chi mo ta chenh lech va do bat dinh "
                 "cua phep do.")
    summary_text = "\n".join(lines) + "\n"
    (out_dir / "bootstrap_summary.md").write_text(
        summary_text, encoding="utf-8", newline="\n")

    # ------------------------------------------------------------------ in ra
    print()
    print(f"Delta toan test (diem %): dF1 = {fmt_pp(point['delta']['macro_f1'])}, "
          f"dacc = {fmt_pp(point['delta']['accuracy'])}")
    print(f"CI95 dF1 (diem %): [{fmt_pp(summary_models['delta']['macro_f1']['ci95_low'])}, "
          f"{fmt_pp(summary_models['delta']['macro_f1']['ci95_high'])}]")
    print(f"CI95 dacc (diem %): [{fmt_pp(summary_models['delta']['accuracy']['ci95_low'])}, "
          f"{fmt_pp(summary_models['delta']['accuracy']['ci95_high'])}]")
    print(f"Ti le dF1<0: {fractions['delta_macro_f1']['lt0']:.4f} | =0: "
          f"{fractions['delta_macro_f1']['eq0']:.4f} | >0: "
          f"{fractions['delta_macro_f1']['gt0']:.4f}")
    print()
    print("sha256 cac file ket qua:")
    for name in ("bootstrap_results.json", "bootstrap_draws.csv",
                 "per_subject_metrics.csv", "loso_delta.csv", "bootstrap_summary.md"):
        print(f"  {sha256_file(out_dir / name)}  {name}")
    print(f"wrote {out_dir.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

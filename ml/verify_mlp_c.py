#!/usr/bin/env python3
"""Doi chieu logit MLP do C tinh voi logit PyTorch tren toan bo 2947 mau test.

Chay tu goc repo, sau khi da co CSV tu runner C:
    .venv-ml\\Scripts\\python ml\\verify_mlp_c.py

Dau ra: ml/results/verify_c_vs_torch.txt
Kem kiem tra am tinh: sua 1 trong so trong bản sao tam cua header, build lai,
xac nhan sai lech tang ro ret; khong dung file that.
"""
import argparse
import csv
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "UCI HAR Dataset"
DEFAULT_C_CSV = ROOT / "ml" / "results" / "mlp_c_logits_test.csv"
DEFAULT_TORCH_CSV = ROOT / "ml" / "results" / "predictions_test.csv"
DEFAULT_HEADER = ROOT / "firmware" / "common" / "mlp_weights.h"
DEFAULT_F32 = ROOT / "firmware" / "host" / "logs" / "uci_test.f32"
REPORT = ROOT / "ml" / "results" / "verify_c_vs_torch.txt"

HOST_C = ROOT / "firmware" / "host" / "host_main_mlp.c"
MLP_C = ROOT / "firmware" / "common" / "mlp_har.c"
MLP_H = ROOT / "firmware" / "common" / "mlp_har.h"
COMMON = ROOT / "firmware" / "common"


def wsl_path(path: Path) -> str:
    s = str(Path(path).resolve())
    if len(s) >= 2 and s[1] == ":":
        return "/mnt/" + s[0].lower() + s[2:].replace("\\", "/")
    return s.replace("\\", "/")


def shq(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def load_c_csv(path: Path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    idx = [int(r["sample_index"]) for r in rows]
    pred = np.array([int(r["pred"]) for r in rows], dtype=np.int64)
    logits = np.array([[float(r[f"logit{c}"]) for c in range(6)] for r in rows], dtype=np.float64)
    return idx, pred, logits


def load_torch_csv(path: Path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    pred = np.array([int(r["pred"]) for r in rows], dtype=np.int64)
    logits = np.array([[float(r[f"logit{c}"]) for c in range(6)] for r in rows], dtype=np.float64)
    return pred, logits


def score_output(csv_path: Path) -> str:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "firmware" / "host" / "uci_har.py"), "score",
         str(csv_path), str(DATA)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"uci_har.py score loi:\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout.rstrip("\n")


def negative_control(header: Path, f32: Path, torch_logits: np.ndarray) -> dict:
    text = header.read_text(encoding="utf-8")
    m = re.search(r"(static const float mlp_w1\[[^\]]+\] = \{\s*)([-+]?\d+\.\d{9}e[-+]\d{2,3})", text)
    if not m:
        raise AssertionError("khong tim thay phan tu dau cua mlp_w1")
    old = float(m.group(2))
    new = old + 1.0
    mutated = text[:m.start(2)] + f"{new:.9e}" + text[m.end(2):]
    assert mutated != text

    tmp = Path(tempfile.mkdtemp(prefix="mlp_neg_"))
    try:
        (tmp / "mlp_weights.h").write_text(mutated, encoding="utf-8", newline="\n")
        shutil.copy2(MLP_C, tmp / "mlp_har.c")
        shutil.copy2(MLP_H, tmp / "mlp_har.h")
        out_csv = tmp / "neg_logits.csv"
        bin_wsl = "/tmp/host_main_mlp_neg_bin"
        cmd = (
            f"gcc -O2 -std=c11 -I {shq(wsl_path(tmp))} -I {shq(wsl_path(COMMON))} "
            f"-o {shq(bin_wsl)} {shq(wsl_path(HOST_C))} {shq(wsl_path(tmp / 'mlp_har.c'))} -lm"
        )
        build = subprocess.run(["wsl", "-e", "bash", "-c", cmd], capture_output=True, text=True)
        if build.returncode != 0:
            raise RuntimeError(f"build negative control loi:\n{build.stdout}\n{build.stderr}")
        run = subprocess.run(
            ["wsl", "-e", "bash", "-c",
             f"{shq(bin_wsl)} --batch {shq(wsl_path(f32))} {shq(wsl_path(out_csv))}"],
            capture_output=True, text=True,
        )
        if run.returncode != 0:
            raise RuntimeError(f"chay negative control loi:\n{run.stdout}\n{run.stderr}")
        idx, pred, logits = load_c_csv(out_csv)
        assert idx == list(range(len(idx))), "negative control: sample_index khong lien tuc"
        assert len(idx) == len(torch_logits), (len(idx), len(torch_logits))
        diff = np.abs(logits - torch_logits)
        return {
            "mutated_weight_old": old,
            "mutated_weight_new": new,
            "pred_mismatch": int(np.count_nonzero(pred != torch_logits.argmax(axis=1))),
            "max_abs_delta": float(diff.max()),
            "mae": float(diff.mean()),
        }
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        subprocess.run(["wsl", "-e", "bash", "-c", "rm -f /tmp/host_main_mlp_neg_bin"],
                       capture_output=True, text=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--c-csv", default=str(DEFAULT_C_CSV))
    ap.add_argument("--torch-csv", default=str(DEFAULT_TORCH_CSV))
    ap.add_argument("--header", default=str(DEFAULT_HEADER))
    ap.add_argument("--f32", default=str(DEFAULT_F32))
    args = ap.parse_args()

    c_csv = Path(args.c_csv)
    t_csv = Path(args.torch_csv)
    header = Path(args.header)
    f32 = Path(args.f32)

    c_idx, c_pred, c_logits = load_c_csv(c_csv)
    t_pred, t_logits = load_torch_csv(t_csv)
    assert len(c_idx) == len(t_pred), (len(c_idx), len(t_pred))
    assert c_idx == list(range(len(c_idx))), "sample_index cua C khong lien tuc 0..N-1"
    assert c_logits.shape == t_logits.shape == (len(c_idx), 6), (c_logits.shape, t_logits.shape)

    diff = np.abs(c_logits - t_logits)
    max_pos = np.unravel_index(int(diff.argmax()), diff.shape)
    pred_mismatch = int(np.count_nonzero(c_pred != t_pred))

    lines = []
    lines.append("Doi chieu MLP: C (firmware/common/mlp_har.c) vs PyTorch (FP32, CPU)")
    lines.append("")
    lines.append(f"c_csv: {c_csv.relative_to(ROOT).as_posix()}")
    lines.append(f"torch_csv: {t_csv.relative_to(ROOT).as_posix()}")
    lines.append(f"header: {header.relative_to(ROOT).as_posix()}")
    lines.append(f"samples: {len(c_idx)}")
    lines.append(f"pred khac nhau: {pred_mismatch}")
    lines.append(f"max|dlogit|: {float(diff.max()):.9e}")
    lines.append(f"MAE: {float(diff.mean()):.9e}")
    lines.append(
        f"vi tri lech lon nhat: sample_index={int(max_pos[0])} logit={int(max_pos[1])} "
        f"c={c_logits[max_pos]:.9e} torch={t_logits[max_pos]:.9e} delta={diff[max_pos]:.9e}")
    lines.append("")
    lines.append("uci_har.py score (CSV tu C):")
    lines.append(score_output(c_csv))
    lines.append("")
    lines.append("uci_har.py score (CSV tu PyTorch):")
    lines.append(score_output(t_csv))
    lines.append("")
    lines.append("Kiem tra am tinh: sua 1 trong so trong ban sao tam cua header, build lai, chay lai")
    neg = negative_control(header, f32, t_logits)
    lines.append(f"  mlp_w1[0]: {neg['mutated_weight_old']:.9e} -> {neg['mutated_weight_new']:.9e} (+1.0)")
    lines.append(f"  pred khac nhau: {neg['pred_mismatch']}")
    lines.append(f"  max|dlogit|: {neg['max_abs_delta']:.9e}")
    lines.append(f"  MAE: {neg['mae']:.9e}")
    lines.append("")

    if pred_mismatch != 0 or float(diff.max()) > 1e-3:
        lines.append("CANH BAO: sai lech lon hon ky vong dinh tinh (pred phai giong het, logit co ~1e-6).")
        status = 1
    else:
        lines.append("OK: pred giong het; logit lech o muc float32 (ky vong dinh tinh ~1e-6).")
        status = 0
    if not (neg["max_abs_delta"] > max(1e-2, 100.0 * float(diff.max()))):
        lines.append("CANH BAO: kiem tra am tinh khong lam sai lech tang ro ret.")
        status = 1
    else:
        lines.append("OK: kiem tra am tinh lam sai lech tang ro ret.")

    text = "\n".join(lines) + "\n"
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return status


if __name__ == "__main__":
    raise SystemExit(main())

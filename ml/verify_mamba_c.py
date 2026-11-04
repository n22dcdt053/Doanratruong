#!/usr/bin/env python3
"""Doi chieu logit Mamba do C tinh voi logit PyTorch tren toan bo 2947 mau test.

Chay tu goc repo, sau khi da co CSV tu runner C (firmware/host/run_host_retrained.sh):
    .venv-ml\\Scripts\\python ml\\verify_mamba_c.py

Dau ra: ml/results/mamba_retrained/verify_c_vs_torch.txt
Kem kiem tra am tinh: sua 1 trong so trong ban sao tam cua header, build lai,
xac nhan sai lech tang; khong dung file that, khong commit ban sao.
Chi bao so do; khong dat nguong dung sai cho |dlogit|.
"""
import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "UCI HAR Dataset"
MAMBA_DIR = ROOT / "ml" / "results" / "mamba_retrained"
DEFAULT_C_CSV = MAMBA_DIR / "mamba_c_logits_test.csv"
DEFAULT_TORCH_CSV = MAMBA_DIR / "predictions_test.csv"
DEFAULT_HEADER = MAMBA_DIR / "mamba_weights.h"
DEFAULT_F32 = ROOT / "firmware" / "host" / "logs" / "uci_test.f32"
REPORT = MAMBA_DIR / "verify_c_vs_torch.txt"

HOST_C = ROOT / "firmware" / "host" / "host_main.c"
VENDOR = ROOT / "firmware" / "common"
CSRC = ROOT / "MambaLite-Micro" / "csrc"
UPSTREAM_INC = ROOT / "MambaLite-Micro" / "examples" / "mambahar-arduino-6" / "include"

N_CLASSES = 6


def wsl_path(path: Path) -> str:
    s = str(Path(path).resolve())
    if len(s) >= 2 and s[1] == ":":
        return "/mnt/" + s[0].lower() + s[2:].replace("\\", "/")
    return s.replace("\\", "/")


def shq(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_c_csv(path: Path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    idx = [int(r["sample_index"]) for r in rows]
    pred = np.array([int(r["pred"]) for r in rows], dtype=np.int64)
    logits = np.array(
        [[float(r[f"logit{c}"]) for c in range(N_CLASSES)] for r in rows], dtype=np.float64)
    return idx, pred, logits


def load_torch_csv(path: Path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    pred = np.array([int(r["pred"]) for r in rows], dtype=np.int64)
    logits = np.array(
        [[float(r[f"logit{c}"]) for c in range(N_CLASSES)] for r in rows], dtype=np.float64)
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
    m = re.search(r"(const float linear_in_weight\[\d+\] = \{\s*)([-+]?\d+\.\d{9}e[-+]\d{2,3})f", text)
    if not m:
        raise AssertionError("khong tim thay phan tu dau cua linear_in_weight")
    old = float(m.group(2))
    new = old + 1.0
    mutated = text[:m.start(2)] + f"{new:.9e}" + text[m.end(2):]
    assert mutated != text

    tmp = Path(tempfile.mkdtemp(prefix="mamba_neg_"))
    try:
        (tmp / "mamba_weights.h").write_text(mutated, encoding="utf-8", newline="\n")
        out_csv = tmp / "neg_logits.csv"
        bin_wsl = "/tmp/host_main_mamba_neg_bin"
        includes = " ".join(shq(wsl_path(p)) for p in (tmp, VENDOR, CSRC, UPSTREAM_INC))
        cmd = (f"gcc -O2 -o {shq(bin_wsl)} {shq(wsl_path(HOST_C))} {includes} -lm")
        build = subprocess.run(["wsl", "-e", "bash", "-c", cmd],
                               capture_output=True, text=True)
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
        subprocess.run(["wsl", "-e", "bash", "-c", f"rm -f {shq(bin_wsl)}"],
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
    assert c_logits.shape == t_logits.shape == (len(c_idx), N_CLASSES), (
        c_logits.shape, t_logits.shape)
    if not np.isfinite(c_logits).all():
        raise SystemExit("DUNG: logit C co NaN/Inf — bao nguyen van, khong tu sua")

    diff = np.abs(c_logits - t_logits)
    max_pos = np.unravel_index(int(diff.argmax()), diff.shape)
    pred_mismatch = int(np.count_nonzero(c_pred != t_pred))

    lines = []
    lines.append("Doi chieu Mamba huan luyen lai: C (firmware/common/mamba.c) vs PyTorch (FP32, CPU)")
    lines.append("")
    lines.append(f"c_csv: {c_csv.relative_to(ROOT).as_posix()}")
    lines.append(f"torch_csv: {t_csv.relative_to(ROOT).as_posix()}")
    lines.append(f"header: {header.relative_to(ROOT).as_posix()}")
    lines.append(f"header sha256: {sha256_file(header)}")
    lines.append(f"samples: {len(c_idx)}")
    lines.append(f"pred khac nhau: {pred_mismatch}")
    lines.append(f"max|dlogit|: {float(diff.max()):.9e}")
    lines.append(f"MAE: {float(diff.mean()):.9e}")
    lines.append(
        f"vi tri lech lon nhat: sample_index={int(max_pos[0])} logit={int(max_pos[1])} "
        f"c={c_logits[max_pos]:.9e} torch={t_logits[max_pos]:.9e} delta={diff[max_pos]:.9e}")
    lines.append(f"khoang logit C: min={float(c_logits.min()):.9e} max={float(c_logits.max()):.9e}")
    lines.append(f"khoang logit PyTorch: min={float(t_logits.min()):.9e} max={float(t_logits.max()):.9e}")
    lines.append("")
    lines.append("uci_har.py score (CSV tu C):")
    lines.append(score_output(c_csv))
    lines.append("")
    lines.append("uci_har.py score (CSV tu PyTorch):")
    lines.append(score_output(t_csv))
    lines.append("")
    lines.append("Kiem tra am tinh: sua 1 trong so trong ban sao tam cua header, build lai, chay lai")
    neg = negative_control(header, f32, t_logits)
    lines.append(f"  linear_in_weight[0]: {neg['mutated_weight_old']:.9e} -> "
                 f"{neg['mutated_weight_new']:.9e} (+1.0)")
    lines.append(f"  pred khac nhau: {neg['pred_mismatch']}")
    lines.append(f"  max|dlogit|: {neg['max_abs_delta']:.9e}")
    lines.append(f"  MAE: {neg['mae']:.9e}")
    lines.append("")
    lines.append("Ghi chu: chi bao so do; khong dat nguong dung sai cho |dlogit|. P2 do tren tap")
    lines.append("train (trong so cong khai): pred khop 7352/7352, max|dlogit| 1.879934254e-04.")
    lines.append("")

    status = 0
    if pred_mismatch != 0:
        lines.append("CANH BAO: co mau pred khac nhau giua C va PyTorch.")
        status = 1
    if not (neg["max_abs_delta"] > max(1e-2, 100.0 * float(diff.max()))):
        lines.append("CANH BAO: kiem tra am tinh khong lam sai lech tang ro ret.")
        status = 1
    else:
        lines.append("Kiem tra am tinh: sai lech tang ro ret so voi baseline (xem so o tren).")

    text = "\n".join(lines) + "\n"
    REPORT.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")
    return status


if __name__ == "__main__":
    raise SystemExit(main())

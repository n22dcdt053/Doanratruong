#!/usr/bin/env python3
"""Doi chieu PyTorch (trong so cong khai) voi runner C tren tap train.

Chay tu goc repo, sau khi da tao uci_train.f32 va CSV logit C:
    .venv-ml\\Scripts\\python ml\\check_fidelity.py

Doc:
    firmware/host/logs/uci_train.f32        (7352 x 570 float32 LE)
    ml/results/fidelity_public_weights_c_logits.csv
    MambaLite-Micro/.../mamba_weights.h

Ghi:
    ml/results/fidelity_public_weights.txt  (nguyen van)

Khong doc X_test.txt hay uci_test.f32. Chi bao so, khong ket luan.
"""
import csv
from pathlib import Path

import numpy as np
import torch

from load_public_weights import DEFAULT_HEADER, load_public_weights, sha256_file
from mamba_torch import MambaHAR, N_FEAT, N_TIME

ROOT = Path(__file__).resolve().parents[1]
TRAIN_F32 = ROOT / "firmware" / "host" / "logs" / "uci_train.f32"
C_CSV = ROOT / "ml" / "results" / "fidelity_public_weights_c_logits.csv"
REPORT = ROOT / "ml" / "results" / "fidelity_public_weights.txt"

EXPECTED_ROWS = 7352
BATCH = 256


def read_c_csv(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    expected = ["sample_index", "pred"] + [f"logit{c}" for c in range(6)]
    if header != expected:
        raise SystemExit(f"{path}: header {header}, expected {expected}")
    indices, preds, logits = [], [], []
    for row in rows[1:]:
        if len(row) != 8:
            raise SystemExit(f"{path}: malformed row {row}")
        indices.append(int(row[0]))
        preds.append(int(row[1]))
        logits.append([float(v) for v in row[2:]])
    return (
        np.asarray(indices, dtype=np.int64),
        np.asarray(preds, dtype=np.int64),
        np.asarray(logits, dtype=np.float64),
    )


def main() -> int:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)

    raw = np.fromfile(TRAIN_F32, dtype="<f4")
    n_values = EXPECTED_ROWS * N_TIME * N_FEAT
    if raw.size != n_values:
        raise SystemExit(f"{TRAIN_F32}: {raw.size} floats, expected {n_values}")
    x = torch.from_numpy(raw.reshape(EXPECTED_ROWS, N_TIME, N_FEAT).copy())

    model = MambaHAR()
    load_public_weights(model)
    model.eval()
    chunks = []
    with torch.no_grad():
        for start in range(0, x.shape[0], BATCH):
            chunks.append(model(x[start : start + BATCH]))
    torch_logits = torch.cat(chunks, dim=0).numpy().astype(np.float64)
    torch_pred = torch_logits.argmax(axis=1)

    indices, c_pred, c_logits = read_c_csv(C_CSV)
    if indices.size != EXPECTED_ROWS or not np.array_equal(
        indices, np.arange(EXPECTED_ROWS)
    ):
        raise SystemExit(f"{C_CSV}: sample_index is not 0..{EXPECTED_ROWS - 1}")
    if c_logits.shape != torch_logits.shape:
        raise SystemExit(f"shape mismatch: C {c_logits.shape}, torch {torch_logits.shape}")
    if not np.isfinite(torch_logits).all():
        raise SystemExit("PyTorch produced non-finite logits")
    if not np.isfinite(c_logits).all():
        raise SystemExit("C produced non-finite logits")

    diff = np.abs(torch_logits - c_logits)
    mismatch = np.nonzero(torch_pred != c_pred)[0]
    flat_idx = int(np.argmax(diff))
    worst_sample, worst_class = np.unravel_index(flat_idx, diff.shape)

    lines = [
        "Fidelity check: public weights, train input only",
        f"header: {DEFAULT_HEADER.relative_to(ROOT)}",
        f"header sha256: {sha256_file(DEFAULT_HEADER)}",
        f"data: {TRAIN_F32.relative_to(ROOT)} ({TRAIN_F32.stat().st_size} bytes, {EXPECTED_ROWS} x {N_FEAT})",
        f"C logits: {C_CSV.relative_to(ROOT)}",
        "PyTorch model: ml/mamba_torch.py (MambaHAR)",
        f"samples: {EXPECTED_ROWS}",
        f"pred mismatch: {mismatch.size}",
        "pred mismatch indices: "
        + ("-" if mismatch.size == 0 else " ".join(str(int(i)) for i in mismatch[:50])),
        f"max|dlogit|: {diff.max():.9e}",
        f"MAE: {diff.mean():.9e}",
        (
            "max|dlogit| location: "
            f"sample={worst_sample}, class={worst_class}, "
            f"C={c_logits[worst_sample, worst_class]:.9e}, "
            f"torch={torch_logits[worst_sample, worst_class]:.9e}, "
            f"d={diff[worst_sample, worst_class]:.9e}"
        ),
        f"C logit range: min={c_logits.min():.9e}, max={c_logits.max():.9e}",
        f"torch logit range: min={torch_logits.min():.9e}, max={torch_logits.max():.9e}",
        f"finite logits: C={bool(np.isfinite(c_logits).all())}, torch={bool(np.isfinite(torch_logits).all())}",
        "note: logits are float32; comparisons are computed in float64 after cast",
    ]
    report = "\n".join(lines) + "\n"
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8", newline="\n")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

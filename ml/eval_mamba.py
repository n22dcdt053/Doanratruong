#!/usr/bin/env python3
"""Danh gia checkpoint Mamba da commit tren tap test, dung mot lan.

Chay tu goc repo, CHI sau khi checkpoint da duoc commit:
    .venv-ml\\Scripts\\python ml\\eval_mamba.py

Doc:
    ml/results/mamba_retrained/mamba_seed42.pt   (checkpoint da commit)
    ml/split_manifest.csv                        (cac dong split=test)
    data/UCI HAR Dataset/test/X_test.txt

Ghi (trong ml/results/mamba_retrained/):
    test_metrics.json
    test_confusion_matrix.csv
    predictions_test.csv
"""
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import confusion_matrix, f1_score

from mamba_torch import N_CLASSES, N_FEAT, N_TIME, MambaHAR

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "ml" / "results" / "mamba_retrained"
CKPT = RESULTS / "mamba_seed42.pt"
MANIFEST = ROOT / "ml" / "split_manifest.csv"
X_TEST_FILE = ROOT / "data" / "UCI HAR Dataset" / "test" / "X_test.txt"

N_RAW = 561
N_PAD = 9
BATCH = 256


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)

    if not CKPT.is_file():
        raise SystemExit(f"thieu checkpoint da commit: {CKPT}")
    ckpt_sha = sha256_file(CKPT)

    with open(MANIFEST, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == "test"]
    assert len(rows) == 2947, len(rows)
    assert all(r["source_file"] == "test/X_test.txt" for r in rows)

    X_all = np.loadtxt(X_TEST_FILE, dtype=np.float32)
    assert X_all.shape == (2947, N_RAW), X_all.shape
    idx = np.array([int(r["row_index"]) for r in rows], dtype=np.int64)
    y = np.array([int(r["label"]) for r in rows], dtype=np.int64)
    X = X_all[idx]
    assert X.shape == (len(rows), N_RAW)
    assert np.isfinite(X).all()
    X = np.concatenate([X, np.zeros((len(rows), N_PAD), dtype=np.float32)], axis=1)
    assert X.shape == (len(rows), N_TIME * N_FEAT), X.shape

    state = torch.load(CKPT, map_location="cpu", weights_only=True)
    model = MambaHAR()
    model.load_state_dict(state)
    model.eval()

    x_t = torch.from_numpy(X)
    chunks = []
    with torch.no_grad():
        for start in range(0, x_t.shape[0], BATCH):
            chunks.append(model(x_t[start : start + BATCH]))
    logits = torch.cat(chunks, dim=0).numpy()
    if not np.isfinite(logits).all():
        raise SystemExit("DUNG: logit test co NaN/Inf — khong tu sua, bao nguyen van")
    pred = logits.argmax(axis=1)

    acc = float((pred == y).mean())
    macro_f1 = float(f1_score(y, pred, average="macro", labels=list(range(N_CLASSES))))
    per_class = f1_score(y, pred, average=None, labels=list(range(N_CLASSES)))
    cm = confusion_matrix(y, pred, labels=list(range(N_CLASSES)))

    metrics = {
        "n_test": len(rows),
        "checkpoint": str(CKPT.relative_to(ROOT)).replace("\\", "/"),
        "checkpoint_sha256": ckpt_sha,
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class_f1": {str(i): float(per_class[i]) for i in range(N_CLASSES)},
        "confusion_matrix": [[int(v) for v in row] for row in cm],
    }
    (RESULTS / "test_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8", newline="\n")

    with open(RESULTS / "test_confusion_matrix.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["true_label"] + [str(i) for i in range(N_CLASSES)])
        for i in range(N_CLASSES):
            w.writerow([i] + [int(v) for v in cm[i]])

    with open(RESULTS / "predictions_test.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["sample_id", "subject_id", "label", "pred"]
                   + [f"logit{i}" for i in range(N_CLASSES)])
        for r, p, lg in zip(rows, pred, logits):
            w.writerow([r["sample_id"], r["subject_id"], r["label"], int(p)]
                       + [f"{float(v):.9g}" for v in lg])

    print(f"checkpoint={metrics['checkpoint']}")
    print(f"checkpoint_sha256={ckpt_sha}")
    print(f"n_test={len(rows)}")
    print(f"accuracy={acc:.6f}")
    print(f"macro_f1={macro_f1:.6f}")
    print("per_class_f1=" + " ".join(f"{i}:{per_class[i]:.6f}" for i in range(N_CLASSES)))
    print("confusion_matrix (hang=true, cot=pred):")
    for i in range(N_CLASSES):
        print("  " + " ".join(str(int(v)) for v in cm[i]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Danh gia checkpoint MLP da commit tren tap test, dung mot lan.

Chay tu goc repo, CHI sau khi checkpoint da duoc commit:
    .venv-ml\\Scripts\\python ml\\eval_mlp.py

Doc:
    ml/results/mlp_seed42.pt      (checkpoint da commit)
    ml/split_manifest.csv         (cac dong split=test)
    data/UCI HAR Dataset/test/X_test.txt

Ghi:
    ml/results/test_metrics.json
    ml/results/test_confusion_matrix.csv
    ml/results/predictions_test.csv
"""
import csv
import json
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import confusion_matrix, f1_score
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "ml" / "results"
CKPT = RESULTS / "mlp_seed42.pt"
MANIFEST = ROOT / "ml" / "split_manifest.csv"
X_TEST_FILE = ROOT / "data" / "UCI HAR Dataset" / "test" / "X_test.txt"

IN_FEATURES = 561
HIDDEN = 64
OUT_CLASSES = 6


def main() -> int:
    torch.set_num_threads(1)

    with open(MANIFEST, encoding="utf-8", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == "test"]
    assert len(rows) == 2947, len(rows)
    assert all(r["source_file"] == "test/X_test.txt" for r in rows)

    X_all = np.loadtxt(X_TEST_FILE, dtype=np.float32)
    assert X_all.shape == (2947, IN_FEATURES), X_all.shape
    idx = np.array([int(r["row_index"]) for r in rows], dtype=np.int64)
    y = np.array([int(r["label"]) for r in rows], dtype=np.int64)
    X = X_all[idx]
    assert X.shape == (len(rows), IN_FEATURES)
    assert np.isfinite(X).all()

    state = torch.load(CKPT, map_location="cpu", weights_only=True)
    model = nn.Sequential(
        nn.Linear(IN_FEATURES, HIDDEN),
        nn.ReLU(),
        nn.Linear(HIDDEN, OUT_CLASSES),
    )
    model.load_state_dict(state)
    model.eval()

    with torch.no_grad():
        logits = model(torch.from_numpy(X)).numpy()
    pred = logits.argmax(axis=1)

    acc = float((pred == y).mean())
    macro_f1 = float(f1_score(y, pred, average="macro", labels=list(range(OUT_CLASSES))))
    per_class = f1_score(y, pred, average=None, labels=list(range(OUT_CLASSES)))
    cm = confusion_matrix(y, pred, labels=list(range(OUT_CLASSES)))

    metrics = {
        "n_test": len(rows),
        "accuracy": acc,
        "macro_f1": macro_f1,
        "per_class_f1": {str(i): float(per_class[i]) for i in range(OUT_CLASSES)},
        "confusion_matrix": [[int(v) for v in row] for row in cm],
    }
    (RESULTS / "test_metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8", newline="\n")

    with open(RESULTS / "test_confusion_matrix.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["true_label"] + [str(i) for i in range(OUT_CLASSES)])
        for i in range(OUT_CLASSES):
            w.writerow([i] + [int(v) for v in cm[i]])

    with open(RESULTS / "predictions_test.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["sample_id", "subject_id", "label", "pred"]
                   + [f"logit{i}" for i in range(OUT_CLASSES)])
        for r, p, lg in zip(rows, pred, logits):
            w.writerow([r["sample_id"], r["subject_id"], r["label"], int(p)]
                       + [f"{float(v):.9g}" for v in lg])

    print(f"n_test={len(rows)}")
    print(f"accuracy={acc:.6f}")
    print(f"macro_f1={macro_f1:.6f}")
    print("per_class_f1=" + " ".join(f"{i}:{per_class[i]:.6f}" for i in range(OUT_CLASSES)))
    print("confusion_matrix (hang=true, cot=pred):")
    for i in range(OUT_CLASSES):
        print("  " + " ".join(str(int(v)) for v in cm[i]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

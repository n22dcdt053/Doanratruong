#!/usr/bin/env python3
"""UCI HAR test-set helpers for the host runner (no numpy needed).

  to-f32 <dataset_root> <out.f32>   X_test.txt (561 feats) -> pad 9 zeros -> 570 -> float32 LE
  score  <logits.csv> <dataset_root>  accuracy, macro-F1, NaN/invalid counts vs y_test.txt

Padding matches MambaLite-Micro/Python/train.py: F.pad(features, (0, 9)) then view(-1, 10, 57).
Dataset: "UCI HAR Dataset" (archive.ics.uci.edu/static/public/240/human+activity+recognition+using+smartphones.zip),
extracted to data/UCI HAR Dataset/ (gitignored).
"""
import argparse
import csv
import math
import struct
from pathlib import Path

N_FEAT = 570


def to_f32(root: Path, out: Path):
    src = root / "test" / "X_test.txt"
    rows = 0
    with open(src) as f, open(out, "wb") as g:
        for line in f:
            vals = [float(v) for v in line.split()]
            if len(vals) != 561:
                raise SystemExit(f"{src}: line {rows + 1} has {len(vals)} features, want 561")
            g.write(struct.pack("<570f", *(vals + [0.0] * 9)))
            rows += 1
    print(f"wrote {rows} samples ({out.stat().st_size} bytes) -> {out}")


def score(csv_path: Path, root: Path):
    # y_test.txt is 1..6; train.py uses sklearn LabelEncoder -> classes are 0-based
    labels = [int(v) - 1 for v in (root / "test" / "y_test.txt").read_text().split()]
    preds, nan_rows, invalid_rows = [], 0, 0
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            logits = [float(r[f"logit{c}"]) for c in range(6)]
            if any(not math.isfinite(v) for v in logits):
                nan_rows += 1
            p = int(r["pred"])
            if p < 0:
                invalid_rows += 1
            preds.append(p)
    if len(preds) != len(labels):
        raise SystemExit(f"{csv_path}: {len(preds)} predictions vs {len(labels)} labels")
    n = len(labels)
    acc = sum(p == y for p, y in zip(preds, labels)) / n
    f1s = []
    for c in range(6):
        tp = sum(p == c and y == c for p, y in zip(preds, labels))
        fp = sum(p == c and y != c for p, y in zip(preds, labels))
        fn = sum(p != c and y == c for p, y in zip(preds, labels))
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    print(f"samples: {n}")
    print(f"nan_rows (non-finite logits): {nan_rows}")
    print(f"invalid_rows (pred < 0): {invalid_rows}")
    print(f"accuracy: {acc:.4f}")
    print(f"macro-F1: {sum(f1s) / 6:.4f}")
    print("F1 per class: " + " ".join(f"c{c}={v:.4f}" for c, v in enumerate(f1s)))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("to-f32")
    p1.add_argument("dataset_root", type=Path)
    p1.add_argument("out", type=Path)
    p2 = sub.add_parser("score")
    p2.add_argument("csv_path", type=Path)
    p2.add_argument("dataset_root", type=Path)
    a = ap.parse_args()
    if a.cmd == "to-f32":
        to_f32(a.dataset_root, a.out)
    else:
        score(a.csv_path, a.dataset_root)


main()

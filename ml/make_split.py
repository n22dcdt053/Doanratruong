#!/usr/bin/env python3
"""Tao split_manifest.csv theo nguoi cho UCI HAR.

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\make_split.py

Quy tac:
    - Tap train goc (7352 dong, 21 nguoi) duoc chia train/val bang
      GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42), groups=subject_train.
    - Tap test goc (2947 dong, 9 nguoi) giu nguyen, toan bo nhan split=test.
    - Thu tu dong: toan bo train goc theo thu tu file, roi toan bo test goc.
"""
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "UCI HAR Dataset"
RESULTS = ROOT / "ml" / "results"

MANIFEST = ROOT / "ml" / "split_manifest.csv"
STATS = RESULTS / "split_stats.md"

COLUMNS = ["sample_id", "subject_id", "label", "split", "source_file", "row_index"]
CLASS_NAMES = ["WALKING", "WALKING_UPSTAIRS", "WALKING_DOWNSTAIRS", "SITTING", "STANDING", "LAYING"]


def main() -> int:
    y_train = np.loadtxt(DATA / "train" / "y_train.txt", dtype=np.int64)
    s_train = np.loadtxt(DATA / "train" / "subject_train.txt", dtype=np.int64)
    y_test = np.loadtxt(DATA / "test" / "y_test.txt", dtype=np.int64)
    s_test = np.loadtxt(DATA / "test" / "subject_test.txt", dtype=np.int64)

    assert y_train.shape == (7352,), y_train.shape
    assert y_test.shape == (2947,), y_test.shape
    assert s_train.shape == (7352,), s_train.shape
    assert s_test.shape == (2947,), s_test.shape

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, val_idx = next(splitter.split(np.zeros(len(y_train)), y_train, groups=s_train))
    train_idx = np.sort(train_idx)
    val_idx = np.sort(val_idx)

    mask_val = np.zeros(len(y_train), dtype=bool)
    mask_val[val_idx] = True

    rows = []
    for i in range(len(y_train)):
        rows.append({
            "sample_id": f"train_{i:04d}",
            "subject_id": int(s_train[i]),
            "label": int(y_train[i]) - 1,
            "split": "val" if mask_val[i] else "train",
            "source_file": "train/X_train.txt",
            "row_index": i,
        })
    for i in range(len(y_test)):
        rows.append({
            "sample_id": f"test_{i:04d}",
            "subject_id": int(s_test[i]),
            "label": int(y_test[i]) - 1,
            "split": "test",
            "source_file": "test/X_test.txt",
            "row_index": i,
        })

    # --- tu kiem ---
    assert len(rows) == 10299, len(rows)
    assert len({r["sample_id"] for r in rows}) == len(rows), "sample_id khong duy nhat"

    subjects_by_split = {}
    for r in rows:
        subjects_by_split.setdefault(r["split"], set()).add(r["subject_id"])
    for a in ("train", "val", "test"):
        for b in ("train", "val", "test"):
            if a < b:
                assert not (subjects_by_split[a] & subjects_by_split[b]), (a, b)

    for split in ("train", "val", "test"):
        labels_present = {r["label"] for r in rows if r["split"] == split}
        if labels_present != set(range(6)):
            print(f"CANH BAO: split {split} thieu lop: {sorted(set(range(6)) - labels_present)}")
            return 1

    assert all(r["label"] in range(6) for r in rows)
    assert all(r["split"] in {"train", "val", "test"} for r in rows)

    # --- ghi manifest (LF) ---
    with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # --- thong ke ---
    val_subjects = sorted(int(v) for v in np.unique(s_train[val_idx]))
    n_train_samples = int(len(train_idx))
    n_val_samples = int(len(val_idx))

    lines = []
    lines.append("# Thong ke chia tap — UCI HAR (GroupShuffleSplit theo nguoi)")
    lines.append("")
    lines.append("## Ket qua nguyen van cua sklearn")
    lines.append("")
    lines.append("```text")
    lines.append("GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)")
    lines.append("groups = subject_train (21 nguoi, 7352 mau)")
    lines.append(f"tap validation (test_idx cua splitter): {len(val_subjects)} nguoi {val_subjects}")
    lines.append(f"so mau validation: {n_val_samples}")
    lines.append(f"so mau train (con lai): {n_train_samples}")
    lines.append("```")
    lines.append("")
    lines.append("## So nguoi va so mau")
    lines.append("")
    lines.append("| Tap | So nguoi | So mau | Danh sach nguoi |")
    lines.append("|---|---|---|---|")
    for split in ("train", "val", "test"):
        subjects = sorted({r["subject_id"] for r in rows if r["split"] == split})
        count = sum(1 for r in rows if r["split"] == split)
        lines.append(f"| {split} | {len(subjects)} | {count} | {' '.join(str(s) for s in subjects)} |")
    lines.append("")
    lines.append("## Phan bo nhan")
    lines.append("")
    lines.append("| Tap | " + " | ".join(f"{i + 1} {CLASS_NAMES[i]}" for i in range(6)) + " | Tong |")
    lines.append("|---|" + "---|" * 7)
    for split in ("train", "val", "test"):
        counts = [sum(1 for r in rows if r["split"] == split and r["label"] == c) for c in range(6)]
        lines.append(f"| {split} | " + " | ".join(str(c) for c in counts) + f" | {sum(counts)} |")
    lines.append("")
    lines.append("## Ghi chu")
    lines.append("")
    lines.append("- Nhan trong manifest la 0..5 (nhan goc 1..6 tru 1).")
    lines.append("- Test goc giu nguyen toan bo 2947 mau / 9 nguoi; khong dung de chon bat cu thu gi.")
    lines.append("- `split_manifest.csv` ghi theo thu tu: toan bo train goc (7352 dong) roi toan bo test goc (2947 dong).")
    lines.append("")

    RESULTS.mkdir(parents=True, exist_ok=True)
    STATS.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    print(f"manifest: {MANIFEST} ({len(rows)} dong + header)")
    print(f"val subjects ({len(val_subjects)}): {val_subjects}")
    print(f"train samples={n_train_samples} val_samples={n_val_samples} test_samples={len(y_test)}")
    print(f"stats: {STATS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

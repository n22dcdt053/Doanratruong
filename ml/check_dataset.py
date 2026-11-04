#!/usr/bin/env python3
"""Kiem tra du lieu UCI HAR truoc khi chia tap va ghi checksum byte tho.

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\check_dataset.py

Dau ra:
    ml/results/data_checks.txt
    ml/dataset_checksums.json
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "UCI HAR Dataset"
OUT_DIR = ROOT / "ml" / "results"

FILES = {
    "train/X_train.txt": DATA / "train" / "X_train.txt",
    "train/y_train.txt": DATA / "train" / "y_train.txt",
    "train/subject_train.txt": DATA / "train" / "subject_train.txt",
    "test/X_test.txt": DATA / "test" / "X_test.txt",
    "test/y_test.txt": DATA / "test" / "y_test.txt",
    "test/subject_test.txt": DATA / "test" / "subject_test.txt",
}

EXPECTED_TEST_SUBJECTS = [2, 4, 9, 10, 12, 13, 18, 20, 24]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if not DATA.is_dir():
        print(f"FAIL: khong thay thu muc du lieu: {DATA}", file=sys.stderr)
        return 1

    missing = [str(p) for p in FILES.values() if not p.is_file()]
    if missing:
        print("FAIL: thieu file: " + ", ".join(missing), file=sys.stderr)
        return 1

    X_train = np.loadtxt(FILES["train/X_train.txt"], dtype=np.float32)
    y_train = np.loadtxt(FILES["train/y_train.txt"], dtype=np.int64)
    s_train = np.loadtxt(FILES["train/subject_train.txt"], dtype=np.int64)
    X_test = np.loadtxt(FILES["test/X_test.txt"], dtype=np.float32)
    y_test = np.loadtxt(FILES["test/y_test.txt"], dtype=np.int64)
    s_test = np.loadtxt(FILES["test/subject_test.txt"], dtype=np.int64)

    lines = []
    ok = True

    def check(cond: bool, desc: str, detail: str = "") -> None:
        nonlocal ok
        status = "OK  " if cond else "FAIL"
        if not cond:
            ok = False
        lines.append(f"{status} {desc}" + (f" | {detail}" if detail else ""))

    lines.append("UCI HAR dataset checks")
    lines.append(f"data_dir: {DATA}")
    lines.append("")

    check(X_train.shape == (7352, 561), "X_train.txt shape == 7352 x 561", str(X_train.shape))
    check(X_test.shape == (2947, 561), "X_test.txt shape == 2947 x 561", str(X_test.shape))
    check(y_train.shape == (7352,), "y_train.txt rows == 7352", str(y_train.shape))
    check(y_test.shape == (2947,), "y_test.txt rows == 2947", str(y_test.shape))
    check(s_train.shape == (7352,), "subject_train.txt rows == 7352", str(s_train.shape))
    check(s_test.shape == (2947,), "subject_test.txt rows == 2947", str(s_test.shape))

    n_bad_train = int(np.count_nonzero(~np.isfinite(X_train)))
    n_bad_test = int(np.count_nonzero(~np.isfinite(X_test)))
    check(n_bad_train == 0, "X_train khong co NaN/Inf", f"bad_values={n_bad_train}")
    check(n_bad_test == 0, "X_test khong co NaN/Inf", f"bad_values={n_bad_test}")

    check(int(y_train.min()) >= 1 and int(y_train.max()) <= 6,
          "y_train trong 1..6", f"min={int(y_train.min())} max={int(y_train.max())}")
    check(int(y_test.min()) >= 1 and int(y_test.max()) <= 6,
          "y_test trong 1..6", f"min={int(y_test.min())} max={int(y_test.max())}")

    tr_subj = sorted(int(v) for v in np.unique(s_train))
    te_subj = sorted(int(v) for v in np.unique(s_test))
    check(len(tr_subj) == 21, "so nguoi train == 21", f"{len(tr_subj)}: {tr_subj}")
    check(len(te_subj) == 9, "so nguoi test == 9", f"{len(te_subj)}: {te_subj}")
    check(te_subj == EXPECTED_TEST_SUBJECTS,
          "nguoi test == 2 4 9 10 12 13 18 20 24", str(te_subj))
    overlap = sorted(set(tr_subj) & set(te_subj))
    check(not overlap, "nguoi train va test khong trung nhau", f"overlap={overlap}")

    lines.append("")
    lines.append("Phan bo nhan (nhan goc 1..6):")
    for name, y in (("train", y_train), ("test", y_test)):
        counts = [int(np.count_nonzero(y == c)) for c in range(1, 7)]
        lines.append(f"  {name}: " + " ".join(f"{c}={n}" for c, n in zip(range(1, 7), counts))
                     + f" | tong={len(y)}")

    lines.append("")
    lines.append("Khoang gia tri dac trung:")
    lines.append(f"  X_train min={float(X_train.min()):.6g} max={float(X_train.max()):.6g}")
    lines.append(f"  X_test  min={float(X_test.min()):.6g} max={float(X_test.max()):.6g}")

    checksums = {name: sha256_file(path) for name, path in FILES.items()}
    lines.append("")
    lines.append("sha256 byte tho:")
    for name in FILES:
        lines.append(f"  {checksums[name]}  {name}")

    lines.append("")
    lines.append("KET LUAN: " + ("tat ca kiem tra OK" if ok else "CO KIEM TRA FAIL"))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "data_checks.txt").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (ROOT / "ml" / "dataset_checksums.json").write_text(
        json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    print("\n".join(lines))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

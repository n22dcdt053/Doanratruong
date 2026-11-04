#!/usr/bin/env python3
"""Sinh bo mau nhung 20 mau UCI HAR cho firmware MLP tren ESP32-S3.

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\gen_mlp_samples.py

Doc:
    firmware/mambahar-esp32s3/src/uci_samples.h   (danh sach uci_index cua Mamba)
    data/UCI HAR Dataset/test/X_test.txt          (561 dac trung goc, khong padding)
    data/UCI HAR Dataset/test/y_test.txt          (nhan that, chi de in thong tin)
    ml/results/mlp_c_logits_test.csv              (logit/pred tham chieu tu C host)

Ghi:
    firmware/mlp-esp32s3/src/mlp_samples.h

Moi float32 in bang %.9e de phuc hoi dung bit; script doc lai header vua sinh
va assert bit-exact voi du lieu goc.
"""
import csv
import hashlib
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MAMBA_SAMPLES = ROOT / "firmware" / "mambahar-esp32s3" / "src" / "uci_samples.h"
DATA = ROOT / "data" / "UCI HAR Dataset"
X_TEST = DATA / "test" / "X_test.txt"
Y_TEST = DATA / "test" / "y_test.txt"
C_CSV = ROOT / "ml" / "results" / "mlp_c_logits_test.csv"
CKPT = ROOT / "ml" / "results" / "mlp_seed42.pt"
WEIGHTS = ROOT / "firmware" / "common" / "mlp_weights.h"
OUT = ROOT / "firmware" / "mlp-esp32s3" / "src" / "mlp_samples.h"

# 20 chi so trong brief, dung de doi chieu voi uci_index doc tu header Mamba.
EXPECTED_INDICES = [79, 80, 81, 128, 133, 134, 109, 110, 111, 31,
                    33, 34, 0, 1, 2, 55, 56, 57, 112, 35]

N_SAMPLES = 20
N_FEAT = 561
N_CLASSES = 6


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_mamba_indices(path: Path) -> list:
    text = path.read_text(encoding="utf-8")
    m = re.search(r"static\s+const\s+int\s+uci_index\[20\]\s*=\s*\{([^}]*)\};", text)
    if not m:
        raise AssertionError(f"khong tim thay uci_index[20] trong {path}")
    values = [int(v.strip()) for v in m.group(1).split(",") if v.strip()]
    if len(values) != N_SAMPLES:
        raise AssertionError(f"uci_index co {len(values)} phan tu, can {N_SAMPLES}")
    if len(set(values)) != N_SAMPLES:
        raise AssertionError("uci_index co chi so trung")
    return values


def fmt_matrix(name: str, rows: np.ndarray, width: int) -> str:
    lines = [f"static const float {name}[{len(rows)}][{width}] = {{"]
    for row in rows:
        lines.append("    {")
        for start in range(0, width, 8):
            chunk = row[start:start + 8]
            lines.append("        " + ", ".join(f"{float(v):.9e}" for v in chunk) + ",")
        lines.append("    },")
    lines.append("};")
    return "\n".join(lines)


def parse_matrix(text: str, name: str, rows: int, width: int) -> np.ndarray:
    m = re.search(rf"static const float {name}\[{rows}\]\[{width}\] = \{{(.*?)\n\}};", text, re.S)
    if not m:
        raise AssertionError(f"khong tim thay mang {name} trong header")
    values = re.findall(r"[-+]?\d+\.\d{9}e[-+]\d{2,3}", m.group(1))
    want = rows * width
    if len(values) != want:
        raise AssertionError(f"{name}: {len(values)} gia tri, can {want}")
    return np.array([float(v) for v in values], dtype=np.float32).reshape(rows, width)


def bit_equal(a: np.ndarray, b: np.ndarray) -> bool:
    return np.array_equal(a.reshape(-1).view(np.uint32), b.reshape(-1).view(np.uint32))


def main() -> int:
    indices = read_mamba_indices(MAMBA_SAMPLES)
    if indices != EXPECTED_INDICES:
        raise AssertionError(f"uci_index Mamba khac brief:\n  doc: {indices}\n  brief: {EXPECTED_INDICES}")

    X_all = np.loadtxt(X_TEST, dtype=np.float32)
    y_all = np.loadtxt(Y_TEST, dtype=np.int64)
    if X_all.shape != (2947, N_FEAT):
        raise AssertionError(f"X_test shape {X_all.shape}, can (2947, {N_FEAT})")
    if y_all.shape != (2947,):
        raise AssertionError(f"y_test shape {y_all.shape}, can (2947,)")

    samples = X_all[indices]
    if samples.shape != (N_SAMPLES, N_FEAT):
        raise AssertionError(samples.shape)

    with open(C_CSV, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 2947:
        raise AssertionError(f"{C_CSV}: {len(rows)} dong, can 2947")
    if [int(r["sample_index"]) for r in rows] != list(range(2947)):
        raise AssertionError(f"{C_CSV}: sample_index khong lien tuc 0..2946")

    ref_pred = np.array([int(rows[i]["pred"]) for i in indices], dtype=np.int64)
    ref_logits = np.array(
        [[float(rows[i][f"logit{c}"]) for c in range(N_CLASSES)] for i in indices],
        dtype=np.float32,
    )
    if ref_logits.shape != (N_SAMPLES, N_CLASSES):
        raise AssertionError(ref_logits.shape)
    if not np.array_equal(ref_pred, ref_logits.argmax(axis=1)):
        raise AssertionError("pred trong CSV C khong bang argmax(logit)")

    true_label = (y_all[indices] - 1).astype(np.uint8)
    if true_label.min() < 0 or true_label.max() > 5:
        raise AssertionError("nhan that ngoai 0..5")

    ckpt_sha = sha256_file(CKPT)
    weights_sha = sha256_file(WEIGHTS)

    header = [
        "/* 20 real UCI HAR test samples for the MLP control firmware (561 raw",
        " * features, no padding). Indices are read from",
        " * firmware/mambahar-esp32s3/src/uci_samples.h (uci_index), not typed by hand.",
        " *",
        " * Reference logits/predictions: ml/results/mlp_c_logits_test.csv at the same",
        " * sample_index (C host inference of the MLP).",
        " * True labels: data/UCI HAR Dataset/test/y_test.txt, printed for information",
        " * only and never used for inference.",
        f" * Checkpoint: ml/results/mlp_seed42.pt sha256 {ckpt_sha}",
        f" * Weights: firmware/common/mlp_weights.h sha256 {weights_sha}",
        " * Regenerate: .venv-ml\\Scripts\\python ml\\gen_mlp_samples.py",
        " * const -> lives in flash, no RAM cost.",
        " */",
        "#ifndef MLP_SAMPLES_H",
        "#define MLP_SAMPLES_H",
        "",
        "static const int mlp_sample_index[20] = {" + ", ".join(str(v) for v in indices) + "};",
        "static const int mlp_ref_pred[20] = {" + ", ".join(str(v) for v in ref_pred) + "};",
        "static const unsigned char mlp_true_label[20] = {" + ", ".join(str(v) for v in true_label) + "};",
        "",
        "static const float mlp_ref_logits[20][6] = {",
    ]
    for row in ref_logits:
        header.append("    {" + ", ".join(f"{float(v):.9e}" for v in row) + "},")
    header.append("};")
    header.append("")
    header.append(fmt_matrix("mlp_samples", samples, N_FEAT))
    header.append("#endif /* MLP_SAMPLES_H */")
    text = "\n".join(header) + "\n"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")

    back = OUT.read_text(encoding="utf-8")
    got_samples = parse_matrix(back, "mlp_samples", N_SAMPLES, N_FEAT)
    got_logits = parse_matrix(back, "mlp_ref_logits", N_SAMPLES, N_CLASSES)
    if not bit_equal(got_samples, samples):
        raise AssertionError("mlp_samples doc lai khong bit-exact")
    if not bit_equal(got_logits, ref_logits):
        raise AssertionError("mlp_ref_logits doc lai khong bit-exact")

    print(f"OK mlp_samples: {N_SAMPLES} x {N_FEAT} float32 bit-exact")
    print(f"OK mlp_ref_logits: {N_SAMPLES} x {N_CLASSES} float32 bit-exact")
    print(f"indices (tu uci_samples.h): {indices}")
    print(f"checkpoint sha256: {ckpt_sha}")
    print(f"weights sha256: {weights_sha}")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

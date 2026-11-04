#!/usr/bin/env python3
"""Sinh bo mau nhung cho firmware Mamba huan luyen lai tren ESP32-S3.

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\gen_mamba_retrained_samples.py

Doc:
    firmware/mambahar-esp32s3/src/uci_samples.h   (bo mau cong khai: uci_index,
                                                   uci_host_pred, uci_samples)
    data/UCI HAR Dataset/test/X_test.txt          (561 dac trung + 9 so 0)
    ml/results/mamba_retrained/mamba_c_logits_test.csv   (logit C tren PC)
    ml/results/mamba_retrained/mamba_seed42.pt / mamba_weights.h   (chi de lay sha256)

Ghi:
    firmware/mamba-retrained-esp32s3/src/uci_samples.h

Cung ten bien, cung kieu, cung 20 mau nhu header cu; chi logit/du doan tham chieu
doi sang Mamba huan luyen lai. In %.9e (du 9 chu so co nghia cho float32), LF,
khong dong trong thua cuoi file. Script tu doc lai header vua sinh va assert
bit-exact voi du lieu goc va voi uci_samples cua header cu.
"""
import csv
import hashlib
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OLD_HEADER = ROOT / "firmware" / "mambahar-esp32s3" / "src" / "uci_samples.h"
X_TEST = ROOT / "data" / "UCI HAR Dataset" / "test" / "X_test.txt"
C_CSV = ROOT / "ml" / "results" / "mamba_retrained" / "mamba_c_logits_test.csv"
CKPT = ROOT / "ml" / "results" / "mamba_retrained" / "mamba_seed42.pt"
WEIGHTS = ROOT / "ml" / "results" / "mamba_retrained" / "mamba_weights.h"
OUT = ROOT / "firmware" / "mamba-retrained-esp32s3" / "src" / "uci_samples.h"

N_SAMPLES = 20
N_FEAT_RAW = 561
N_PAD = 9
N_FEAT = N_FEAT_RAW + N_PAD  # 570
EXPECTED_INDEX = [79, 80, 81, 128, 133, 134, 109, 110, 111, 31, 33, 34,
                  0, 1, 2, 55, 56, 57, 112, 35]
N_CLASSES = 6

FLOAT_RE = re.compile(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?f")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_old_header(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    m = re.search(r"uci_index\[20\]\s*=\s*\{([^}]*)\};", text)
    if not m:
        raise SystemExit(f"{path}: khong tim thay uci_index")
    index = [int(v) for v in m.group(1).split(",") if v.strip()]

    m = re.search(r"uci_host_pred\[20\]\s*=\s*\{([^}]*)\};", text)
    if not m:
        raise SystemExit(f"{path}: khong tim thay uci_host_pred")
    pred = [int(v) for v in m.group(1).split(",") if v.strip()]

    m = re.search(r"uci_host_logits\[20\]\[6\]\s*=\s*\{(.*?)\n\};", text, re.S)
    if not m:
        raise SystemExit(f"{path}: khong tim thay uci_host_logits")
    values = [np.float32(v[:-1]) for v in FLOAT_RE.findall(m.group(1))]
    if len(values) != N_SAMPLES * N_CLASSES:
        raise SystemExit(f"{path}: uci_host_logits co {len(values)} gia tri")
    logits = np.array(values, dtype=np.float32).reshape(N_SAMPLES, N_CLASSES)

    m = re.search(r"uci_samples\[20\]\[570\]\s*=\s*\{(.*?)\n\};", text, re.S)
    if not m:
        raise SystemExit(f"{path}: khong tim thay uci_samples")
    values = [np.float32(v[:-1]) for v in FLOAT_RE.findall(m.group(1))]
    if len(values) != N_SAMPLES * N_FEAT:
        raise SystemExit(f"{path}: uci_samples co {len(values)} gia tri")
    samples = np.array(values, dtype=np.float32).reshape(N_SAMPLES, N_FEAT)

    return {
        "index": index,
        "pred": pred,
        "logits": logits,
        "samples": samples,
    }


def load_c_reference(path: Path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 2947:
        raise SystemExit(f"{path}: {len(rows)} dong, mong doi 2947")
    header = list(rows[0].keys())
    if header != ["sample_index", "pred"] + [f"logit{c}" for c in range(N_CLASSES)]:
        raise SystemExit(f"{path}: header khong dung: {header}")
    return rows


def fmt_sample_rows(samples: np.ndarray) -> str:
    lines = []
    for s in range(samples.shape[0]):
        lines.append("    {")
        flat = samples[s]
        for start in range(0, flat.size, 10):
            chunk = flat[start:start + 10]
            lines.append("        " + ", ".join(f"{float(v):.9e}f" for v in chunk) + ",")
        lines.append("    },")
    return "\n".join(lines)


def main() -> int:
    old = parse_old_header(OLD_HEADER)
    if old["index"] != EXPECTED_INDEX:
        raise SystemExit(f"uci_index trong header cu la {old['index']}, khong phai danh sach mong doi")
    index = old["index"]

    X_all = np.loadtxt(X_TEST, dtype=np.float32)
    if X_all.shape != (2947, N_FEAT_RAW):
        raise SystemExit(f"{X_TEST}: shape {X_all.shape}")
    raw = X_all[np.array(index, dtype=np.int64)]
    samples = np.concatenate(
        [raw, np.zeros((N_SAMPLES, N_PAD), dtype=np.float32)], axis=1)
    if samples.shape != (N_SAMPLES, N_FEAT):
        raise SystemExit(f"samples: shape {samples.shape}")
    if not np.isfinite(samples).all():
        raise SystemExit("samples co NaN/Inf")

    # Bo mau nhung phai giong het ban cu (cung dau vao bit-exact voi firmware cu).
    if not np.array_equal(samples.view(np.uint32), old["samples"].view(np.uint32)):
        bad = int(np.count_nonzero(
            samples.view(np.uint32) != old["samples"].view(np.uint32)))
        raise SystemExit(f"{bad} gia tri mau khac bit so voi header cu")

    rows = load_c_reference(C_CSV)
    logits = np.zeros((N_SAMPLES, N_CLASSES), dtype=np.float32)
    pred = np.zeros(N_SAMPLES, dtype=np.uint8)
    for s, sample_index in enumerate(index):
        row = rows[sample_index]
        if int(row["sample_index"]) != sample_index:
            raise SystemExit(f"{C_CSV}: dong {sample_index} khong khop")
        logits[s] = [np.float32(row[f"logit{c}"]) for c in range(N_CLASSES)]
        p = int(row["pred"])
        if not 0 <= p < N_CLASSES:
            raise SystemExit(f"{C_CSV}: dong {sample_index} pred={p} ngoai 0..5")
        pred[s] = p
    if not np.isfinite(logits).all():
        raise SystemExit("logit tham chieu co NaN/Inf")
    if not np.array_equal(logits.argmax(axis=1).astype(np.uint8), pred):
        raise SystemExit("pred trong CSV khong bang argmax cua logit")

    ckpt_sha = sha256_file(CKPT)
    weights_sha = sha256_file(WEIGHTS)

    lines = [
        "/* 20 mau UCI HAR test nhung san cho firmware Mamba HUAN LUYEN LAI (seed 42).",
        " * 561 dac trung chuan hoa + 9 so 0 dem = 570 moi mau.",
        " *",
        " * Nguon mau: data/UCI HAR Dataset/test/X_test.txt, dung chi so lay tu",
        " * uci_samples.h cua project firmware/mambahar-esp32s3 (khong go tay):",
        " *   " + ", ".join(str(i) for i in index),
        " * 20x570 gia tri duoc assert bit-exact voi uci_samples trong header cu",
        " * (cung dau vao voi firmware Mamba trong so cong khai).",
        " *",
        " * Logit/du doan tham chieu: ml/results/mamba_retrained/mamba_c_logits_test.csv",
        " * (suy luan C tren PC cua checkpoint huan luyen lai), dung 20 hang chi so tren.",
        " *",
        " * checkpoint: ml/results/mamba_retrained/mamba_seed42.pt",
        f" * sha256 checkpoint: {ckpt_sha}",
        " * trong so: ml/results/mamba_retrained/mamba_weights.h",
        f" * sha256 trong so: {weights_sha}",
        " *",
        " * generated, do not edit - sinh bang ml/gen_mamba_retrained_samples.py",
        " * const -> nam trong flash, khong ton RAM. */",
        "static const int uci_index[20] = {"
        + ", ".join(str(i) for i in index) + "};",
        "static const unsigned char uci_host_pred[20] = {"
        + ", ".join(str(int(p)) for p in pred) + "};",
        "static const float uci_host_logits[20][6] = {",
    ]
    for s in range(N_SAMPLES):
        lines.append("    {" + ", ".join(f"{float(v):.9e}f" for v in logits[s]) + "},")
    lines.append("};")
    lines.append("static const float uci_samples[20][570] = {")
    lines.append(fmt_sample_rows(samples))
    lines.append("};")
    text = "\n".join(lines) + "\n"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    if text.endswith("\n\n"):
        raise SystemExit("header co dong trong thua cuoi file")

    # Doc lai header vua sinh: bit-exact voi du lieu goc va voi bo mau cu.
    back = OUT.read_text(encoding="utf-8")
    m = re.search(r"uci_samples\[20\]\[570\]\s*=\s*\{(.*?)\n\};", back, re.S)
    got = np.array([np.float32(v[:-1]) for v in FLOAT_RE.findall(m.group(1))],
                   dtype=np.float32).reshape(N_SAMPLES, N_FEAT)
    if not np.array_equal(got.view(np.uint32), samples.view(np.uint32)):
        raise SystemExit("doc lai: uci_samples khac bit so voi du lieu goc")
    m = re.search(r"uci_host_logits\[20\]\[6\]\s*=\s*\{(.*?)\n\};", back, re.S)
    got_logits = np.array([np.float32(v[:-1]) for v in FLOAT_RE.findall(m.group(1))],
                          dtype=np.float32).reshape(N_SAMPLES, N_CLASSES)
    if not np.array_equal(got_logits.view(np.uint32), logits.view(np.uint32)):
        raise SystemExit("doc lai: uci_host_logits khac bit so voi CSV")

    print(f"OK uci_samples: {got.size} float32 bit-exact (du lieu goc + header cu)")
    print(f"OK uci_host_logits: {got_logits.size} float32 bit-exact (CSV C)")
    print(f"OK uci_index: {index}")
    print(f"OK uci_host_pred: {', '.join(str(int(p)) for p in pred)}")
    print(f"checkpoint sha256: {ckpt_sha}")
    print(f"trong so sha256: {weights_sha}")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

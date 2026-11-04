#!/usr/bin/env python3
"""Tao firmware/host/logs/uci_train.f32 tu X_train.txt (chi tap train).

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\make_train_f32.py

Cung bo cuc voi firmware/host/uci_har.py to-f32: 561 dac trung + 9 so 0
thanh 570, float32 little-endian, khong header. Khong doc X_test.txt.
Dau ra bi .gitignore chan (*.f32) nen khong commit.
"""
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
X_TRAIN = ROOT / "data" / "UCI HAR Dataset" / "train" / "X_train.txt"
OUT = ROOT / "firmware" / "host" / "logs" / "uci_train.f32"

N_FEAT_RAW = 561
N_PAD = 9
N_FEAT = N_FEAT_RAW + N_PAD
EXPECTED_ROWS = 7352


def main() -> int:
    rows = 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(X_TRAIN, encoding="utf-8") as f, open(OUT, "wb") as g:
        for line in f:
            vals = [float(v) for v in line.split()]
            if len(vals) != N_FEAT_RAW:
                raise SystemExit(
                    f"{X_TRAIN}: line {rows + 1} has {len(vals)} features, want {N_FEAT_RAW}"
                )
            g.write(struct.pack(f"<{N_FEAT}f", *(vals + [0.0] * N_PAD)))
            rows += 1
    if rows != EXPECTED_ROWS:
        raise SystemExit(f"{X_TRAIN}: {rows} rows, expected {EXPECTED_ROWS}")
    size = OUT.stat().st_size
    if size != EXPECTED_ROWS * N_FEAT * 4:
        raise SystemExit(f"{OUT}: {size} bytes, expected {EXPECTED_ROWS * N_FEAT * 4}")
    print(f"wrote {rows} samples ({size} bytes) -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

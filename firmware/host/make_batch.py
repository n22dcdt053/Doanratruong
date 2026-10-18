#!/usr/bin/env python3
"""Build a batch input file for firmware/host: N x 570 raw float32 (little-endian).

Sample 0 = first 570 values of the upstream sample_input.h (the real demo sample).
Samples 1..N-1 = deterministic pseudo-random values (fixed seed) so numeric A/B
runs are repeatable. Real UCI-HAR batches will come from the dataset loader later.
"""
import argparse
import random
import re
import struct
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SAMPLE_H = REPO / "MambaLite-Micro/examples/mambahar-arduino-6/include/sample_input.h"
N_FEAT = 10 * 57


def real_sample():
    vals = [float(v[:-1]) for v in re.findall(r"[-+]?\d+\.\d+(?:[eE][-+]?\d+)?f", SAMPLE_H.read_text())]
    if len(vals) < N_FEAT:
        raise SystemExit(f"{SAMPLE_H}: found only {len(vals)} floats, need {N_FEAT}")
    return vals[:N_FEAT]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out")
    ap.add_argument("count", type=int, help="number of samples (>=1)")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    if a.count < 1:
        raise SystemExit("count must be >= 1")
    rng = random.Random(a.seed)
    with open(a.out, "wb") as f:
        f.write(struct.pack("<570f", *real_sample()))
        for _ in range(a.count - 1):
            f.write(struct.pack("<570f", *(rng.gauss(0.0, 1.0) for _ in range(N_FEAT))))
    print(f"wrote {a.count} samples ({a.count * N_FEAT * 4} bytes) -> {a.out}")


main()

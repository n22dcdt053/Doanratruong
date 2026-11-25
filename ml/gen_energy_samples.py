#!/usr/bin/env python3
"""Chon 60 mau "tap phat trien" cho phep do nang luong (Brief 07, G1) va sinh header nhung.

Chay tu goc repo (Python co numpy):
    python ml/gen_energy_samples.py            # sinh tep + ghi ml/results/energy_samples/ va header
    python ml/gen_energy_samples.py --check    # sinh lai vao thu muc tam, so byte voi tep da co

Quy tac chon (khong xem du doan cua bat ky mo hinh nao):
    - Nguon: cac dong split == val trong ml/split_manifest.csv (khong dung test).
    - Dac trung 561 doc tu data/UCI HAR Dataset/train/X_train.txt, dong = row_index trong manifest.
    - Moi lop 0..5 chon DUNG 10 mau bang numpy.random.default_rng(42), rut khong hoan lai,
      lan luot lop 0 -> 5 tren CUNG mot rng; roi sap tang dan theo row_index (= sample_id train_NNNN).

Logit tham chieu: runner host (WSL, gcc -O2) cho Mamba huan luyen lai
(firmware/host/run_host_retrained.sh) va MLP (firmware/host/run_mlp_host_test.sh) tren dung 60 mau.
Dau vao Mamba = 561 dac trung + 9 so 0 = 570 float32; runner MLP doc cung tep 570 va dung 561 so dau.
"""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "UCI HAR Dataset" / "train" / "X_train.txt"
MANIFEST = ROOT / "ml" / "split_manifest.csv"
OUT_DIR = ROOT / "ml" / "results" / "energy_samples"
HEADER = ROOT / "firmware" / "energy-esp32s3" / "src" / "energy_samples.h"
CKPT_MAMBA = ROOT / "ml" / "results" / "mamba_retrained" / "mamba_seed42.pt"
CKPT_MLP = ROOT / "ml" / "results" / "mlp_seed42.pt"
W_MAMBA = ROOT / "ml" / "results" / "mamba_retrained" / "mamba_weights.h"
W_MLP = ROOT / "firmware" / "common" / "mlp_weights.h"

SEED = 42
PER_CLASS = 10
N_CLASS = 6
N = PER_CLASS * N_CLASS
N_RAW = 561
N_PAD = 9
N_FEAT = N_RAW + N_PAD


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wsl_path(p: Path) -> str:
    s = str(p.resolve()).replace("\\", "/")
    return f"/mnt/{s[0].lower()}{s[2:]}"


def run_wsl(cmd: str) -> str:
    r = subprocess.run(["wsl", "-e", "bash", "-c", cmd], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"WSL that bai (ma {r.returncode}): {cmd}")
    return r.stdout


def select_samples():
    rows = []
    with open(MANIFEST, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["split"] == "val":
                assert r["source_file"] == "train/X_train.txt"
                rows.append({"row": int(r["row_index"]), "sid": r["sample_id"],
                             "subject": int(r["subject_id"]), "label": int(r["label"])})
    assert len(rows) == 1801, len(rows)
    rng = np.random.default_rng(SEED)
    chosen = []
    for c in range(N_CLASS):
        pool = [r for r in rows if r["label"] == c]  # thu tu row_index tang dan
        pick = rng.choice(len(pool), size=PER_CLASS, replace=False)
        chosen.extend(pool[int(i)] for i in pick)
    chosen.sort(key=lambda r: r["row"])
    # --- assert ---
    assert len(chosen) == N
    assert len({r["row"] for r in chosen}) == N, "co mau trung"
    val_rows = {r["row"] for r in rows}
    assert all(r["row"] in val_rows for r in chosen), "mau ngoai tap val"
    for c in range(N_CLASS):
        assert sum(1 for r in chosen if r["label"] == c) == PER_CLASS, f"lop {c} khong du {PER_CLASS}"
    return chosen


def load_features(chosen):
    want = {r["row"] for r in chosen}
    feats = {}
    with open(DATA, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i in want:
                v = np.array([float(t) for t in line.split()], dtype=np.float64)
                assert v.shape == (N_RAW,), (i, v.shape)
                feats[i] = v.astype(np.float32)
    assert set(feats) == want
    return np.stack([feats[r["row"]] for r in chosen])  # (60, 561) float32


def host_logits(x570: np.ndarray, tmp: Path):
    f32 = tmp / "energy_60.f32"
    f32.write_bytes(x570.astype("<f4").tobytes())
    out = {}
    for name, script in (("mamba", "run_host_retrained.sh"), ("mlp", "run_mlp_host_test.sh")):
        csv_out = tmp / f"ref_{name}_raw.csv"
        cmd = (f"cd '{wsl_path(ROOT)}' && bash firmware/host/{script} --batch "
               f"'{wsl_path(f32)}' '{wsl_path(csv_out)}'")
        log = run_wsl(cmd)
        if name == "mamba":
            assert "header ma gcc doc:" in log and "mamba_retrained" in log, log
        pred = np.zeros(N, dtype=np.int64)
        lg = np.zeros((N, 6), dtype=np.float32)
        with open(csv_out, encoding="utf-8") as f:
            rd = csv.reader(f)
            next(rd)
            n = 0
            for row in rd:
                assert int(row[0]) == n
                pred[n] = int(row[1])
                lg[n] = np.array([float(t) for t in row[2:8]], dtype=np.float32)
                n += 1
        assert n == N, (name, n)
        assert (pred >= 0).all(), f"{name}: co du doan khong hop le"
        out[name] = (pred, lg)
    return out


def fmt(v) -> str:
    return "%.9e" % float(v)


def build(out_dir: Path, header_path: Path):
    chosen = select_samples()
    x561 = load_features(chosen)
    x570 = np.concatenate([x561, np.zeros((N, N_PAD), dtype=np.float32)], axis=1)
    with tempfile.TemporaryDirectory() as td:
        ref = host_logits(x570, Path(td))

    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}

    def write(name, text):
        p = out_dir / name
        p.write_text(text, encoding="utf-8", newline="\n")
        files[name] = p

    lines = ["idx,sample_id,subject_id,label"]
    for i, r in enumerate(chosen):
        lines.append(f"{i},{r['sid']},{r['subject']},{r['label']}")
    write("energy_samples.csv", "\n".join(lines) + "\n")
    for name in ("mamba", "mlp"):
        pred, lg = ref[name]
        lines = ["idx,pred,logit0,logit1,logit2,logit3,logit4,logit5"]
        for i in range(N):
            lines.append(f"{i},{int(pred[i])}," + ",".join(fmt(v) for v in lg[i]))
        write(f"ref_{name}_logits.csv", "\n".join(lines) + "\n")

    sha_ckpt_mamba = sha256_file(CKPT_MAMBA)
    sha_ckpt_mlp = sha256_file(CKPT_MLP)
    sha_w_mamba = sha256_file(W_MAMBA)
    sha_w_mlp = sha256_file(W_MLP)

    # --- header ---
    h = []
    h.append("/* 60 mau UCI HAR \"tap phat trien\" (split == val) cho firmware do nang luong (Brief 07).")
    h.append(" * 10 mau moi lop (6 lop), chon bang numpy.random.default_rng(%d), rut khong hoan lai trong tung lop," % SEED)
    h.append(" * sap tang dan theo sample_id. KHONG chon theo du doan cua mo hinh nao. Khong dung test.")
    h.append(" * Nguon dac trung: data/UCI HAR Dataset/train/X_train.txt (dong = row_index trong ml/split_manifest.csv);")
    h.append(" * energy_sample_id[i] = row_index (sample_id 'train_NNNN' <-> NNNN).")
    h.append(" * Dau vao Mamba = 561 dac trung + 9 so 0 (570) do main.c ghep luc chay; MLP dung 561 so dau.")
    h.append(" * Logit/du doan tham chieu: runner host gcc -O2 (WSL) tren dung 60 mau nay:")
    h.append(" *   Mamba huan luyen lai: ml/results/mamba_retrained/mamba_seed42.pt")
    h.append(" *     sha256 checkpoint: %s" % sha_ckpt_mamba)
    h.append(" *     sha256 trong so  : %s (mamba_weights.h)" % sha_w_mamba)
    h.append(" *   MLP 561-64-6: ml/results/mlp_seed42.pt")
    h.append(" *     sha256 checkpoint: %s" % sha_ckpt_mlp)
    h.append(" *     sha256 trong so  : %s (firmware/common/mlp_weights.h)" % sha_w_mlp)
    h.append(" * generated, do not edit - sinh bang ml/gen_energy_samples.py")
    h.append(" * const -> nam trong flash, khong ton RAM. */")
    h.append("#pragma once")
    h.append("#include <stdint.h>")
    h.append("")
    h.append("#define ENERGY_N_SAMPLES %d" % N)
    h.append("#define ENERGY_N_FEAT 561")
    h.append("")
    h.append("static const uint32_t energy_sample_id[%d] = {%s};" % (N, ", ".join(str(r["row"]) for r in chosen)))
    h.append("static const uint8_t energy_label[%d] = {%s};" % (N, ", ".join(str(r["label"]) for r in chosen)))
    h.append("static const uint8_t energy_ref_mamba_pred[%d] = {%s};" % (N, ", ".join(str(int(v)) for v in ref["mamba"][0])))
    h.append("static const uint8_t energy_ref_mlp_pred[%d] = {%s};" % (N, ", ".join(str(int(v)) for v in ref["mlp"][0])))
    for nm, key in (("energy_ref_mamba", "mamba"), ("energy_ref_mlp", "mlp")):
        h.append("static const float %s[%d][6] = {" % (nm, N))
        for i in range(N):
            h.append("    {" + ", ".join(fmt(v) + "f" for v in ref[key][1][i]) + "},")
        h.append("};")
    h.append("static const float energy_features[%d][%d] = {" % (N, N_RAW))
    for i in range(N):
        h.append("    {" + ", ".join(fmt(v) + "f" for v in x561[i]) + "},")
    h.append("};")
    header_path.parent.mkdir(parents=True, exist_ok=True)
    header_path.write_text("\n".join(h) + "\n", encoding="utf-8", newline="\n")
    files["energy_samples.h"] = header_path

    # --- assert dac trung trong header khop bit-exact voi du lieu goc ---
    text = header_path.read_text(encoding="utf-8")
    blk = text.split("energy_features[%d][%d] = {" % (N, N_RAW), 1)[1].split("\n};", 1)[0]
    parsed = [[np.float32(float(t.rstrip("f"))) for t in ln.strip().strip("{},").split(", ")]
              for ln in blk.strip().split("\n")]
    parsed = np.array(parsed, dtype=np.float32)
    assert parsed.shape == (N, N_RAW)
    assert parsed.tobytes() == x561.tobytes(), "dac trung header khong khop bit-exact voi X_train.txt"

    manifest = {
        "brief": "07-G1",
        "seed": SEED,
        "rng": "numpy.random.default_rng",
        "numpy_version_note": "ket qua rng.choice phu thuoc phien ban numpy; da chay voi numpy " + np.__version__,
        "per_class": PER_CLASS,
        "source_split": "val (ml/split_manifest.csv), khong dung test",
        "n_samples": N,
        "split_manifest_sha256": sha256_file(MANIFEST),
        "checkpoint_sha256": {"mamba_retrained": sha_ckpt_mamba, "mlp": sha_ckpt_mlp},
        "weights_sha256": {"mamba_weights.h": sha_w_mamba, "mlp_weights.h": sha_w_mlp},
        "files_sha256": {k: sha256_file(v) for k, v in sorted(files.items())},
    }
    write("energy_samples_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return {k: v.read_bytes() for k, v in files.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="sinh lai vao thu muc tam va so byte voi tep da co")
    a = ap.parse_args()
    if not a.check:
        build(OUT_DIR, HEADER)
        print(f"ghi {OUT_DIR} va {HEADER}")
        return 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        new = build(td / "energy_samples", td / "energy_samples.h")
    old = {n: (OUT_DIR / n if n != "energy_samples.h" else HEADER).read_bytes() for n in new}
    bad = [n for n in new if new[n] != old[n]]
    for n in sorted(new):
        print(("KHAC  " if n in bad else "GIONG ") + n + " " + hashlib.sha256(new[n]).hexdigest())
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

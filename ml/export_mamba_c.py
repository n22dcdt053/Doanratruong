#!/usr/bin/env python3
"""Xuat trong so Mamba huan luyen lai tu checkpoint PyTorch sang header C.

Chay tu goc repo (sau khi da co ml/results/mamba_retrained/mamba_seed42.pt):
    .venv-ml\\Scripts\\python ml\\export_mamba_c.py

Dau ra mac dinh: ml/results/mamba_retrained/mamba_weights.h
Cung ten mang, cung #define va thu tu voi mamba_weights.h cong khai (de thay the
duoc - xem firmware/host/run_host_retrained.sh), chi khac dinh dang so:
in %.9e (10 chu so co nghia) thay vi %.8f cua upstream (%.8f lam mat bit float32).
Script doc lai header vua sinh va assert bit-exact voi tensor trong checkpoint.
"""
import argparse
import datetime
import hashlib
import re
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CKPT = ROOT / "ml" / "results" / "mamba_retrained" / "mamba_seed42.pt"
DEFAULT_OUT = ROOT / "ml" / "results" / "mamba_retrained" / "mamba_weights.h"

# #define khong doi, cung thu tu voi mamba_weights.h cong khai.
DEFINES = [
    ("mamba_d_model", "64"),
    ("mamba_d_state", "16"),
    ("mamba_d_conv", "4"),
    ("mamba_expand", "2"),
    ("mamba_dt_min", "0.001"),
    ("mamba_dt_max", "0.1"),
    ("mamba_dt_scale", "1.0"),
    ("mamba_dt_rank", "4"),
]

# (ten mang C, ten state_dict, kich thuoc khai bao, so phan tu, defines di kem)
ARRAYS = [
    ("linear_in_weight", "linear_in.weight", "3648", 3648,
     [("linear_in_weight_rows", "64"), ("linear_in_weight_cols", "57")]),
    ("linear_in_bias", "linear_in.bias", "64", 64,
     [("linear_in_bias_size", "64")]),
    ("mamba_A_log", "mamba.A_log", "2048", 2048,
     [("mamba_A_log_rows", "128"), ("mamba_A_log_cols", "16")]),
    ("mamba_D", "mamba.D", "128", 128,
     [("mamba_D_size", "128")]),
    ("mamba_in_proj_weight", "mamba.in_proj.weight", "16384", 16384,
     [("mamba_in_proj_weight_rows", "256"), ("mamba_in_proj_weight_cols", "64")]),
    ("mamba_conv1d_weight", "mamba.conv1d.weight", "512", 512,
     [("mamba_conv1d_weight_rows", "128"), ("mamba_conv1d_weight_cols", "4")]),
    ("mamba_conv1d_bias", "mamba.conv1d.bias", "128", 128,
     [("mamba_conv1d_bias_size", "128")]),
    ("mamba_x_proj_weight", "mamba.x_proj.weight", "4608", 4608,
     [("mamba_x_proj_weight_rows", "36"), ("mamba_x_proj_weight_cols", "128")]),
    ("mamba_dt_proj_weight", "mamba.dt_proj.weight", "512", 512,
     [("mamba_dt_proj_weight_rows", "128"), ("mamba_dt_proj_weight_cols", "4")]),
    ("mamba_dt_proj_bias", "mamba.dt_proj.bias", "128", 128,
     [("mamba_dt_proj_bias_size", "128")]),
    ("mamba_out_proj_weight", "mamba.out_proj.weight", "8192", 8192,
     [("mamba_out_proj_weight_rows", "64"), ("mamba_out_proj_weight_cols", "128")]),
    ("classifier_weight", "classifier.weight", "384", 384,
     [("classifier_weight_rows", "6"), ("classifier_weight_cols", "64")]),
    ("classifier_bias", "classifier.bias", "6", 6,
     [("classifier_bias_size", "6")]),
]

VALUE_RE = re.compile(r"[-+]?\d+\.\d{9}e[-+]\d{2,3}f")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt_array(name: str, flat: np.ndarray, size_expr: str) -> str:
    lines = [f"const float {name}[{size_expr}] = {{"]
    for start in range(0, flat.size, 8):
        chunk = flat[start:start + 8]
        lines.append("    " + ", ".join(f"{float(v):.9e}f" for v in chunk) + ",")
    lines.append("};")
    return "\n".join(lines)


def parse_array(text: str, name: str, count: int) -> np.ndarray:
    m = re.search(rf"const float {name}\[\d+\] = \{{(.*?)\}};", text, re.S)
    if not m:
        raise AssertionError(f"khong tim thay mang {name} trong header")
    values = VALUE_RE.findall(m.group(1))
    if len(values) != count:
        raise AssertionError(f"{name}: {len(values)} gia tri, khai bao {count}")
    return np.array([np.float32(v[:-1]) for v in values], dtype=np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default=str(DEFAULT_CKPT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    ckpt = Path(args.checkpoint)
    out = Path(args.out)
    state = torch.load(ckpt, map_location="cpu", weights_only=True)

    tensors = {}
    for c_name, sd_name, _, count, _ in ARRAYS:
        tensor = state[sd_name].detach().cpu().numpy().astype(np.float32)
        flat = tensor.reshape(-1)
        assert flat.size == count, (c_name, flat.size, count)
        tensors[c_name] = flat
    total = sum(t.size for t in tensors.values())
    assert total == 36742, total

    ckpt_sha = sha256_file(ckpt)
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    lines = [
        "/* mamba_weights.h - trong so Mamba huan luyen lai (UCI HAR, seed 42).",
        " *",
        " * Sinh tu dong boi ml/export_mamba_c.py tu checkpoint PyTorch.",
        f" * checkpoint: {ckpt.relative_to(ROOT).as_posix()}",
        f" * sha256 checkpoint: {ckpt_sha}",
        f" * ngay xuat (UTC): {today}",
        " * generated, do not edit.",
        " *",
        " * Cung ten mang, cung #define va thu tu voi mamba_weights.h cong khai, nhung",
        " * in %.9e (10 chu so co nghia) thay vi %.8f cua upstream: %.8f lam mat bit float32.",
        " */",
        "#ifndef MAMBA_WEIGHTS_H",
        "#define MAMBA_WEIGHTS_H",
        "",
    ]
    lines += [f"#define {name} {value}" for name, value in DEFINES]
    lines.append("")
    for c_name, _, size_expr, _, array_defines in ARRAYS:
        lines += [f"#define {name} {value}" for name, value in array_defines]
        lines.append(fmt_array(c_name, tensors[c_name], size_expr))
        lines.append("")
    lines.append("#endif // MAMBA_WEIGHTS_H")
    text = "\n".join(lines) + "\n"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")
    assert not text.endswith("\n\n"), "header co dong trong thua cuoi file"

    back = out.read_text(encoding="utf-8")
    for c_name, _, _, count, _ in ARRAYS:
        got = parse_array(back, c_name, count)
        want = tensors[c_name]
        if not np.array_equal(got.view(np.uint32), want.view(np.uint32)):
            bad = int(np.count_nonzero(got.view(np.uint32) != want.view(np.uint32)))
            raise AssertionError(f"{c_name}: {bad} gia tri khac bit sau khi doc lai")
        print(f"OK {c_name}: {got.size} float32 bit-exact")

    print(f"tong tham so: {total}")
    print(f"checkpoint sha256: {ckpt_sha}")
    print(f"wrote {out.relative_to(ROOT).as_posix()} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

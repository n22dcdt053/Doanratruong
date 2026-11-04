#!/usr/bin/env python3
"""Nap mamba_weights.h cong khai thanh state_dict PyTorch (phan tich van ban).

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\load_public_weights.py

Khong sua file header. Moi mang duoc doc theo dung so phan tu trong khai bao
`const float <ten>[N]`, parse float32 (hau to f), reshape theo cac #define
*_rows/_cols hoac *_size, roi doi chieu tung ten/kich thuoc voi MambaHAR.
"""
import argparse
import hashlib
import re
from collections import OrderedDict
from pathlib import Path

import numpy as np
import torch

from mamba_torch import MambaHAR

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HEADER = (
    ROOT
    / "MambaLite-Micro"
    / "examples"
    / "mambahar-arduino-6"
    / "include"
    / "mamba_weights.h"
)

# (mang C, ten state_dict, kieu reshape, khoa kich thuoc)
ARRAY_MAP = [
    ("linear_in_weight", "linear_in.weight", "rows_cols", ("linear_in_weight_rows", "linear_in_weight_cols")),
    ("linear_in_bias", "linear_in.bias", "size", ("linear_in_bias_size",)),
    ("mamba_A_log", "mamba.A_log", "rows_cols", ("mamba_A_log_rows", "mamba_A_log_cols")),
    ("mamba_D", "mamba.D", "size", ("mamba_D_size",)),
    ("mamba_in_proj_weight", "mamba.in_proj.weight", "rows_cols", ("mamba_in_proj_weight_rows", "mamba_in_proj_weight_cols")),
    ("mamba_conv1d_weight", "mamba.conv1d.weight", "conv", ("mamba_conv1d_weight_rows", "mamba_conv1d_weight_cols")),
    ("mamba_conv1d_bias", "mamba.conv1d.bias", "size", ("mamba_conv1d_bias_size",)),
    ("mamba_x_proj_weight", "mamba.x_proj.weight", "rows_cols", ("mamba_x_proj_weight_rows", "mamba_x_proj_weight_cols")),
    ("mamba_dt_proj_weight", "mamba.dt_proj.weight", "rows_cols", ("mamba_dt_proj_weight_rows", "mamba_dt_proj_weight_cols")),
    ("mamba_dt_proj_bias", "mamba.dt_proj.bias", "size", ("mamba_dt_proj_bias_size",)),
    ("mamba_out_proj_weight", "mamba.out_proj.weight", "rows_cols", ("mamba_out_proj_weight_rows", "mamba_out_proj_weight_cols")),
    ("classifier_weight", "classifier.weight", "rows_cols", ("classifier_weight_rows", "classifier_weight_cols")),
    ("classifier_bias", "classifier.bias", "size", ("classifier_bias_size",)),
]

ARRAY_RE = re.compile(r"const\s+float\s+(\w+)\s*\[\s*(\d+)\s*\]\s*=\s*\{(.*?)\}\s*;", re.S)
DEFINE_RE = re.compile(r"^#define\s+(\w+)\s+([0-9]+)\s*$", re.M)
NUMBER_RE = re.compile(r"^[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?f$")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_defines(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for name, value in DEFINE_RE.findall(text):
        out[name] = int(value)
    return out


def parse_arrays(text: str) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for name, count_s, body in ARRAY_RE.findall(text):
        count = int(count_s)
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
        body = re.sub(r"//[^\n]*", "", body)
        tokens = [t.strip() for t in body.split(",") if t.strip()]
        if len(tokens) != count:
            raise ValueError(f"{name}: {len(tokens)} values, header declares {count}")
        values = []
        for tok in tokens:
            if not NUMBER_RE.match(tok):
                raise ValueError(f"{name}: unexpected token {tok!r}")
            values.append(np.float32(tok[:-1]))
        arrays[name] = np.asarray(values, dtype=np.float32)
    return arrays


def build_state_dict(header: Path) -> "OrderedDict[str, torch.Tensor]":
    text = header.read_text(encoding="utf-8")
    defines = parse_defines(text)
    arrays = parse_arrays(text)
    missing = [name for name, *_ in ARRAY_MAP if name not in arrays]
    if missing:
        raise ValueError(f"missing arrays in {header}: {missing}")

    state: "OrderedDict[str, torch.Tensor]" = OrderedDict()
    for c_name, torch_name, kind, size_keys in ARRAY_MAP:
        missing_keys = [k for k in size_keys if k not in defines]
        if missing_keys:
            raise ValueError(f"missing defines for {c_name}: {missing_keys}")
        dims = tuple(defines[k] for k in size_keys)
        count = int(np.prod(dims))
        flat = arrays[c_name]
        if flat.size != count:
            raise ValueError(f"{c_name}: {flat.size} values, defines want {count}")
        tensor = torch.from_numpy(flat.copy()).reshape(dims)
        if kind == "conv":
            tensor = tensor.view(dims[0], 1, dims[1])
        state[torch_name] = tensor
    return state


def load_public_weights(model: torch.nn.Module, header: Path = DEFAULT_HEADER) -> None:
    state = build_state_dict(header)
    model_state = model.state_dict()
    missing = sorted(set(model_state) - set(state))
    unexpected = sorted(set(state) - set(model_state))
    if missing or unexpected:
        raise KeyError(f"state_dict key mismatch: missing={missing}, unexpected={unexpected}")
    for name, tensor in state.items():
        if tuple(tensor.shape) != tuple(model_state[name].shape):
            raise ValueError(
                f"{name}: header gives {tuple(tensor.shape)}, model wants {tuple(model_state[name].shape)}"
            )
    model.load_state_dict(state, strict=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--header", type=Path, default=DEFAULT_HEADER)
    args = ap.parse_args()

    header = args.header.resolve()
    state = build_state_dict(header)
    print(f"header: {header}")
    print(f"sha256: {sha256_file(header)}")
    model = MambaHAR()
    model.load_state_dict(state, strict=False)
    model_state = MambaHAR().state_dict()
    for name, tensor in state.items():
        print(f"{name}: {tuple(tensor.shape)} values={tensor.numel()}")
    if set(state) != set(model_state):
        raise SystemExit("state_dict keys do not match MambaHAR")
    for name, tensor in state.items():
        if tuple(tensor.shape) != tuple(model_state[name].shape):
            raise SystemExit(
                f"{name}: {tuple(tensor.shape)} != model {tuple(model_state[name].shape)}"
            )
    print(f"all {len(state)} tensors match MambaHAR shapes ({sum(t.numel() for t in state.values())} params)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

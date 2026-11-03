#!/usr/bin/env python3
"""Xuat trong so MLP tu checkpoint PyTorch sang header C.

Chay tu goc repo (sau khi da co ml/results/mlp_seed42.pt):
    .venv-ml\\Scripts\\python ml\\export_mlp_c.py

Dau ra mac dinh: firmware/common/mlp_weights.h
Moi float32 duoc in bang %.9e de phuc hoi dung bit; script doc lai header vua
sinh va assert bit-exact voi tensor trong checkpoint.
"""
import argparse
import datetime
import hashlib
import re
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CKPT = ROOT / "ml" / "results" / "mlp_seed42.pt"
DEFAULT_OUT = ROOT / "firmware" / "common" / "mlp_weights.h"

MLP_IN = 561
MLP_HID = 64
MLP_OUT = 6

ARRAYS = [
    ("mlp_w1", (MLP_HID, MLP_IN), "64 * 561"),
    ("mlp_b1", (MLP_HID,), "64"),
    ("mlp_w2", (MLP_OUT, MLP_HID), "6 * 64"),
    ("mlp_b2", (MLP_OUT,), "6"),
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt_array(name: str, arr: np.ndarray, size_expr: str) -> str:
    flat = arr.reshape(-1)
    lines = [f"static const float {name}[{size_expr}] = {{"]
    for start in range(0, flat.size, 8):
        chunk = flat[start:start + 8]
        lines.append("    " + ", ".join(f"{float(v):.9e}" for v in chunk) + ",")
    lines.append("};")
    return "\n".join(lines)


def element_count(expr: str) -> int:
    count = 1
    for part in expr.split("*"):
        count *= int(part.strip())
    return count


def parse_array(text: str, name: str) -> np.ndarray:
    m = re.search(rf"static const float {name}\[([^\]]+)\] = \{{(.*?)\}};", text, re.S)
    if not m:
        raise AssertionError(f"khong tim thay mang {name} trong header")
    count = element_count(m.group(1))
    values = re.findall(r"[-+]?\d+\.\d{9}e[-+]\d{2,3}", m.group(2))
    if len(values) != count:
        raise AssertionError(f"{name}: {len(values)} gia tri, khai bao {count}")
    return np.array([float(v) for v in values], dtype=np.float32)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", default=str(DEFAULT_CKPT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    ckpt = Path(args.checkpoint)
    out = Path(args.out)
    state = torch.load(ckpt, map_location="cpu", weights_only=True)

    tensors = {
        "mlp_w1": state["0.weight"].detach().cpu().numpy().astype(np.float32),
        "mlp_b1": state["0.bias"].detach().cpu().numpy().astype(np.float32),
        "mlp_w2": state["2.weight"].detach().cpu().numpy().astype(np.float32),
        "mlp_b2": state["2.bias"].detach().cpu().numpy().astype(np.float32),
    }
    for name, shape, _ in ARRAYS:
        assert tensors[name].shape == shape, (name, tensors[name].shape, shape)

    ckpt_sha = sha256_file(ckpt)
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    header = [
        "/* mlp_weights.h — trong so MLP 561-64-6 xuat tu checkpoint PyTorch.",
        " *",
        f" * checkpoint: {ckpt.relative_to(ROOT).as_posix()}",
        f" * sha256 checkpoint: {ckpt_sha}",
        f" * ngay xuat (UTC): {today}",
        " * generated, do not edit.",
        " *",
        " * Layout: mlp_w1[out][in] (64x561), mlp_w2[out][in] (6x64); float32.",
        " */",
        "#ifndef MLP_WEIGHTS_H",
        "#define MLP_WEIGHTS_H",
        "",
        f"#define MLP_IN {MLP_IN}",
        f"#define MLP_HID {MLP_HID}",
        f"#define MLP_OUT {MLP_OUT}",
        "",
    ]
    body = []
    for name, _, size_expr in ARRAYS:
        body.append(fmt_array(name, tensors[name], size_expr))
        body.append("")

    footer = ["#endif /* MLP_WEIGHTS_H */", ""]
    text = "\n".join(header + body + footer) + "\n"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8", newline="\n")

    # Doc lai header vua sinh va kiem bit-exact.
    back = out.read_text(encoding="utf-8")
    for name, _, _ in ARRAYS:
        got = parse_array(back, name)
        want = tensors[name].reshape(-1)
        assert got.shape == want.shape, (name, got.shape, want.shape)
        if not np.array_equal(got.view(np.uint32), want.view(np.uint32)):
            bad = int(np.count_nonzero(got.view(np.uint32) != want.view(np.uint32)))
            raise AssertionError(f"{name}: {bad} gia tri khac bit sau khi doc lai")
        print(f"OK {name}: {got.size} float32 bit-exact")

    print(f"checkpoint sha256: {ckpt_sha}")
    print(f"wrote {out.relative_to(ROOT).as_posix()} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

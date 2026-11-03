#!/usr/bin/env python3
"""Dem tham so Mamba (mamba_weights.h) va MLP (mlp_weights.h), ghi bao cao kich thuoc.

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\model_size.py

Dau ra: ml/results/model_size_comparison.md
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAMBA_H = ROOT / "MambaLite-Micro" / "examples" / "mambahar-arduino-6" / "include" / "mamba_weights.h"
MLP_H = ROOT / "firmware" / "common" / "mlp_weights.h"
OUT = ROOT / "ml" / "results" / "model_size_comparison.md"

NUM = re.compile(r"[-+]?\d+\.\d+(?:[eE][-+]?\d+)?|[-+]?\d+")


def arrays_in(header: Path):
    text = header.read_text(encoding="utf-8", errors="replace")
    found = []
    for m in re.finditer(r"(?:static\s+)?const\s+float\s+(\w+)\s*\[\s*([^\]]+)\s*\]\s*=\s*\{(.*?)\};",
                         text, re.S):
        name = m.group(1)
        expr = m.group(2)
        declared = 1
        for part in expr.split("*"):
            declared *= int(part.strip())
        body = re.sub(r"/\*.*?\*/|//[^\n]*", "", m.group(3), flags=re.S)
        counted = len(NUM.findall(body))
        found.append((name, declared, counted))
    return found


def main() -> int:
    mamba = arrays_in(MAMBA_H)
    mlp = arrays_in(MLP_H)

    assert mamba, "khong doc duoc mang nao trong mamba_weights.h"
    assert mlp, "khong doc duoc mang nao trong mlp_weights.h"
    for name, declared, counted in mamba + mlp:
        assert declared == counted, f"{name}: khai bao {declared}, dem {counted}"

    mamba_params = sum(d for _, d, _ in mamba)
    mlp_params = sum(d for _, d, _ in mlp)
    assert mlp_params == 561 * 64 + 64 + 64 * 6 + 6, mlp_params
    mlp_macs = 561 * 64 + 64 * 6

    lines = []
    lines.append("# Kich thuoc mo hinh: Mamba va MLP")
    lines.append("")
    lines.append("So lieu dem bang `ml/model_size.py` tren cac mang `float` da khai bao trong header.")
    lines.append("")
    lines.append("| Mo hinh | Tham so | Byte (FP32) | Ghi chu |")
    lines.append("|---|---|---|---|")
    lines.append(f"| Mamba (mamba_weights.h) | {mamba_params:,} | {mamba_params * 4:,} | tong cac mang float |")
    lines.append(f"| MLP 561-64-6 (mlp_weights.h) | {mlp_params:,} | {mlp_params * 4:,} | 561*64 + 64 + 64*6 + 6 |")
    lines.append(f"| Chenh lech (Mamba - MLP) | {mamba_params - mlp_params:,} | {(mamba_params - mlp_params) * 4:,} | |")
    lines.append("")
    lines.append(f"So phep nhan-cong moi mau cua MLP: {mlp_macs:,} = 561*64 + 64*6 (chua tinh cong bias).")
    lines.append("")
    lines.append("## Cach dem")
    lines.append("")
    lines.append("- Mamba: doc `MambaLite-Micro/examples/mambahar-arduino-6/include/mamba_weights.h`,")
    lines.append("  tim cac khai bao `const float <ten>[<so chieu>] = { ... };`, cong so phan tu khai bao")
    lines.append("  va doi chieu voi so token so trong dau ngoac (khong co chenh lech).")
    lines.append("- MLP: doc `firmware/common/mlp_weights.h` (sinh tu checkpoint), cung cach dem.")
    lines.append("- Byte = so tham so x 4 (float32). Khong tinh header, padding hay metadata file `.pt`.")
    lines.append("")
    lines.append("## Chi tiet mang Mamba")
    lines.append("")
    lines.append("| Mang | So phan tu |")
    lines.append("|---|---|")
    for name, declared, _ in mamba:
        lines.append(f"| `{name}` | {declared:,} |")
    lines.append("")
    lines.append("## Chi tiet mang MLP")
    lines.append("")
    lines.append("| Mang | So phan tu |")
    lines.append("|---|---|")
    for name, declared, _ in mlp:
        lines.append(f"| `{name}` | {declared:,} |")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"mamba_params={mamba_params}")
    print(f"mlp_params={mlp_params}")
    print(f"mlp_macs={mlp_macs}")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

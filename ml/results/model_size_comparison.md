# Kich thuoc mo hinh: Mamba va MLP

So lieu dem bang `ml/model_size.py` tren cac mang `float` da khai bao trong header.

| Mo hinh | Tham so | Byte (FP32) | Ghi chu |
|---|---|---|---|
| Mamba (mamba_weights.h) | 36,742 | 146,968 | tong cac mang float |
| MLP 561-64-6 (mlp_weights.h) | 36,358 | 145,432 | 561*64 + 64 + 64*6 + 6 |
| Chenh lech (Mamba - MLP) | 384 | 1,536 | |

So phep nhan-cong moi mau cua MLP: 36,288 = 561*64 + 64*6 (chua tinh cong bias).

## Cach dem

- Mamba: doc `MambaLite-Micro/examples/mambahar-arduino-6/include/mamba_weights.h`,
  tim cac khai bao `const float <ten>[<so chieu>] = { ... };`, cong so phan tu khai bao
  va doi chieu voi so token so trong dau ngoac (khong co chenh lech).
- MLP: doc `firmware/common/mlp_weights.h` (sinh tu checkpoint), cung cach dem.
- Byte = so tham so x 4 (float32). Khong tinh header, padding hay metadata file `.pt`.

## Chi tiet mang Mamba

| Mang | So phan tu |
|---|---|
| `linear_in_weight` | 3,648 |
| `linear_in_bias` | 64 |
| `mamba_A_log` | 2,048 |
| `mamba_D` | 128 |
| `mamba_in_proj_weight` | 16,384 |
| `mamba_conv1d_weight` | 512 |
| `mamba_conv1d_bias` | 128 |
| `mamba_x_proj_weight` | 4,608 |
| `mamba_dt_proj_weight` | 512 |
| `mamba_dt_proj_bias` | 128 |
| `mamba_out_proj_weight` | 8,192 |
| `classifier_weight` | 384 |
| `classifier_bias` | 6 |

## Chi tiet mang MLP

| Mang | So phan tu |
|---|---|
| `mlp_w1` | 35,904 |
| `mlp_b1` | 64 |
| `mlp_w2` | 384 |
| `mlp_b2` | 6 |

#!/usr/bin/env python3
"""Mamba HAR bang PyTorch thuan, khop firmware/common/mamba.c va mambahar.c.

Chay tren CPU, khong dung mamba_ssm/CUDA. Day la dac ta duy nhat:
  - linear_in: y = x @ W^T + b                    (mambahar.c)
  - in_proj:   xz = h @ W^T, cat doi lay x, z     (mamba.c)
  - conv1d:    depthwise, kernel 4, pad trai 3, SiLU
  - x_proj:    dt (4) | B (16) | C (16)
  - dt_proj:   dt @ W^T + b, softplus = log(1 + exp(x)) (khong threshold)
  - A = -exp(A_log); quet tuan tu h = exp(dt*A)*h + dt*B*u; y = C*h
  - y = (y + u*D) * silu(z); out_proj; mean-pool theo thoi gian; classifier

Trang thai h reset cho tung mau (moi lan forward khoi tao h = 0).
Ten tham so state_dict anh xa 1-1 sang mang C trong mamba_weights.h.
"""
import math

import torch
import torch.nn.functional as F
from torch import nn

D_MODEL = 64
D_STATE = 16
D_CONV = 4
EXPAND = 2
D_INNER = D_MODEL * EXPAND
DT_RANK = 4
N_FEAT = 57
N_TIME = 10
N_CLASSES = 6

DT_MIN = 0.001
DT_MAX = 0.1
DT_SCALE = 1.0
DT_INIT_FLOOR = 1e-4


def softplus_c(x: torch.Tensor) -> torch.Tensor:
    """log(1 + exp(x)) nhu ham softplus() trong mamba.c (khong threshold)."""
    return torch.log(1.0 + torch.exp(x))


def init_dt_proj_bias(d_inner: int, generator: torch.Generator | None = None) -> torch.Tensor:
    """softplus^-1(dt), dt ~ logUniform(dt_min, dt_max), san DT_INIT_FLOOR.

    Cong thuc mac dinh cua Mamba: dt = exp(U*[log(dt_max)-log(dt_min)] + log(dt_min)),
    clamp san, roi inv_dt = dt + log(-expm1(-dt)).
    """
    u = torch.rand(d_inner, generator=generator)
    dt = torch.exp(u * (math.log(DT_MAX) - math.log(DT_MIN)) + math.log(DT_MIN))
    dt = torch.clamp(dt, min=max(DT_MIN, DT_INIT_FLOOR))
    return dt + torch.log(-torch.expm1(-dt))


class MambaBlock(nn.Module):
    """Mot khoi Mamba selective-scan, dung cho T=10 va batch doc lap."""

    def __init__(
        self,
        d_model: int = D_MODEL,
        d_state: int = D_STATE,
        d_conv: int = D_CONV,
        expand: int = EXPAND,
        dt_rank: int = DT_RANK,
        dt_scale: float = DT_SCALE,
        generator: torch.Generator | None = None,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state
        self.d_conv = d_conv
        self.expand = expand
        self.d_inner = expand * d_model
        self.dt_rank = dt_rank

        # Khoi tao mac dinh PyTorch (Linear/Conv1d), sau do thay A_log, D, dt_proj.
        self.in_proj = nn.Linear(d_model, 2 * self.d_inner, bias=False)
        self.conv1d = nn.Conv1d(
            self.d_inner,
            self.d_inner,
            kernel_size=d_conv,
            groups=self.d_inner,
            bias=True,
            padding=d_conv - 1,
        )
        self.x_proj = nn.Linear(self.d_inner, dt_rank + 2 * d_state, bias=False)
        self.dt_proj = nn.Linear(dt_rank, self.d_inner, bias=True)
        self.out_proj = nn.Linear(self.d_inner, d_model, bias=False)

        # A_log[d, n] = log(n + 1), lap theo d_inner; D = 1.
        a = torch.arange(1, d_state + 1, dtype=torch.float32).repeat(self.d_inner, 1)
        self.A_log = nn.Parameter(torch.log(a))
        self.D = nn.Parameter(torch.ones(self.d_inner))

        bound = dt_rank ** -0.5 * dt_scale
        nn.init.uniform_(self.dt_proj.weight, -bound, bound)
        with torch.no_grad():
            self.dt_proj.bias.copy_(init_dt_proj_bias(self.d_inner, generator=generator))

    def forward(self, hidden_states: torch.Tensor) -> torch.Tensor:
        """hidden_states: [B, T, d_model] -> [B, T, d_model]."""
        batch, seqlen, _ = hidden_states.shape
        if seqlen != N_TIME:
            raise ValueError(f"seqlen must be {N_TIME}, got {seqlen}")

        xz = self.in_proj(hidden_states)  # [B, T, 2*d_inner]
        u, z = xz.chunk(2, dim=-1)

        # Depthwise conv1d, pad trai d_conv-1, lay seqlen phan tu dau (nhu C).
        conv = F.conv1d(
            u.transpose(1, 2),
            self.conv1d.weight,
            self.conv1d.bias,
            padding=self.d_conv - 1,
            groups=self.d_inner,
        )[:, :, :seqlen]
        u = F.silu(conv).transpose(1, 2)  # [B, T, d_inner]

        x_dbl = self.x_proj(u)  # [B, T, dt_rank + 2*d_state]
        dt, b_mat, c_mat = torch.split(
            x_dbl, [self.dt_rank, self.d_state, self.d_state], dim=-1
        )
        dt = softplus_c(self.dt_proj(dt))  # [B, T, d_inner]

        a = -torch.exp(self.A_log)  # [d_inner, d_state]
        h = torch.zeros(batch, self.d_inner, self.d_state, dtype=u.dtype, device=u.device)
        ys = []
        for t in range(seqlen):
            dt_t = dt[:, t, :]  # [B, d_inner]
            decay = torch.exp(dt_t.unsqueeze(-1) * a.unsqueeze(0))
            h = decay * h + (dt_t.unsqueeze(-1) * b_mat[:, t, :].unsqueeze(1)) * u[
                :, t, :
            ].unsqueeze(-1)
            ys.append((h * c_mat[:, t, :].unsqueeze(1)).sum(dim=-1))

        y = torch.stack(ys, dim=1)  # [B, T, d_inner]
        y = (y + u * self.D) * F.silu(z)
        return self.out_proj(y)


class MambaHAR(nn.Module):
    """linear_in -> Mamba -> mean-pool -> classifier, dung cho UCI HAR."""

    def __init__(self, generator: torch.Generator | None = None) -> None:
        super().__init__()
        self.linear_in = nn.Linear(N_FEAT, D_MODEL)
        self.mamba = MambaBlock(generator=generator)
        self.classifier = nn.Linear(D_MODEL, N_CLASSES)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.dim() == 2:
            if x.shape[1] != N_TIME * N_FEAT:
                raise ValueError(f"expected {N_TIME * N_FEAT} features, got {x.shape[1]}")
            x = x.view(-1, N_TIME, N_FEAT)
        if x.dim() != 3 or x.shape[1:] != (N_TIME, N_FEAT):
            raise ValueError(f"expected [B, {N_TIME}, {N_FEAT}], got {tuple(x.shape)}")
        h = self.linear_in(x)
        h = self.mamba(h)
        h = h.mean(dim=1)
        return self.classifier(h)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters())


if __name__ == "__main__":
    model = MambaHAR()
    print(f"parameters: {count_parameters(model)}")
    for name, tensor in model.state_dict().items():
        print(f"{name}: {tuple(tensor.shape)}")
    with torch.no_grad():
        dummy = torch.zeros(2, N_TIME, N_FEAT)
        print("output shape:", tuple(model(dummy).shape))

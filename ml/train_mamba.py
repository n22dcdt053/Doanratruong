#!/usr/bin/env python3
"""Huan luyen lai Mamba tren UCI HAR theo split_manifest.csv (Bang 2 de cuong).

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\train_mamba.py
    .venv-ml\\Scripts\\python ml\\train_mamba.py --out-dir <thu muc tam>   # kiem tai lap

Chi doc cac dong split=train/val cua manifest va X_train.txt. KHONG mo X_test.txt
va khong nap uci_test.f32; assert ben duoi chan moi dong split khac train/val.

Dau vao: 570 gia tri = 561 dac trung goc + 9 so 0, view(-1, 10, 57) nhu
firmware/common/mamba.c. Sieu tham so co dinh theo Bang 2, mot seed 42, khong tinh chinh.
Khoi tao theo cong thuc mac dinh cua Mamba (ghi trong train_config.json).
"""
import argparse
import copy
import csv
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import sklearn
import torch
from sklearn.metrics import confusion_matrix, f1_score
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from mamba_torch import N_CLASSES, N_FEAT, N_TIME, count_parameters, MambaHAR

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ml" / "split_manifest.csv"
X_TRAIN_FILE = ROOT / "data" / "UCI HAR Dataset" / "train" / "X_train.txt"

SEED = 42
BATCH_SIZE = 64
LR = 1e-3
MAX_EPOCHS = 100
PATIENCE = 10
N_RAW = 561
N_PAD = 9
N_INPUT = N_TIME * N_FEAT  # 570

# Gioi han thoi gian mot epoch theo brief: qua 5 phut thi dung va bao.
EPOCH_LIMIT_SECONDS = 300.0


def read_manifest_rows():
    with open(MANIFEST, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    used = [r for r in rows if r["split"] in ("train", "val")]
    train_rows = [r for r in used if r["split"] == "train"]
    val_rows = [r for r in used if r["split"] == "val"]

    # Chan tuyet doi: khong duoc co dong test trong du lieu huan luyen.
    assert used, "manifest rong"
    assert all(r["split"] != "test" for r in used), "co dong split=test lot vao train/val"
    assert all(r["source_file"] == "train/X_train.txt" for r in used), \
        "chi chap nhan dong tu train/X_train.txt"
    assert len({r["sample_id"] for r in used}) == len(used), "sample_id trung"
    return train_rows, val_rows


def load_xy(rows, X_all):
    idx = np.array([int(r["row_index"]) for r in rows], dtype=np.int64)
    y = np.array([int(r["label"]) for r in rows], dtype=np.int64)
    X = X_all[idx]
    assert X.shape == (len(rows), N_RAW), X.shape
    assert np.isfinite(X).all(), "X co NaN/Inf"
    X = np.concatenate([X, np.zeros((len(rows), N_PAD), dtype=np.float32)], axis=1)
    assert X.shape == (len(rows), N_INPUT), X.shape
    return torch.from_numpy(X), torch.from_numpy(y)


def check_finite(tag, tensor):
    """Dung ngay neu co NaN/Inf (khong tu them nguong hay doi cong thuc)."""
    if not bool(torch.isfinite(tensor).all()):
        raise SystemExit(f"DUNG: {tag} co NaN/Inf — khong tu sua, bao nguyen van")


def evaluate(model, loader, loss_fn):
    model.eval()
    total_loss = 0.0
    n = 0
    preds = []
    targets = []
    with torch.no_grad():
        for xb, yb in loader:
            logits = model(xb)
            check_finite("logit val", logits)
            loss = loss_fn(logits, yb)
            check_finite("loss val", loss)
            total_loss += float(loss.item()) * len(yb)
            n += len(yb)
            preds.append(logits.argmax(dim=1))
            targets.append(yb)
    y_pred = torch.cat(preds).numpy()
    y_true = torch.cat(targets).numpy()
    acc = float((y_pred == y_true).mean())
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", labels=list(range(N_CLASSES))))
    per_class = f1_score(y_true, y_pred, average=None, labels=list(range(N_CLASSES)))
    cm = confusion_matrix(y_true, y_pred, labels=list(range(N_CLASSES)))
    return {
        "loss": total_loss / n,
        "acc": acc,
        "macro_f1": macro_f1,
        "per_class_f1": [float(v) for v in per_class],
        "confusion_matrix": [[int(v) for v in row] for row in cm],
        "n": n,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(ROOT / "ml" / "results" / "mamba_retrained"),
                    help="thu muc ghi ket qua (dung thu muc tam khi kiem tai lap)")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)

    train_rows, val_rows = read_manifest_rows()
    X_all = np.loadtxt(X_TRAIN_FILE, dtype=np.float32)
    assert X_all.shape == (7352, N_RAW), X_all.shape
    X_tr, y_tr = load_xy(train_rows, X_all)
    X_va, y_va = load_xy(val_rows, X_all)

    gen = torch.Generator()
    gen.manual_seed(SEED)
    train_loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=BATCH_SIZE,
                              shuffle=True, generator=gen, num_workers=0)
    val_loader = DataLoader(TensorDataset(X_va, y_va), batch_size=BATCH_SIZE,
                            shuffle=False, num_workers=0)

    model = MambaHAR()
    n_params = count_parameters(model)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=0.0)
    loss_fn = nn.CrossEntropyLoss()

    history = []
    epoch_seconds = []
    best_f1 = float("-inf")
    best_epoch = 0
    best_state = None
    bad_epochs = 0

    print(f"train={len(train_rows)} val={len(val_rows)} (test khong duoc nap)")
    print(f"parameters={n_params}")
    print("epoch,train_loss,val_loss,val_acc,val_macro_f1,seconds")

    for epoch in range(1, MAX_EPOCHS + 1):
        t0 = time.perf_counter()
        model.train()
        total_loss = 0.0
        n = 0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            logits = model(xb)
            check_finite("logit train", logits)
            loss = loss_fn(logits, yb)
            check_finite("loss train", loss)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * len(yb)
            n += len(yb)
        train_loss = total_loss / n

        val = evaluate(model, val_loader, loss_fn)
        elapsed = time.perf_counter() - t0
        epoch_seconds.append(elapsed)
        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val["loss"],
            "val_acc": val["acc"],
            "val_macro_f1": val["macro_f1"],
        })
        print(f"{epoch},{train_loss:.6f},{val['loss']:.6f},{val['acc']:.6f},"
              f"{val['macro_f1']:.6f},{elapsed:.3f}", flush=True)

        if elapsed > EPOCH_LIMIT_SECONDS:
            raise SystemExit(
                f"DUNG: epoch {epoch} mat {elapsed:.1f}s > {EPOCH_LIMIT_SECONDS:.0f}s "
                "(brief: dung va bao thoi gian do duoc)"
            )

        if val["macro_f1"] > best_f1:
            best_f1 = val["macro_f1"]
            best_epoch = epoch
            best_state = copy.deepcopy(model.state_dict())
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= PATIENCE:
                break

    assert best_state is not None
    model.load_state_dict(best_state)
    val_best = evaluate(model, val_loader, loss_fn)

    torch.save(best_state, out_dir / "mamba_seed42.pt")

    with open(out_dir / "train_history.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["epoch", "train_loss", "val_loss", "val_acc", "val_macro_f1"],
                           lineterminator="\n")
        w.writeheader()
        for row in history:
            w.writerow({k: (f"{v:.9g}" if isinstance(v, float) else v) for k, v in row.items()})

    val_metrics = {
        "checkpoint_epoch": best_epoch,
        "n_val": val_best["n"],
        "accuracy": val_best["acc"],
        "macro_f1": val_best["macro_f1"],
        "per_class_f1": {str(i): val_best["per_class_f1"][i] for i in range(N_CLASSES)},
        "confusion_matrix": val_best["confusion_matrix"],
    }
    (out_dir / "val_metrics.json").write_text(
        json.dumps(val_metrics, indent=2) + "\n", encoding="utf-8", newline="\n")

    config = {
        "model": "Linear(57,64) -> Mamba(d_model=64,d_inner=128,d_state=16,d_conv=4,dt_rank=4)"
                 " -> mean-pool -> Linear(64,6), FP32",
        "parameters": n_params,
        "input": "570 gia tri = 561 dac trung goc + 9 so 0, view(-1, 10, 57), khong chuan hoa them",
        "optimizer": {"name": "Adam", "lr": LR, "weight_decay": 0.0},
        "loss": "CrossEntropyLoss",
        "batch_size": BATCH_SIZE,
        "shuffle": True,
        "shuffle_generator_seed": SEED,
        "max_epochs": MAX_EPOCHS,
        "early_stop_patience": PATIENCE,
        "checkpoint_selection": "val macro-F1 cao nhat; cai thien nghiem ngat; hoa -> epoch som hon",
        "seed": SEED,
        "device": "cpu",
        "torch_num_threads": 1,
        "deterministic_algorithms": True,
        "epoch_limit_seconds": EPOCH_LIMIT_SECONDS,
        "n_train": len(train_rows),
        "n_val": len(val_rows),
        "epochs_run": len(history),
        "stopped_epoch": history[-1]["epoch"],
        "best_epoch": best_epoch,
        "best_val_macro_f1": best_f1,
        "epoch_seconds": epoch_seconds,
        "init": {
            "A_log": "log(1..16) lap theo d_inner (36.742 tham so tong)",
            "D": "1.0",
            "dt_proj.weight": "U(-dt_rank^-0.5, +dt_rank^-0.5), dt_scale=1.0",
            "dt_proj.bias": "softplus^-1(dt), dt ~ logUniform(dt_min=0.001, dt_max=0.1), san 1e-4",
            "in_proj/x_proj/out_proj": "mac dinh PyTorch (khong bias)",
            "conv1d": "mac dinh PyTorch (kernel 4, groups=d_inner, co bias)",
            "linear_in/classifier": "mac dinh PyTorch",
            "note": "xem ml/mamba_torch.py; moi thu tu khoi tao nam sau torch.manual_seed(42)",
        },
        "versions": {
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
        },
    }
    (out_dir / "train_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"stopped_epoch={history[-1]['epoch']} best_epoch={best_epoch} "
          f"best_val_macro_f1={best_f1:.6f}")
    print(f"epoch_seconds_total={sum(epoch_seconds):.1f} "
          f"max={max(epoch_seconds):.1f} min={min(epoch_seconds):.1f}")
    print(f"checkpoint={out_dir / 'mamba_seed42.pt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

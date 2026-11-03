#!/usr/bin/env python3
"""Huan luyen MLP 561-64-6 tren UCI HAR theo split_manifest.csv.

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\train_mlp.py

Chi doc cac dong split=train/val cua manifest va X_train.txt.
KHONG mo X_test.txt; script co assert chan moi dong test lot vao qua trinh huan luyen.

Sieu tham so co dinh theo Bang 2 cua de cuong (khong tinh chinh).
"""
import argparse
import copy
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
import sklearn
import torch
from sklearn.metrics import confusion_matrix, f1_score
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ml" / "split_manifest.csv"
X_TRAIN_FILE = ROOT / "data" / "UCI HAR Dataset" / "train" / "X_train.txt"

SEED = 42
BATCH_SIZE = 64
LR = 1e-3
MAX_EPOCHS = 100
PATIENCE = 10
IN_FEATURES = 561
HIDDEN = 64
OUT_CLASSES = 6


def read_manifest_rows():
    with open(MANIFEST, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    train_rows = [r for r in rows if r["split"] == "train"]
    val_rows = [r for r in rows if r["split"] == "val"]
    used = train_rows + val_rows

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
    assert X.shape == (len(rows), IN_FEATURES), X.shape
    assert np.isfinite(X).all(), "X co NaN/Inf"
    return torch.from_numpy(X), torch.from_numpy(y)


def evaluate(model, loader):
    model.eval()
    total_loss = 0.0
    n = 0
    preds = []
    targets = []
    loss_fn = nn.CrossEntropyLoss()
    with torch.no_grad():
        for xb, yb in loader:
            logits = model(xb)
            loss = loss_fn(logits, yb)
            total_loss += float(loss.item()) * len(yb)
            n += len(yb)
            preds.append(logits.argmax(dim=1))
            targets.append(yb)
    y_pred = torch.cat(preds).numpy()
    y_true = torch.cat(targets).numpy()
    acc = float((y_pred == y_true).mean())
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", labels=list(range(OUT_CLASSES))))
    per_class = f1_score(y_true, y_pred, average=None, labels=list(range(OUT_CLASSES)))
    cm = confusion_matrix(y_true, y_pred, labels=list(range(OUT_CLASSES)))
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
    ap.add_argument("--out-dir", default=str(ROOT / "ml" / "results"),
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
    assert X_all.shape == (7352, IN_FEATURES), X_all.shape
    X_tr, y_tr = load_xy(train_rows, X_all)
    X_va, y_va = load_xy(val_rows, X_all)

    gen = torch.Generator()
    gen.manual_seed(SEED)
    train_loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=BATCH_SIZE,
                              shuffle=True, generator=gen, num_workers=0)
    val_loader = DataLoader(TensorDataset(X_va, y_va), batch_size=BATCH_SIZE,
                            shuffle=False, num_workers=0)

    model = nn.Sequential(
        nn.Linear(IN_FEATURES, HIDDEN),
        nn.ReLU(),
        nn.Linear(HIDDEN, OUT_CLASSES),
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=0.0)
    loss_fn = nn.CrossEntropyLoss()

    history = []
    best_f1 = float("-inf")
    best_epoch = 0
    best_state = None
    bad_epochs = 0

    print(f"train={len(train_rows)} val={len(val_rows)} (test khong duoc nap)")
    print("epoch,train_loss,val_loss,val_acc,val_macro_f1")

    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        total_loss = 0.0
        n = 0
        for xb, yb in train_loader:
            optimizer.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.item()) * len(yb)
            n += len(yb)
        train_loss = total_loss / n

        val = evaluate(model, val_loader)
        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val["loss"],
            "val_acc": val["acc"],
            "val_macro_f1": val["macro_f1"],
        })
        print(f"{epoch},{train_loss:.6f},{val['loss']:.6f},{val['acc']:.6f},{val['macro_f1']:.6f}")

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
    val_best = evaluate(model, val_loader)

    torch.save(best_state, out_dir / "mlp_seed42.pt")

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
        "per_class_f1": {str(i): val_best["per_class_f1"][i] for i in range(OUT_CLASSES)},
        "confusion_matrix": val_best["confusion_matrix"],
    }
    (out_dir / "val_metrics.json").write_text(
        json.dumps(val_metrics, indent=2) + "\n", encoding="utf-8", newline="\n")

    config = {
        "model": "Linear(561,64) -> ReLU -> Linear(64,6), FP32",
        "input": "561 dac trung goc, khong padding, khong chuan hoa them",
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
        "n_train": len(train_rows),
        "n_val": len(val_rows),
        "epochs_run": len(history),
        "stopped_epoch": history[-1]["epoch"],
        "best_epoch": best_epoch,
        "best_val_macro_f1": best_f1,
        "versions": {
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
        },
    }
    (out_dir / "train_config.json").write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"stopped_epoch={history[-1]['epoch']} best_epoch={best_epoch} best_val_macro_f1={best_f1:.6f}")
    print(f"checkpoint={out_dir / 'mlp_seed42.pt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

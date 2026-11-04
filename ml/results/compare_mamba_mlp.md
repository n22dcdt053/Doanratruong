# Bang so sanh Mamba va MLP tren cung tap chia (ml/split_manifest.csv)

Nguon so lieu (lay tu cac file ket qua da commit):

- Mamba huan luyen lai, seed 42: `ml/results/mamba_retrained/val_metrics.json` (checkpoint
  epoch 27), `ml/results/mamba_retrained/test_metrics.json` (checkpoint
  `mamba_seed42.pt`, sha256 `f742597b772f609968040e0ffc22f50b011a996ebf3c05fdbdfa8ec95b6f7839`).
- MLP 561-64-6, seed 42: `ml/results/val_metrics.json` (checkpoint epoch 26),
  `ml/results/test_metrics.json`.
- Kich thuoc mo hinh: `ml/results/model_size_comparison.md`.

Val: 1.801 mau / 5 nguoi. Test: 2.947 mau / 9 nguoi. Ca hai dung chung mot manifest.

## Tong hop

| Chi so | Mamba | MLP 561-64-6 | Chenh lech (Mamba - MLP) |
|---|---|---|---|
| Accuracy val | 0.942254 | 0.964464 | -0.022210 |
| Macro-F1 val | 0.935930 | 0.961066 | -0.025136 |
| Accuracy test | 0.929759 | 0.940278 | -0.010519 |
| Macro-F1 test | 0.927253 | 0.939992 | -0.012739 |
| So tham so | 36,742 | 36,358 | +384 |
| Byte trong so FP32 | 146,968 | 145,432 | +1,536 |

## F1 tung lop — tap validation (1.801 mau)

| Lop | Mamba | MLP | Chenh lech |
|---|---|---|---|
| 0 WALKING | 0.986667 | 0.981132 | +0.005535 |
| 1 WALKING_UPSTAIRS | 0.883031 | 0.947368 | -0.064337 |
| 2 WALKING_DOWNSTAIRS | 0.845794 | 0.909492 | -0.063698 |
| 3 SITTING | 0.951096 | 0.962585 | -0.011489 |
| 4 STANDING | 0.962733 | 0.968847 | -0.006114 |
| 5 LAYING | 0.986260 | 0.996970 | -0.010710 |

## F1 tung lop — tap test (2.947 mau)

| Lop | Mamba | MLP | Chenh lech |
|---|---|---|---|
| 0 WALKING | 0.930502 | 0.954455 | -0.023954 |
| 1 WALKING_UPSTAIRS | 0.904762 | 0.942060 | -0.037298 |
| 2 WALKING_DOWNSTAIRS | 0.892903 | 0.946988 | -0.054085 |
| 3 SITTING | 0.910828 | 0.895197 | +0.015632 |
| 4 STANDING | 0.925455 | 0.907814 | +0.017641 |
| 5 LAYING | 0.999070 | 0.993440 | +0.005630 |

## Ghi chu bat buoc

- Chi mot seed (42) cho moi mo hinh, nen khong suy ra duoc do on dinh giua cac lan khoi tao.
- Tap test chi co 9 nguoi; chua co khoang tin cay (bootstrap theo nguoi se lam o brief sau).
- Nguong sai so (neu co) chua duoc GVHD chot.
- Day chi la chenh lech so do tren cung tap chia; khong ket luan mo hinh nao tot hon.
- Trong so Mamba cong khai (accuracy 0.9267 / macro-F1 0.9265 tren test) khong nam trong bang
  nay: bo trong so do duoc train bang `random_split` khong theo nguoi va chon checkpoint theo
  accuracy, nen chi dung de tai lap thuc thi (xem `ml/results/fidelity_public_weights.txt`),
  khong so sanh duoc voi hai dong tren.

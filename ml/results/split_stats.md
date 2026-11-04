# Thong ke chia tap — UCI HAR (GroupShuffleSplit theo nguoi)

## Ket qua nguyen van cua sklearn

```text
GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
groups = subject_train (21 nguoi, 7352 mau)
tap validation (test_idx cua splitter): 5 nguoi [1, 3, 15, 25, 27]
so mau validation: 1801
so mau train (con lai): 5551
```

## So nguoi va so mau

| Tap | So nguoi | So mau | Danh sach nguoi |
|---|---|---|---|
| train | 16 | 5551 | 5 6 7 8 11 14 16 17 19 21 22 23 26 28 29 30 |
| val | 5 | 1801 | 1 3 15 25 27 |
| test | 9 | 2947 | 2 4 9 10 12 13 18 20 24 |

## Phan bo nhan

| Tap | 1 WALKING | 2 WALKING_UPSTAIRS | 3 WALKING_DOWNSTAIRS | 4 SITTING | 5 STANDING | 6 LAYING | Tong |
|---|---|---|---|---|---|---|---|
| train | 888 | 797 | 744 | 993 | 1053 | 1076 | 5551 |
| val | 338 | 276 | 242 | 293 | 321 | 331 | 1801 |
| test | 496 | 471 | 420 | 491 | 532 | 537 | 2947 |

## Ghi chu

- Nhan trong manifest la 0..5 (nhan goc 1..6 tru 1).
- Test goc giu nguyen toan bo 2947 mau / 9 nguoi; khong dung de chon bat cu thu gi.
- `split_manifest.csv` ghi theo thu tu: toan bo train goc (7352 dong) roi toan bo test goc (2947 dong).

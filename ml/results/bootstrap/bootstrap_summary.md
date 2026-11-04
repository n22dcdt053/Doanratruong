# Bootstrap CI 95% theo cum nguoi — Mamba (huan luyen lai) va MLP

- Tap test: **2947 cua so, 9 nguoi** (ma nguoi tang dan: 2, 4, 9, 10, 12, 13, 18, 20, 24).
- Bootstrap: **B = 2000**, seed **42**, moi lan rut 9 ma nguoi co hoan lai (giu toan bo cua so cua nguoi duoc rut), hai mo hinh tinh tren cung mot tap cua so (ghep cap).
- Khoang 95%: percentile 2,5 / 97,5 (`numpy.percentile`, `method="linear"`). Diem uoc luong la chi so tren toan bo tap test, khong phai trung binh bootstrap.
- Don vi: chi so tung mo hinh ghi thap phan 4 chu so; Δ ghi theo **diem phan tram** (2 chu so thap phan). Trong cac file CSV, Δ ghi dang thap phan (nhan 100 de ra diem phan tram).

## 1. Chi so toan test va khoang 95%

| Mo hinh | Chi so | Toan test | Khoang 95% | Trung binh bootstrap | SD bootstrap |
|---|---|---|---|---|---|
| Mamba (huan luyen lai) | accuracy | 0.9298 | [0.9058, 0.9540] | 0.9291 | 0.0122 |
| Mamba (huan luyen lai) | macro-F1 | 0.9273 | [0.9015, 0.9523] | 0.9264 | 0.0128 |
| MLP 561-64-6 | accuracy | 0.9403 | [0.9077, 0.9674] | 0.9394 | 0.0155 |
| MLP 561-64-6 | macro-F1 | 0.9400 | [0.9073, 0.9670] | 0.9391 | 0.0155 |

## 2. Chenh lech Δ = Mamba − MLP

| Chi so | Δ toan test (diem %) | Khoang 95% Δ (diem %) | Trung binh bootstrap (diem %) | SD (diem %) | Ti le Δ<0 | Ti le Δ=0 | Ti le Δ>0 |
|---|---|---|---|---|---|---|---|
| Δaccuracy | -1.05 | [-2.60, 0.75] | -1.03 | 0.85 | 0.8835 | 0.0080 | 0.1085 |
| Δmacro-F1 | -1.27 | [-3.11, 0.66] | -1.27 | 0.96 | 0.9095 | 0.0000 | 0.0905 |

(Ti le tinh tren 2000 lan bootstrap; Δ<0 nghia la Mamba thap hon MLP trong lan rut do, Δ>0 nghia la nguoc lai.)

## 3. Phan bo theo nguoi

| Nguoi | So cua so | acc Mamba | macro-F1 Mamba | acc MLP | macro-F1 MLP | Δacc (diem %) | ΔF1 (diem %) |
|---|---|---|---|---|---|---|---|
| 2 | 302 | 0.9669 | 0.9660 | 0.9735 | 0.9726 | -0.66 | -0.67 |
| 4 | 317 | 0.9432 | 0.9437 | 0.9527 | 0.9528 | -0.95 | -0.91 |
| 9 | 288 | 0.8819 | 0.8815 | 0.8681 | 0.8673 | 1.39 | 1.42 |
| 10 | 294 | 0.8912 | 0.8896 | 0.8469 | 0.8468 | 4.42 | 4.28 |
| 12 | 320 | 0.9000 | 0.8959 | 0.9250 | 0.9217 | -2.50 | -2.59 |
| 13 | 327 | 0.9633 | 0.9603 | 0.9908 | 0.9903 | -2.75 | -3.01 |
| 18 | 364 | 0.8929 | 0.8655 | 0.9451 | 0.9411 | -5.22 | -7.57 |
| 20 | 354 | 0.9350 | 0.9265 | 0.9463 | 0.9465 | -1.13 | -2.00 |
| 24 | 381 | 0.9816 | 0.9802 | 0.9895 | 0.9903 | -0.79 | -1.01 |

Ghi chu: moi nguoi trong tap test deu co du 6 lop, nen macro-F1 trong nguoi xac dinh duoc; so lop co mau so 0 khi tinh trong tung nguoi: Mamba=0, MLP=0.

## 4. Bo-mot-nguoi (leave-one-subject-out)

| Nguoi bi bo | So cua so con lai | Δacc (diem %) | ΔF1 (diem %) |
|---|---|---|---|
| 2 | 2645 | -1.10 | -1.36 |
| 4 | 2630 | -1.06 | -1.32 |
| 9 | 2659 | -1.32 | -1.61 |
| 10 | 2653 | -1.66 | -1.90 |
| 12 | 2627 | -0.88 | -1.12 |
| 13 | 2620 | -0.84 | -1.06 |
| 18 | 2583 | -0.46 | -0.58 |
| 20 | 2593 | -1.04 | -1.20 |
| 24 | 2566 | -1.09 | -1.32 |

- ΔF1 khi bo-mot-nguoi: nho nhat -1.90 diem % (bo nguoi 10), lon nhat -0.58 diem % (bo nguoi 18); khoang -1.90 … -0.58 diem %.

## 5. F1 theo lop tren toan bo tap test (khong co khoang tin cay)

| Lop | F1 Mamba | F1 MLP |
|---|---|---|
| 0 WALKING | 0.9305 | 0.9545 |
| 1 WALKING_UPSTAIRS | 0.9048 | 0.9421 |
| 2 WALKING_DOWNSTAIRS | 0.8929 | 0.9470 |
| 3 SITTING | 0.9108 | 0.8952 |
| 4 STANDING | 0.9255 | 0.9078 |
| 5 LAYING | 0.9991 | 0.9934 |

## 6. Do on dinh Monte Carlo cua chinh bootstrap (seed 43, 44)

Chay lai bootstrap voi seed 43 va 44 **chi de xem dau mut khoang 95% dich bao nhieu**. Day **khong phai** bien thien do khoi tao/huan luyen va **khong** duoc dung de chon seed; ket qua chinh thuc van la seed 42.

| Seed | CI ΔF1 (diem %) | CI Δacc (diem %) | CI F1 Mamba | CI F1 MLP |
|---|---|---|---|---|
| 42 (chinh thuc) | [-3.11, 0.66] | [-2.60, 0.75] | [0.9015, 0.9523] | [0.9073, 0.9670] |
| 43 | [-3.07, 0.40] | [-2.55, 0.52] | [0.9025, 0.9513] | [0.9102, 0.9668] |
| 44 | [-3.15, 0.50] | [-2.60, 0.61] | [0.9030, 0.9523] | [0.9093, 0.9670] |

## 7. Kiem tra tu dong

1. Hai file du doan khop tung hang (sample_id, subject_id, label), 2947 dong, 9 nguoi, so cua so theo nguoi dung bang o muc 0 cua brief.
2. Tuong duong resample: 200 lan rut dau, sai khac tuyet doi lon nhat giua resample cua so tuong minh (sklearn) va tinh tu ma tran nham lan la 0.0e+00 (<= 1e-12).
3. Chi so toan test tinh lai bang ma tran nham lan khop hai test_metrics.json: sai khac tuyet doi lon nhat 0.0e+00 (<= 1e-12).
4. So lan gap lop co mau so 0 trong 2000 lan bootstrap (ca 2 mo hinh): 0.
5. Doi chung am tinh (MLP vs MLP): max|Δ| = 0.0e+00, CI Δacc = [0.0, 0.0], CI Δmacro-F1 = [0.0, 0.0] (thap phan).
6. Tinh tat dinh: so sha256 tung file ket qua giua hai lan chay (ghi trong `docs/briefs/REPORT_06.md`).

## 8. Ghi chu bat buoc

- Tap test chi co **9 nguoi** -> phan phoi bootstrap chi co 9 phan tu goc de lay lai; khoang 95% bang percentile voi so cum nho co the qua hep hoac khong on dinh. Dien giai than trong.
- Moi mo hinh huan luyen **mot seed (42)** -> khoang nay **khong** mo ta bien thien do khoi tao/huan luyen.
- Nguong sai so (neu co) chua duoc GVHD chot; tai lieu nay khong dung nguong nao.
- Mamba huan luyen lai bang PyTorch thuan (khong `mamba_ssm`), cung `ml/split_manifest.csv` voi MLP; trong so Mamba cong khai **khong** tham gia.
- Khong xep hang hai mo hinh; tai lieu chi mo ta chenh lech va do bat dinh cua phep do.


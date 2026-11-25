# Bao cao ghep - phien 1

**Trang thai phien: HOP LE (qua cac kiem tra duoi day).** Day la so do CHUA HIEU CHINH; khong co danh gia do chinh xac.

- logger: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\smoke1\s1_logger.csv` (sha256 `de078408cafe8359ef274803fc05899c1a141f21a41679e1da78f7013669e406`)
- devkit: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\smoke1\s1_devkit.txt` (sha256 `b6598622af227e8dd7d1268f55877f790557490e2976668d3fe7546a248d571c`)
- R_shunt dung de tinh: **0.1 ohm, danh nghia, chua do**
- order=MF seed=42

## Kiem tra

- [ok] tieu de logger: # fw=a123742 cfg=0x4127 avg=1 vct_us=1100 rshunt_nominal_ohm=0.1 marker_gpio=1 ina_addr=0x44 mfr_id=0x5449 die_id=0x2260 fw_tree=clean
- [canh bao] 1 dong logger khong khop mau (ghi nguyen, khong dung); dong dau: (2, '=clean')
- [ok] devkit ACK: ACK session=1 order=MF seed=42
- [ok] devkit: 32 dong EMP/BLK
- [ok] devkit: co SESSION_DONE session=1
- [ok] devkit: pulse lien tuc tu 1
- [ok] devkit: cfg/kind/block + idx khop pulse_plan(MF) va hoan vi seed=42 (schedule.py)
- [ok] logger: 32 xung (len+xuong)
- [ok] 33754 mau S, chu ky trung vi 2000 us
- [ok] STAT dau->cuoi: samples 19971->49930, edges 0->64, drops tang 0, i2c_err tang 0
- [ok] P_idle = -1.25147e-07 W (13423 mau, do lech chuan 1.02e-07 W)

## Cua so nen

| loai | bat dau us | ket thuc us | so mau | P_mean W | co mau tu bat dau |
|---|---|---|---|---|---|
| init | 41595639 | 48595639 | 3495 | -1.2639485e-07 | co |
| rest | 52335721 | 53735721 | 699 | -1.29157725e-07 | co |
| rest | 80095390 | 81495390 | 699 | -1.23122318e-07 | co |
| gap | 55236704 | 56777182 | 769 | -1.31420676e-07 | co |
| gap | 58597216 | 59997147 | 699 | -1.21199928e-07 | co |
| gap | 61817286 | 63217110 | 699 | -1.20261087e-07 | co |
| gap | 65037455 | 66437065 | 699 | -1.25044707e-07 | co |
| gap | 68257419 | 69657035 | 698 | -1.28357808e-07 | co |
| gap | 71477406 | 72876986 | 699 | -1.20976395e-07 | co |
| gap | 82996374 | 84536847 | 769 | -1.2341515e-07 | co |
| gap | 85235827 | 86636823 | 700 | -1.25044643e-07 | co |
| gap | 87335811 | 88736794 | 699 | -1.2513412e-07 | co |
| gap | 89435774 | 90836767 | 700 | -1.24464286e-07 | co |
| gap | 91535747 | 92936743 | 699 | -1.26251788e-07 | co |
| gap | 93635724 | 95036714 | 700 | -1.21517857e-07 | co |

P_idle_mean = -1.2514667e-07 W, do lech chuan = 1.01608636e-07 W, 13423 mau.

## Xung rong (EMP)

Xung rong ~1 ms voi chu ky INA226 ~2.2 ms: nhieu xung co 0-1 mau. Day chi la so do, khong tru vao dau ca.

| pulse | cfg | do rong ms | so mau | E_raw mJ | E_net mJ |
|---|---|---|---|---|---|
| 1 | mamba | 1.008 | 1 | -9.45e-08 | 3.16478433e-08 |
| 2 | mamba | 1.002 | 1 | -1.565625e-07 | -3.11655368e-08 |
| 3 | mamba | 1.001 | 1 | -0 | 1.25271817e-07 |
| 4 | mamba | 1.003 | 1 | -0 | 1.2552211e-07 |
| 5 | mamba | 1.004 | 1 | -6.275e-08 | 6.28972566e-08 |
| 6 | mamba | 1.003 | 1 | -9.403125e-08 | 3.14908599e-08 |
| 7 | mamba | 1.003 | 0 |  |  |
| 8 | mamba | 1.002 | 0 |  |  |
| 9 | mamba | 1.003 | 0 |  |  |
| 10 | mamba | 1.003 | 0 |  |  |
| 17 | mlp | 1.006 | 1 | -0 | 1.2589755e-07 |
| 18 | mlp | 1.002 | 1 | -9.39375e-08 | 3.14594632e-08 |
| 19 | mlp | 1.005 | 1 | -0 | 1.25772403e-07 |
| 20 | mlp | 1.003 | 0 |  |  |
| 21 | mlp | 1.003 | 0 |  |  |
| 22 | mlp | 1.002 | 0 |  |  |
| 23 | mlp | 1.002 | 0 |  |  |
| 24 | mlp | 1.003 | 0 |  |  |
| 25 | mlp | 1.003 | 0 |  |  |
| 26 | mlp | 1.002 | 0 |  |  |

## Gia dinh va cach tinh

- Hai dong ho khac nhau (XIAO va devkit): ghep bang so thu tu xung, khong bang thoi gian. Do rong xung logger so voi devkit (+-20%%) va khoang cach hai xung lien tiep (2 ms + 0.1%%) la kiem tra lech timer/GPIO.
- Phien duoc coi la toan bo doan capture: capture phai bat dau truoc lenh START va dung sau SESSION_DONE; xung thua ben ngoai phien se bi bao la thua.
- Thoi diem mau = ngay sau khi doc xong thanh ghi bus; chua bu tre chuyen doi (<= ~1 chu ky + thoi gian doc I2C).
- E: tich phan hinh thang P(t) giua cac mau trong [canh len, canh xuong]; hai doan bien giu gia tri mau gan nhat; P_mean = E_raw / thoi luong; V_mean, I_mean la trung binh mau.
- Cua so nen: (init) 10 s nghi dau phien suy tu xung dau tien va do dai khoi 0 (20 luot on dinh ~ 2 x khoi 0 bi loai vi CPU dang tinh), bo 2 s dau va 1 s cuoi; (rest) 2 s truoc xung rong dau moi cau hinh; (gap) khoang nghi >= 1.6 s giua hai xung cung cau hinh. Moi doan bo 300 ms hai dau. Brief 08 viet cua so dau la 'ACK+2 s den xung dau - 1 s'; cua so do chua 20 luot on dinh (CPU dang tinh) nen khong dung lam nen.
- few_samples: khoi < 20 mau; saturated: |shunt_raw| >= 32767; i2c_gap: dong X trong khoi hoac khoang cach hai mau lien tiep > 3 x chu ky trung vi.
- Cac nguong tren la quy uoc cua code ghep, khong phai nguong cua phep do.


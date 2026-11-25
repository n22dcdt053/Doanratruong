# Bao cao ghep - phien 3

**Trang thai phien: HOP LE (qua cac kiem tra duoi day).** Day la so do CHUA HIEU CHINH; khong co danh gia do chinh xac.

- logger: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\real_s3\s3_logger.csv` (sha256 `c7175b247861a488bc472fa080daad1d2edcde6805144bc789004b2cc200fe16`)
- devkit: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\real_s3\s3_devkit.txt` (sha256 `3fbd1b157ae80146139c427bcf6b27e14257d8ad5a4b4aa79619fb57dd02e45f`)
- R_shunt dung de tinh: **0.1 ohm, danh nghia, chua do**
- order=MF seed=44

## Kiem tra

- [ok] tieu de logger: # fw=a123742 cfg=0x4127 avg=1 vct_us=1100 rshunt_nominal_ohm=0.1 marker_gpio=1 ina_addr=0x44 mfr_id=0x5449 die_id=0x2260 fw_tree=clean
- [ok] devkit ACK: ACK session=3 order=MF seed=44
- [ok] devkit: 32 dong EMP/BLK
- [ok] devkit: co SESSION_DONE session=3
- [ok] devkit: pulse lien tuc tu 1
- [ok] devkit: cfg/kind/block + idx khop pulse_plan(MF) va hoan vi seed=44 (schedule.py)
- [ok] logger: 32 xung (len+xuong)
- [ok] 33655 mau S, chu ky trung vi 2000 us
- [ok] STAT dau->cuoi: samples 429398->461853, edges 180->244, drops tang 0, i2c_err tang 0
- [ok] P_idle = 0.170186 W (13424 mau, do lech chuan 0.0021 W)

## Cua so nen

| loai | bat dau us | ket thuc us | so mau | P_mean W | co mau tu bat dau |
|---|---|---|---|---|---|
| init | 862764688 | 869764688 | 3495 | 0.170131997 | co |
| rest | 873505178 | 874905178 | 699 | 0.170308388 | co |
| rest | 901264806 | 902664806 | 699 | 0.170225214 | co |
| gap | 876406157 | 877946630 | 769 | 0.170244025 | co |
| gap | 879766862 | 881166585 | 699 | 0.170209853 | co |
| gap | 882986881 | 884386542 | 699 | 0.170355242 | co |
| gap | 886206795 | 887606503 | 699 | 0.170156646 | co |
| gap | 889426701 | 890826459 | 699 | 0.170112796 | co |
| gap | 892646589 | 894046417 | 699 | 0.170215853 | co |
| gap | 904165791 | 905706263 | 770 | 0.170125356 | co |
| gap | 906405242 | 907806232 | 699 | 0.170153912 | co |
| gap | 908505221 | 909906200 | 700 | 0.170209973 | co |
| gap | 910605180 | 912006178 | 699 | 0.170236358 | co |
| gap | 912705157 | 914106146 | 700 | 0.170177337 | co |
| gap | 914805127 | 916206121 | 699 | 0.17014934 | co |

P_idle_mean = 0.17018631 W, do lech chuan = 0.00209962795 W, 13424 mau.

## Xung rong (EMP)

Xung rong ~1 ms voi chu ky INA226 ~2.2 ms: nhieu xung co 0-1 mau. Day chi la so do, khong tru vao dau ca.

| pulse | cfg | do rong ms | so mau | E_raw mJ | E_net mJ |
|---|---|---|---|---|---|
| 1 | mamba | 1.009 | 1 | 0.1740875 | 0.00236951302 |
| 2 | mamba | 1.002 | 1 | 0.17270472 | 0.0021780375 |
| 3 | mamba | 1.003 | 1 | 0.173052292 | 0.00235542276 |
| 4 | mamba | 1.002 | 1 | 0.172489697 | 0.00196301457 |
| 5 | mamba | 1.002 | 1 | 0.173204217 | 0.0026775345 |
| 6 | mamba | 1.003 | 1 | 0.17333683 | 0.00263996132 |
| 7 | mamba | 1.003 | 0 |  |  |
| 8 | mamba | 1.002 | 0 |  |  |
| 9 | mamba | 1.003 | 0 |  |  |
| 10 | mamba | 1.003 | 0 |  |  |
| 17 | mlp | 1.004 | 0 |  |  |
| 18 | mlp | 1.002 | 0 |  |  |
| 19 | mlp | 1.002 | 0 |  |  |
| 20 | mlp | 1.002 | 0 |  |  |
| 21 | mlp | 0.999 | 0 |  |  |
| 22 | mlp | 1.002 | 1 | 0.168369316 | -0.002157366 |
| 23 | mlp | 1.003 | 1 | 0.168498264 | -0.00219860471 |
| 24 | mlp | 1.003 | 1 | 0.168729362 | -0.00196750724 |
| 25 | mlp | 1.002 | 1 | 0.168600246 | -0.00192643631 |
| 26 | mlp | 1.003 | 1 | 0.168672504 | -0.00202436481 |

## Gia dinh va cach tinh

- Hai dong ho khac nhau (XIAO va devkit): ghep bang so thu tu xung, khong bang thoi gian. Do rong xung logger so voi devkit (+-20%%) va khoang cach hai xung lien tiep (2 ms + 0.1%%) la kiem tra lech timer/GPIO.
- Phien duoc coi la toan bo doan capture: capture phai bat dau truoc lenh START va dung sau SESSION_DONE; xung thua ben ngoai phien se bi bao la thua.
- Thoi diem mau = ngay sau khi doc xong thanh ghi bus; chua bu tre chuyen doi (<= ~1 chu ky + thoi gian doc I2C).
- E: tich phan hinh thang P(t) giua cac mau trong [canh len, canh xuong]; hai doan bien giu gia tri mau gan nhat; P_mean = E_raw / thoi luong; V_mean, I_mean la trung binh mau.
- Cua so nen: (init) 10 s nghi dau phien suy tu xung dau tien va do dai khoi 0 (20 luot on dinh ~ 2 x khoi 0 bi loai vi CPU dang tinh), bo 2 s dau va 1 s cuoi; (rest) 2 s truoc xung rong dau moi cau hinh; (gap) khoang nghi >= 1.6 s giua hai xung cung cau hinh. Moi doan bo 300 ms hai dau. Brief 08 viet cua so dau la 'ACK+2 s den xung dau - 1 s'; cua so do chua 20 luot on dinh (CPU dang tinh) nen khong dung lam nen.
- few_samples: khoi < 20 mau; saturated: |shunt_raw| >= 32767; i2c_gap: dong X trong khoi hoac khoang cach hai mau lien tiep > 3 x chu ky trung vi.
- Cac nguong tren la quy uoc cua code ghep, khong phai nguong cua phep do.


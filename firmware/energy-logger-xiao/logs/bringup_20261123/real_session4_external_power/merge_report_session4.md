# Bao cao ghep - phien 4

**Trang thai phien: HOP LE (qua cac kiem tra duoi day).** Day la so do CHUA HIEU CHINH; khong co danh gia do chinh xac.

- logger: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\real_s4\s4_logger.csv` (sha256 `7745af2af34ee5cc97f5a015fecf9511a777888d9607f0c98c6147446568b565`)
- devkit: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\real_s4\s4_devkit.txt` (sha256 `e4c306092da641e6b952e1780f5d8b8af4859d6198c5513d9baa712cef65b986`)
- R_shunt dung de tinh: **0.1 ohm, danh nghia, chua do**
- order=LF seed=45

## Kiem tra

- [ok] tieu de logger: # fw=a123742 cfg=0x4127 avg=1 vct_us=1100 rshunt_nominal_ohm=0.1 marker_gpio=1 ina_addr=0x44 mfr_id=0x5449 die_id=0x2260 fw_tree=clean
- [ok] devkit ACK: ACK session=4 order=LF seed=45
- [ok] devkit: 32 dong EMP/BLK
- [ok] devkit: co SESSION_DONE session=4
- [ok] devkit: pulse lien tuc tu 1
- [ok] devkit: cfg/kind/block + idx khop pulse_plan(LF) va hoan vi seed=45 (schedule.py)
- [ok] logger: 32 xung (len+xuong)
- [ok] 33451 mau S, chu ky trung vi 2000 us
- [ok] STAT dau->cuoi: samples 469343->499301, edges 244->308, drops tang 0, i2c_err tang 0
- [ok] P_idle = 0.170097 W (13423 mau, do lech chuan 0.00206 W)

## Cua so nen

| loai | bat dau us | ket thuc us | so mau | P_mean W | co mau tu bat dau |
|---|---|---|---|---|---|
| init | 939966234 | 946966234 | 3495 | 0.170008132 | co |
| rest | 948464190 | 949864190 | 699 | 0.170104756 | co |
| rest | 971703891 | 973103891 | 699 | 0.17028762 | co |
| gap | 951365169 | 952905632 | 769 | 0.170028174 | co |
| gap | 953604609 | 955005612 | 700 | 0.169979371 | co |
| gap | 955704605 | 957105583 | 699 | 0.170043888 | co |
| gap | 957804562 | 959205550 | 700 | 0.170005459 | co |
| gap | 959904530 | 961305525 | 699 | 0.169928162 | co |
| gap | 962004505 | 963405500 | 700 | 0.169982663 | co |
| gap | 974604862 | 976145330 | 769 | 0.170304259 | co |
| gap | 977965509 | 979365296 | 699 | 0.170326495 | co |
| gap | 981185677 | 982585253 | 698 | 0.170190944 | co |
| gap | 984405415 | 985805208 | 699 | 0.170193904 | co |
| gap | 987625483 | 989025165 | 699 | 0.170201373 | co |
| gap | 990845451 | 992245121 | 699 | 0.170214912 | co |

P_idle_mean = 0.170097151 W, do lech chuan = 0.00205893836 W, 13423 mau.

## Xung rong (EMP)

Xung rong ~1 ms voi chu ky INA226 ~2.2 ms: nhieu xung co 0-1 mau. Day chi la so do, khong tru vao dau ca.

| pulse | cfg | do rong ms | so mau | E_raw mJ | E_net mJ |
|---|---|---|---|---|---|
| 1 | mlp | 1.007 | 0 |  |  |
| 2 | mlp | 1.003 | 1 | 0.169134636 | -0.00147280652 |
| 3 | mlp | 1.002 | 1 | 0.16906173 | -0.0013756158 |
| 4 | mlp | 1.002 | 1 | 0.169505835 | -0.000931510615 |
| 5 | mlp | 1.003 | 1 | 0.170215369 | -0.000392074016 |
| 6 | mlp | 1.002 | 1 | 0.171125318 | 0.000687971885 |
| 7 | mlp | 1.002 | 1 | 0.173568601 | 0.00313125495 |
| 8 | mlp | 1.005 | 1 | 0.173791447 | 0.00284380949 |
| 9 | mlp | 1.002 | 0 |  |  |
| 10 | mlp | 1.002 | 0 |  |  |
| 17 | mamba | 0.994 | 1 | 0.168247329 | -0.000829239592 |
| 18 | mamba | 1.003 | 1 | 0.170366884 | -0.000240558329 |
| 19 | mamba | 1.003 | 1 | 0.172851535 | 0.00224409208 |
| 20 | mamba | 1.002 | 0 |  |  |
| 21 | mamba | 1.003 | 0 |  |  |
| 22 | mamba | 1.003 | 0 |  |  |
| 23 | mamba | 1.002 | 0 |  |  |
| 24 | mamba | 1.003 | 0 |  |  |
| 25 | mamba | 1.003 | 0 |  |  |
| 26 | mamba | 1.002 | 0 |  |  |

## Gia dinh va cach tinh

- Hai dong ho khac nhau (XIAO va devkit): ghep bang so thu tu xung, khong bang thoi gian. Do rong xung logger so voi devkit (+-20%%) va khoang cach hai xung lien tiep (2 ms + 0.1%%) la kiem tra lech timer/GPIO.
- Phien duoc coi la toan bo doan capture: capture phai bat dau truoc lenh START va dung sau SESSION_DONE; xung thua ben ngoai phien se bi bao la thua.
- Thoi diem mau = ngay sau khi doc xong thanh ghi bus; chua bu tre chuyen doi (<= ~1 chu ky + thoi gian doc I2C).
- E: tich phan hinh thang P(t) giua cac mau trong [canh len, canh xuong]; hai doan bien giu gia tri mau gan nhat; P_mean = E_raw / thoi luong; V_mean, I_mean la trung binh mau.
- Cua so nen: (init) 10 s nghi dau phien suy tu xung dau tien va do dai khoi 0 (20 luot on dinh ~ 2 x khoi 0 bi loai vi CPU dang tinh), bo 2 s dau va 1 s cuoi; (rest) 2 s truoc xung rong dau moi cau hinh; (gap) khoang nghi >= 1.6 s giua hai xung cung cau hinh. Moi doan bo 300 ms hai dau. Brief 08 viet cua so dau la 'ACK+2 s den xung dau - 1 s'; cua so do chua 20 luot on dinh (CPU dang tinh) nen khong dung lam nen.
- few_samples: khoi < 20 mau; saturated: |shunt_raw| >= 32767; i2c_gap: dong X trong khoi hoac khoang cach hai mau lien tiep > 3 x chu ky trung vi.
- Cac nguong tren la quy uoc cua code ghep, khong phai nguong cua phep do.


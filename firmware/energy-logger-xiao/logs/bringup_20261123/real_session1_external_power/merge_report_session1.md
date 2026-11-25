# Bao cao ghep - phien 1

**Trang thai phien: HOP LE (qua cac kiem tra duoi day).** Day la so do CHUA HIEU CHINH; khong co danh gia do chinh xac.

- logger: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\real2\s1_logger.csv` (sha256 `9072b7829b854fd2ed2e6cb36a2d81a84d5306e5e8e04b38b18c5cc35263e4de`)
- devkit: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\real2\s1_devkit.txt` (sha256 `c39f4901b386679ccb42d155df2c0408840216e4c7c8a075736e0abf2580ea45`)
- R_shunt dung de tinh: **0.1 ohm, danh nghia, chua do**
- order=MF seed=42

## Kiem tra

- [ok] tieu de logger: # fw=a123742 cfg=0x4127 avg=1 vct_us=1100 rshunt_nominal_ohm=0.1 marker_gpio=1 ina_addr=0x44 mfr_id=0x5449 die_id=0x2260 fw_tree=clean
- [ok] devkit ACK: ACK session=1 order=MF seed=42
- [ok] devkit: 32 dong EMP/BLK
- [ok] devkit: co SESSION_DONE session=1
- [ok] devkit: pulse lien tuc tu 1
- [ok] devkit: cfg/kind/block + idx khop pulse_plan(MF) va hoan vi seed=42 (schedule.py)
- [ok] logger: 32 xung (len+xuong)
- [ok] 34061 mau S, chu ky trung vi 2000 us
- [ok] STAT dau->cuoi: samples 307069->339524, edges 52->116, drops tang 0, i2c_err tang 0
- [ok] P_idle = 0.16957 W (13423 mau, do lech chuan 0.00188 W)

## Cua so nen

| loai | bat dau us | ket thuc us | so mau | P_mean W | co mau tu bat dau |
|---|---|---|---|---|---|
| init | 618338313 | 625338313 | 3495 | 0.169887419 | co |
| rest | 629078395 | 630478395 | 699 | 0.169995745 | co |
| rest | 656838029 | 658238029 | 699 | 0.169276678 | co |
| gap | 631979376 | 633519852 | 769 | 0.169848638 | co |
| gap | 635339883 | 636739812 | 699 | 0.169936518 | co |
| gap | 638559950 | 639959771 | 699 | 0.169928561 | co |
| gap | 641780114 | 643179722 | 698 | 0.169505259 | co |
| gap | 645000083 | 646399689 | 699 | 0.169405365 | co |
| gap | 648220057 | 649619635 | 699 | 0.169290344 | co |
| gap | 659739011 | 661279482 | 770 | 0.169336603 | co |
| gap | 661978462 | 663379456 | 699 | 0.169009083 | co |
| gap | 664078443 | 665479425 | 700 | 0.169111818 | co |
| gap | 666178404 | 667579395 | 699 | 0.169221762 | co |
| gap | 668278375 | 669679373 | 700 | 0.168945612 | co |
| gap | 670378349 | 671779337 | 699 | 0.169586383 | co |

P_idle_mean = 0.169570427 W, do lech chuan = 0.00187915203 W, 13423 mau.

## Xung rong (EMP)

Xung rong ~1 ms voi chu ky INA226 ~2.2 ms: nhieu xung co 0-1 mau. Day chi la so do, khong tru vao dau ca.

| pulse | cfg | do rong ms | so mau | E_raw mJ | E_net mJ |
|---|---|---|---|---|---|
| 1 | mamba | 1.008 | 1 | 0.173316528 | 0.00238953745 |
| 2 | mamba | 1.003 | 1 | 0.172281705 | 0.00220256705 |
| 3 | mamba | 1.003 | 1 | 0.171916206 | 0.00183706759 |
| 4 | mamba | 1.002 | 1 | 0.171665145 | 0.00175557701 |
| 5 | mamba | 1.003 | 1 | 0.172026787 | 0.00194764834 |
| 6 | mamba | 1.004 | 1 | 0.171943314 | 0.00169460553 |
| 7 | mamba | 1.002 | 0 |  |  |
| 8 | mamba | 1.002 | 0 |  |  |
| 9 | mamba | 1.003 | 0 |  |  |
| 10 | mamba | 1.002 | 0 |  |  |
| 17 | mlp | 1.005 | 0 |  |  |
| 18 | mlp | 1.002 | 0 |  |  |
| 19 | mlp | 1.002 | 0 |  |  |
| 20 | mlp | 1.002 | 0 |  |  |
| 21 | mlp | 1.003 | 0 |  |  |
| 22 | mlp | 1.002 | 1 | 0.170355093 | 0.000445524638 |
| 23 | mlp | 1.003 | 1 | 0.170119739 | 4.06005544e-05 |
| 24 | mlp | 1.003 | 1 | 0.169309002 | -0.000770136883 |
| 25 | mlp | 1.002 | 1 | 0.169314453 | -0.000595114987 |
| 26 | mlp | 1.003 | 1 | 0.169134636 | -0.000944502164 |

## Gia dinh va cach tinh

- Hai dong ho khac nhau (XIAO va devkit): ghep bang so thu tu xung, khong bang thoi gian. Do rong xung logger so voi devkit (+-20%%) va khoang cach hai xung lien tiep (2 ms + 0.1%%) la kiem tra lech timer/GPIO.
- Phien duoc coi la toan bo doan capture: capture phai bat dau truoc lenh START va dung sau SESSION_DONE; xung thua ben ngoai phien se bi bao la thua.
- Thoi diem mau = ngay sau khi doc xong thanh ghi bus; chua bu tre chuyen doi (<= ~1 chu ky + thoi gian doc I2C).
- E: tich phan hinh thang P(t) giua cac mau trong [canh len, canh xuong]; hai doan bien giu gia tri mau gan nhat; P_mean = E_raw / thoi luong; V_mean, I_mean la trung binh mau.
- Cua so nen: (init) 10 s nghi dau phien suy tu xung dau tien va do dai khoi 0 (20 luot on dinh ~ 2 x khoi 0 bi loai vi CPU dang tinh), bo 2 s dau va 1 s cuoi; (rest) 2 s truoc xung rong dau moi cau hinh; (gap) khoang nghi >= 1.6 s giua hai xung cung cau hinh. Moi doan bo 300 ms hai dau. Brief 08 viet cua so dau la 'ACK+2 s den xung dau - 1 s'; cua so do chua 20 luot on dinh (CPU dang tinh) nen khong dung lam nen.
- few_samples: khoi < 20 mau; saturated: |shunt_raw| >= 32767; i2c_gap: dong X trong khoi hoac khoang cach hai mau lien tiep > 3 x chu ky trung vi.
- Cac nguong tren la quy uoc cua code ghep, khong phai nguong cua phep do.


# Bao cao ghep - phien 5

**Trang thai phien: HOP LE (qua cac kiem tra duoi day).** Day la so do CHUA HIEU CHINH; khong co danh gia do chinh xac.

- logger: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\real_s5\s5_logger.csv` (sha256 `f3977495dfb4f032981f7a6c19ca2f9b4b89a45667766012ed0be365f4a9dd32`)
- devkit: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\real_s5\s5_devkit.txt` (sha256 `06d1441129a4d010487978b67a01e245e8a45bd96a8ededfaac6d38ae3a55e60`)
- R_shunt dung de tinh: **0.1 ohm, danh nghia, chua do**
- order=MF seed=46

## Kiem tra

- [ok] tieu de logger: # fw=a123742 cfg=0x4127 avg=1 vct_us=1100 rshunt_nominal_ohm=0.1 marker_gpio=1 ina_addr=0x44 mfr_id=0x5449 die_id=0x2260 fw_tree=clean
- [ok] devkit ACK: ACK session=5 order=MF seed=46
- [ok] devkit: 32 dong EMP/BLK
- [ok] devkit: co SESSION_DONE session=5
- [ok] devkit: pulse lien tuc tu 1
- [ok] devkit: cfg/kind/block + idx khop pulse_plan(MF) va hoan vi seed=46 (schedule.py)
- [ok] logger: 32 xung (len+xuong)
- [ok] 33440 mau S, chu ky trung vi 2000 us
- [ok] STAT dau->cuoi: samples 506790->536749, edges 308->372, drops tang 0, i2c_err tang 0
- [ok] P_idle = 0.169899 W (13426 mau, do lech chuan 0.00199 W)

## Cua so nen

| loai | bat dau us | ket thuc us | so mau | P_mean W | co mau tu bat dau |
|---|---|---|---|---|---|
| init | 1017052937 | 1024052937 | 3495 | 0.170090077 | co |
| rest | 1027793145 | 1029193145 | 699 | 0.170209589 | co |
| rest | 1055552773 | 1056952773 | 700 | 0.170175427 | co |
| gap | 1030694123 | 1032234598 | 770 | 0.170108193 | co |
| gap | 1034054695 | 1035454555 | 699 | 0.170227256 | co |
| gap | 1037274828 | 1038674513 | 699 | 0.170161335 | co |
| gap | 1040494697 | 1041894467 | 699 | 0.170137543 | co |
| gap | 1043714768 | 1045114428 | 699 | 0.170149615 | co |
| gap | 1046934719 | 1048334380 | 699 | 0.170167091 | co |
| gap | 1058453758 | 1059994231 | 769 | 0.169038752 | co |
| gap | 1060693213 | 1062094201 | 700 | 0.169048644 | co |
| gap | 1062793190 | 1064194171 | 699 | 0.169146892 | co |
| gap | 1064893151 | 1066294142 | 700 | 0.16906061 | co |
| gap | 1066993121 | 1068394116 | 699 | 0.169973598 | co |
| gap | 1069093096 | 1070494085 | 700 | 0.170099144 | co |

P_idle_mean = 0.169899335 W, do lech chuan = 0.00198698239 W, 13426 mau.

## Xung rong (EMP)

Xung rong ~1 ms voi chu ky INA226 ~2.2 ms: nhieu xung co 0-1 mau. Day chi la so do, khong tru vao dau ca.

| pulse | cfg | do rong ms | so mau | E_raw mJ | E_net mJ |
|---|---|---|---|---|---|
| 1 | mamba | 1.009 | 0 |  |  |
| 2 | mamba | 1.003 | 0 |  |  |
| 3 | mamba | 1.002 | 0 |  |  |
| 4 | mamba | 1.003 | 0 |  |  |
| 5 | mamba | 1.003 | 0 |  |  |
| 6 | mamba | 1.002 | 1 | 0.172919868 | 0.00268073406 |
| 7 | mamba | 1.003 | 1 | 0.173417321 | 0.00300828742 |
| 8 | mamba | 1.003 | 1 | 0.174984164 | 0.00457513014 |
| 9 | mamba | 1.002 | 1 | 0.173500057 | 0.00326092338 |
| 10 | mamba | 1.003 | 1 | 0.170310936 | -9.80976148e-05 |
| 17 | mlp | 1.004 | 1 | 0.170058273 | -0.000520659794 |
| 18 | mlp | 1.002 | 1 | 0.168909394 | -0.00132973962 |
| 19 | mlp | 1.003 | 1 | 0.168285033 | -0.0021240009 |
| 20 | mlp | 1.002 | 1 | 0.166999081 | -0.00324005262 |
| 21 | mlp | 1.002 | 1 | 0.166825454 | -0.00341368044 |
| 22 | mlp | 1.003 | 0 |  |  |
| 23 | mlp | 1.003 | 0 |  |  |
| 24 | mlp | 1.002 | 0 |  |  |
| 25 | mlp | 1.003 | 0 |  |  |
| 26 | mlp | 1.003 | 0 |  |  |

## Gia dinh va cach tinh

- Hai dong ho khac nhau (XIAO va devkit): ghep bang so thu tu xung, khong bang thoi gian. Do rong xung logger so voi devkit (+-20%%) va khoang cach hai xung lien tiep (2 ms + 0.1%%) la kiem tra lech timer/GPIO.
- Phien duoc coi la toan bo doan capture: capture phai bat dau truoc lenh START va dung sau SESSION_DONE; xung thua ben ngoai phien se bi bao la thua.
- Thoi diem mau = ngay sau khi doc xong thanh ghi bus; chua bu tre chuyen doi (<= ~1 chu ky + thoi gian doc I2C).
- E: tich phan hinh thang P(t) giua cac mau trong [canh len, canh xuong]; hai doan bien giu gia tri mau gan nhat; P_mean = E_raw / thoi luong; V_mean, I_mean la trung binh mau.
- Cua so nen: (init) 10 s nghi dau phien suy tu xung dau tien va do dai khoi 0 (20 luot on dinh ~ 2 x khoi 0 bi loai vi CPU dang tinh), bo 2 s dau va 1 s cuoi; (rest) 2 s truoc xung rong dau moi cau hinh; (gap) khoang nghi >= 1.6 s giua hai xung cung cau hinh. Moi doan bo 300 ms hai dau. Brief 08 viet cua so dau la 'ACK+2 s den xung dau - 1 s'; cua so do chua 20 luot on dinh (CPU dang tinh) nen khong dung lam nen.
- few_samples: khoi < 20 mau; saturated: |shunt_raw| >= 32767; i2c_gap: dong X trong khoi hoac khoang cach hai mau lien tiep > 3 x chu ky trung vi.
- Cac nguong tren la quy uoc cua code ghep, khong phai nguong cua phep do.


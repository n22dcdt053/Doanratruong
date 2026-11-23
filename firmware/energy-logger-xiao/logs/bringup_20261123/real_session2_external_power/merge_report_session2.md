# Bao cao ghep - phien 2

**Trang thai phien: HOP LE (qua cac kiem tra duoi day).** Day la so do CHUA HIEU CHINH; khong co danh gia do chinh xac.

- logger: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\real_s2\s2_logger.csv` (sha256 `3a4b5b9624028eb8ff40454f92690762e9fabbda544c3dfcdf76a6d6861b2a7b`)
- devkit: `C:\Users\ADMIN\AppData\Local\Temp\claude\350e057eb50d49a0\aec9e33d-1b62-4e26-bbdb-9a714cf09de7\scratchpad\real_s2\s2_devkit.txt` (sha256 `35ede0d8f2938f0e1d16fe3f6100929d434130b93bb207b7e6c621556458f2a5`)
- R_shunt dung de tinh: **0.1 ohm, danh nghia, chua do**
- order=LF seed=43

## Kiem tra

- [ok] tieu de logger: # fw=a123742 cfg=0x4127 avg=1 vct_us=1100 rshunt_nominal_ohm=0.1 marker_gpio=1 ina_addr=0x44 mfr_id=0x5449 die_id=0x2260 fw_tree=clean
- [ok] devkit ACK: ACK session=2 order=LF seed=43
- [ok] devkit: 32 dong EMP/BLK
- [ok] devkit: co SESSION_DONE session=2
- [ok] devkit: pulse lien tuc tu 1
- [ok] devkit: cfg/kind/block + idx khop pulse_plan(LF) va hoan vi seed=43 (schedule.py)
- [ok] logger: 32 xung (len+xuong)
- [ok] 34184 mau S, chu ky trung vi 2000 us
- [ok] STAT dau->cuoi: samples 391951->421909, edges 116->180, drops tang 0, i2c_err tang 0
- [ok] P_idle = 0.170114 W (13424 mau, do lech chuan 0.00214 W)

## Cua so nen

| loai | bat dau us | ket thuc us | so mau | P_mean W | co mau tu bat dau |
|---|---|---|---|---|---|
| init | 785648269 | 792648269 | 3495 | 0.170124935 | co |
| rest | 794146221 | 795546221 | 699 | 0.170305887 | co |
| rest | 817385915 | 818785915 | 699 | 0.170079585 | co |
| gap | 797047201 | 798587671 | 769 | 0.170168099 | co |
| gap | 799286648 | 800687642 | 700 | 0.170028988 | co |
| gap | 801386633 | 802787613 | 699 | 0.170220255 | co |
| gap | 803486593 | 804887586 | 700 | 0.170115779 | co |
| gap | 805586565 | 806987558 | 699 | 0.170035125 | co |
| gap | 807686537 | 809087528 | 700 | 0.169969343 | co |
| gap | 820286895 | 821827371 | 770 | 0.170133767 | co |
| gap | 823647410 | 825047325 | 699 | 0.170116004 | co |
| gap | 826867708 | 828267282 | 699 | 0.170138761 | co |
| gap | 830087450 | 831487240 | 699 | 0.170069198 | co |
| gap | 833307449 | 834707199 | 699 | 0.170065341 | co |
| gap | 836527514 | 837927153 | 698 | 0.170078793 | co |

P_idle_mean = 0.170113518 W, do lech chuan = 0.00213923877 W, 13424 mau.

## Xung rong (EMP)

Xung rong ~1 ms voi chu ky INA226 ~2.2 ms: nhieu xung co 0-1 mau. Day chi la so do, khong tru vao dau ca.

| pulse | cfg | do rong ms | so mau | E_raw mJ | E_net mJ |
|---|---|---|---|---|---|
| 1 | mlp | 1.008 | 1 | 0.169609829 | -0.0018645979 |
| 2 | mlp | 1.000 | 1 | 0.168415875 | -0.00169764326 |
| 3 | mlp | 1.003 | 1 | 0.168938424 | -0.00168543444 |
| 4 | mlp | 1.005 | 0 |  |  |
| 5 | mlp | 1.000 | 0 |  |  |
| 6 | mlp | 1.000 | 0 |  |  |
| 7 | mlp | 1.000 | 0 |  |  |
| 8 | mlp | 1.007 | 0 |  |  |
| 9 | mlp | 1.008 | 0 |  |  |
| 10 | mlp | 1.001 | 0 |  |  |
| 17 | mamba | 1.002 | 0 |  |  |
| 18 | mamba | 1.000 | 0 |  |  |
| 19 | mamba | 0.999 | 0 |  |  |
| 20 | mamba | 1.001 | 0 |  |  |
| 21 | mamba | 0.998 | 0 |  |  |
| 22 | mamba | 1.002 | 1 | 0.168639356 | -0.00181438979 |
| 23 | mamba | 1.007 | 1 | 0.169537891 | -0.00176642226 |
| 24 | mamba | 1.008 | 1 | 0.169785 | -0.0016894264 |
| 25 | mamba | 0.999 | 1 | 0.168151992 | -0.00179141255 |
| 26 | mamba | 0.995 | 1 | 0.168304716 | -0.00095823426 |

## Gia dinh va cach tinh

- Hai dong ho khac nhau (XIAO va devkit): ghep bang so thu tu xung, khong bang thoi gian. Do rong xung logger so voi devkit (+-20%%) va khoang cach hai xung lien tiep (2 ms + 0.1%%) la kiem tra lech timer/GPIO.
- Phien duoc coi la toan bo doan capture: capture phai bat dau truoc lenh START va dung sau SESSION_DONE; xung thua ben ngoai phien se bi bao la thua.
- Thoi diem mau = ngay sau khi doc xong thanh ghi bus; chua bu tre chuyen doi (<= ~1 chu ky + thoi gian doc I2C).
- E: tich phan hinh thang P(t) giua cac mau trong [canh len, canh xuong]; hai doan bien giu gia tri mau gan nhat; P_mean = E_raw / thoi luong; V_mean, I_mean la trung binh mau.
- Cua so nen: (init) 10 s nghi dau phien suy tu xung dau tien va do dai khoi 0 (20 luot on dinh ~ 2 x khoi 0 bi loai vi CPU dang tinh), bo 2 s dau va 1 s cuoi; (rest) 2 s truoc xung rong dau moi cau hinh; (gap) khoang nghi >= 1.6 s giua hai xung cung cau hinh. Moi doan bo 300 ms hai dau. Brief 08 viet cua so dau la 'ACK+2 s den xung dau - 1 s'; cua so do chua 20 luot on dinh (CPU dang tinh) nen khong dung lam nen.
- few_samples: khoi < 20 mau; saturated: |shunt_raw| >= 32767; i2c_gap: dong X trong khoi hoac khoang cach hai mau lien tiep > 3 x chu ky trung vi.
- Cac nguong tren la quy uoc cua code ghep, khong phai nguong cua phep do.


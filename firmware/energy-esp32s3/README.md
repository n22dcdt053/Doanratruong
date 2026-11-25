# energy-esp32s3 — firmware đo năng lượng cho devkit ESP32-S3

Firmware cho **bo được đo** (devkit ESP32-S3-WROOM-1 N16R8). Một firmware chứa cả **Mamba huấn luyện lại (seed 42)** và **MLP 561-64-6**,
chạy theo phiên do PC ra lệnh, và kéo chân marker lên cao đúng trong lúc chạy một khối 10 suy luận.
Logger (INA226 + XIAO ESP32S3, Brief 08) bắt cạnh marker và đo dòng. Ghép hai nguồn ở PC cho ra năng lượng theo khối.

**Trạng thái:** chỉ build trên PC. **Chưa nạp bo, chưa nối dây, chưa đo.** Không có kết luận về mô hình nào tốt hơn hay hiệu quả hơn.

## Chân

| Chức năng | Chân devkit | Ghi chú |
|---|---|---|
| Marker ra | `GPIO4` (`ENERGY_MARKER_GPIO`, đổi được lúc build) | Mức thấp khi rảnh. Nối tới `D0` (GPIO1) của XIAO. |
| Console | UART0: `GPIO43` TX, `GPIO44` RX, 115200 8N1 | Qua adapter USB-TTL 3,3 V ngoài. Chỉ nối TX, RX, GND; **không** nối VCC của adapter. |

Không dùng GPIO 0, 3, 19, 20, 26–37, 43/44 (trừ UART0), 45, 46, 47, 48 cho marker (có `#error` lúc build).

## Giao thức (Brief 07, mục 3 — chép nguyên văn)

**Chân.** Marker ra: `ENERGY_MARKER_GPIO = 4` (macro, đổi được lúc build). Console: UART0 mặc định (GPIO43 TX, GPIO44 RX), 115200 8N1, qua adapter USB-TTL bên ngoài. **Không dùng GPIO 0, 3, 19, 20, 26–37, 43/44 (trừ UART0), 45, 46, 47, 48 cho marker.**

**Marker.** Mức thấp khi rảnh. Mỗi **khối 10 suy luận** = **một xung duy nhất** (lên cao ngay trước suy luận đầu, xuống thấp ngay sau suy luận cuối). Ghi `esp_timer_get_time()` ngay sau khi kéo lên và ngay trước khi kéo xuống (hai giá trị này in ra **sau** vùng đo, mục dưới). Cho phép thêm **xung rỗng** (không suy luận) để đo chi phí marker, mục "Phiên".

**Lệnh bắt đầu phiên** (từ PC, qua UART0, một dòng ASCII kết thúc `\n`):
```
START <session 1..5> <order MF|LF> <seed uint32>\n
```
`MF` = Mamba đo trước, MLP sau; `LF` = MLP trước. Firmware chờ lệnh này sau khi boot (in `READY fw=<commit> gpio=4` mỗi 2 s khi chờ). Lệnh sai/thiếu → in `ERR <lý do>` và tiếp tục chờ. Đúng → in `ACK session=<s> order=<o> seed=<seed>` rồi chạy.

**Một phiên** (theo thứ tự, tất cả **không in log trong vùng marker cao**):
1. Nghỉ nền 10 s (marker thấp, `vTaskDelay`), để Brief 08 đo công suất nền.
2. Hoán vị 60 mẫu bằng `xorshift32` (mục lập lịch bên dưới), **cùng một hoán vị cho cả hai cấu hình trong phiên**.
3. Với từng cấu hình theo `order`:
   a. 20 lượt chạy ổn định (không marker, không in), rồi nghỉ 2 s.
   b. 10 xung rỗng (marker lên/xuống liên tiếp, nghỉ 100 ms giữa hai xung), in kết quả sau.
   c. 6 khối: khối `b` (0..5) dùng các mẫu ở vị trí `10b…10b+9` của hoán vị. **Trước khi kéo marker lên**, chép 10 mẫu vào bộ đệm RAM (đầu vào "nạp sẵn"; Mamba: 561 + 9 số 0 = 570) và chuẩn bị mảng kết quả. Kéo marker lên → 10 lần `…forward_logits` → kéo xuống. Chỉ **sau đó** mới in một dòng `BLK` (dưới) và so logit với tham chiếu. Nghỉ 2 s (marker thấp) giữa các khối.
   d. Nghỉ 5 s sau cấu hình.
4. In `SESSION_DONE session=<s>` rồi quay lại chờ lệnh (in `READY`).

**Dòng in sau mỗi khối** (một dòng, các trường cách nhau một dấu cách):
```
BLK s=<session> b=<block 0..5> cfg=<mamba|mlp> pulse=<số xung thứ tự trong phiên, từ 1, tính cả xung rỗng> t_rise_us=<u64> t_fall_us=<u64> n=10 idx=<10 chỉ số 0..59 cách nhau dấu phẩy> pred=<10 nhãn> ref=<10 nhãn tham chiếu host> maxdl=<max|Δlogit| so tham chiếu, %.3e> invalid=<số lần trả -2>
```
Xung rỗng: `EMP s=<..> cfg=<..> pulse=<..> t_rise_us=<..> t_fall_us=<..>`. Mỗi cấu hình tạo đúng 10 `EMP` rồi 6 `BLK`; mỗi phiên tạo 32 xung (2 × 16) và 2 × 16 dòng `EMP/BLK`. **Số xung và thứ tự `pulse` là khóa nối với dữ liệu logger.**

**Lập lịch** (`src/energy_sched.h/.c`, hàm thuần, không phụ thuộc ESP-IDF):
```c
uint32_t xorshift32(uint32_t *s);                       // x^=x<<13; x^=x>>17; x^=x<<5 (uint32). seed 0 → dùng 1.
void energy_permutation(uint32_t seed, uint8_t perm[60]); // perm[i]=i; i từ 59 xuống 1: j = xorshift32(&s) % (i+1); đổi perm[i], perm[j]
```
`test/sched_host.c` (gcc, không ESP-IDF) in hoán vị cho seed 1, 42, 123456789 và `START` với mọi `session 1..5 × order MF/LF`; kết quả lưu ở `test/sched_expected.txt` (Brief 08 so với bản Python). Chạy: `bash firmware/energy-esp32s3/test/run_sched_host.sh`.

## Điều firmware làm thêm hoặc chọn khi brief chưa ghi (đã thực hiện, cần người kiểm tra biết)

- **Xung rỗng rộng khoảng 1 ms** (`ENERGY_EMPTY_PULSE_US`, `esp_rom_delay_us`). Brief không ghi độ rộng; xung vài µs thì ISR của logger không tách được hai cạnh. `EMP` ghi `t_rise_us`/`t_fall_us` thực.
- **Nghỉ thêm 2 s sau 10 xung rỗng, trước khối 0**, để có khoảng nền yên giữa xung rỗng cuối và khối đầu. Giữa các khối nghỉ 2 s (5 lần mỗi cấu hình, không nghỉ sau khối 5); sau khối 5 nghỉ 5 s.
- `energy_sched.c` biên dịch thành tệp riêng (`src/CMakeLists.txt` quét mọi tệp trong `src/`); `main.c` chỉ include `energy_sched.h`.
- Marker bằng `gpio_set_level`; chưa đo độ trễ của lời gọi này (không thêm vùng đo).
- Vòng chờ lệnh và các phiên chạy trong **task riêng stack 8 KB** (lõi 0); stack của `app_main` chỉ 3584 B và `sdkconfig.esp32s3` phải giữ byte-identical.
- Mã khởi động (`esp_reset_reason()` và đếm boot `RTC_NOINIT`) chỉ in lúc boot, theo cách của `mamba-retrained-esp32s3/src/main.c`.

## Build (trên PC)

```powershell
cd firmware\energy-esp32s3
pio run -j 1
```

`scripts/gen_build_info.py` sinh `src/build_info.h` (commit, clean/dirty, UTC) mỗi lần build; dòng đầu console in lại các giá trị này.
Cấu hình build **giống hệt** `firmware/mamba-retrained-esp32s3`: `sdkconfig.esp32s3` byte-identical (sha256 `9d48f45c0d4aef6ac07f5656ef7eb1353ef0f82aeba10b36637456b76c42cfeb`), `-Og`, 160 MHz, cùng platform, framework và board.
Wi-Fi, Bluetooth, PSRAM đều tắt.

## Nạp bo — dành cho người kiểm tra

```powershell
cd firmware\energy-esp32s3
pio run -t upload --upload-port <COM>
```

Dùng cổng USB-C UART/CH343 của devkit. **Nạp xong phải rút USB khỏi devkit trước khi đo**: dòng điện phải đi qua INA226, không được có đường cấp nguồn USB song song. Không có `flash_and_log.ps1` ở project này (script nạp và bắt log đo năng lượng sẽ làm sau, vì phải rút USB khi đo).

## Giới hạn

- Build `-Og` ở 160 MHz: số đo không đại diện hiệu năng thật. Chỉ một bo.
- INA226 lấy mẫu cỡ ms nên **chỉ cho năng lượng trung bình theo khối** nhiều suy luận, không thấy dòng từng phép toán.
- 60 mẫu lấy từ tập validation (`split == val`), 10 mẫu mỗi lớp, chọn theo nhãn và seed 42 (`ml/gen_energy_samples.py`), không chọn theo kết quả mô hình.
- `maxdl` là số đo so với logit host; ngưỡng sai số chờ GVHD xác nhận, không ghi "đạt".

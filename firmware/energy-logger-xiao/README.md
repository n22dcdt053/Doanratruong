# energy-logger-xiao — logger đo năng lượng (INA226 + XIAO ESP32S3)

Firmware cho **bo logger** (Seeed XIAO ESP32S3), **không phải bo được đo**. Nó đọc INA226 qua I2C và bắt cạnh lên/xuống của chân marker
từ devkit, gán cả hai vào **cùng một đồng hồ `esp_timer` (µs)**, và gửi ra PC qua USB-CDC. PC ghép với log UART của devkit
(firmware `firmware/energy-esp32s3`, Brief 07) bằng `tools/energy/` để ra năng lượng theo khối.

**Trạng thái:** chỉ build trên PC. **Chưa nạp bo XIAO, chưa nối dây, chưa có số đo thật.** README này không đánh giá độ chính xác của hệ đo.

## Chân

| Chức năng | XIAO | GPIO | Ghi chú |
|---|---|---|---|
| I2C SDA (INA226) | D4 | 5 | 400 kHz. Địa chỉ INA226 là macro `LOGGER_INA226_ADDR` (mặc định 0x40 = A0 và A1 nối GND; `platformio.ini` đang đặt 0x44 cho module trên bàn đo, xem dưới). Bật thêm pull-up nội bộ (module thường đã có pull-up riêng). |
| I2C SCL (INA226) | D5 | 6 | |
| Marker vào (từ devkit `GPIO4`) | D0 | 1 | Đầu vào, kéo xuống nội bộ, ngắt cả hai cạnh. |
| Tự kiểm ra | D3 | 4 | Lệnh `T`. Không dùng D2 (GPIO3) vì là chân strapping. |
| INA226 `VCC` | 3V3-OUT | — | Không cần mã. **Không** cấp 5 V cho VCC module (pull-up I2C sẽ đưa 5 V vào GPIO XIAO, không chịu 5 V). |

Các chân là macro (`LOGGER_SDA_GPIO`, `LOGGER_SCL_GPIO`, `LOGGER_MARKER_GPIO`, `LOGGER_SELFTEST_GPIO`) đổi được lúc build.
Nguồn đo: 5 V → INA226 (shunt 0,1 Ω, đo phía cao, `VIN+` phía nguồn, `VIN−` về 5V của devkit) → devkit. GND chung giữa nguồn, INA226, XIAO, devkit.
Marker devkit (`GPIO4`) nối **D0** của XIAO. Bảng chân devkit: `firmware/energy-esp32s3/README.md`.

## INA226

- Ghi cấu hình vào thanh ghi `0x00`: `AVG = 1`, `VBUSCT = VSHCT = 1,1 ms`, `MODE = 111` (shunt + bus, liên tục) → giá trị **`0x4127`**, chu kỳ chuyển đổi ≈ 2,2 ms.
  (`0x4127` cũng là giá trị mặc định sau reset; firmware vẫn ghi lệnh reset `0x8000`, chờ 2 ms, ghi cấu hình và đọc lại để kiểm.)
- Đọc `0xFE` (Manufacturer ID, kỳ vọng `0x5449`) và `0xFF` (Die ID). Sai/không đọc được → in `ERR ina226_id` và **không đo** (cần reset bo sau khi sửa dây).
  Dòng `ERR` lúc boot có thể mất nếu chưa có ai mở cổng USB, nên lý do lỗi được **lặp lại mỗi 5 s** cùng `STAT`: `# fw=… ERR ina226 (khong do) reason=… i2c_esp_err=… value=0x…` rồi `ERR …` (`i2c_esp_err=259` là `ESP_FAIL`, tức INA226 không trả lời ACK ở 0x40). Đọc lại cấu hình sai → `ERR ina226_cfg` và không đo.
- Lấy mẫu: poll thanh ghi Mask/Enable `0x06` (việc đọc xóa cờ CVRF); khi CVRF = 1 thì đọc `0x01` (shunt) rồi `0x02` (bus). Thời điểm mẫu = `esp_timer_get_time()` **ngay sau khi đọc xong `0x02`**.
- **Chỉ ghi mã thô.** Không dùng thanh ghi calibration/current/power. Quy đổi ở PC: `V_shunt = raw · 2,5 µV` (số có dấu 16 bit), `V_bus = raw · 1,25 mV`, `I = V_shunt / R_shunt`.
  `R_shunt = 0,1 Ω` là **giá trị danh nghĩa, chưa đo**; ghi trong dòng tiêu đề.

## Định dạng đầu ra (USB-CDC, CSV, một dòng/bản ghi, `\n`)

| Dòng | Ý nghĩa |
|---|---|
| `S,<t_us>,<shunt_raw>,<bus_raw>` | một mẫu INA226 (`shunt_raw` là số có dấu) |
| `E,<t_us>,<level 0\|1>` | một cạnh marker (1 = lên); mức đọc ngay trong ISR |
| `X,<t_us>,<mã>` | lỗi I2C (`esp_err_t`, ví dụ 263 = `ESP_ERR_TIMEOUT`, 259 = `ESP_FAIL`) |
| `STAT,<t_us>,samples=<n>,edges=<n>,drops=<n>,i2c_err=<n>` | mỗi 5 s, bộ đếm **tích lũy** từ lúc khởi động |
| `# fw=<commit> cfg=0x4127 avg=1 vct_us=1100 rshunt_nominal_ohm=0.1 marker_gpio=1 mfr_id=0x… die_id=0x… fw_tree=<clean\|dirty>` | tiêu đề |
| `PING,<t_us>` / `SELFTEST_DONE` / `ERR <lý do>` | trả lời lệnh / lỗi |

Lệnh từ PC (một ký tự + `\n`): `P` → `PING,<t_us>`; `T` → tự kiểm: **20 xung trên D3 (GPIO4), mỗi xung cao 1 ms rồi thấp 4 ms**, rồi in `SELFTEST_DONE` (nối dây D3→D0 để thấy 20 cặp `E` tương ứng). Ký tự khác → `ERR cmd`.
Không Wi-Fi/BT. Không in gì ngoài các dòng trên.

### Điều firmware làm thêm hoặc chọn khi brief chưa ghi

- **Dòng tiêu đề lặp lại sau mỗi dòng `STAT`** (ngoài lần in lúc khởi động), vì capture có thể mở cổng sau khi XIAO đã chạy. Có thêm `mfr_id`, `die_id`, `fw_tree` ở **cuối** dòng (phần đầu đúng như brief).
- Cổng USB Serial/JTAG ghi qua driver `usb_serial_jtag` (ring TX 8 KB). **Khi chưa có chương trình nào mở cổng**, dữ liệu không được lấy đi: vòng đệm đầy rồi bản ghi bị bỏ và **tăng `drops`**. Vì vậy `drops` tích lũy trước khi capture bắt đầu là bình thường; `merge_blocks.py` chỉ xét phần tăng giữa dòng `STAT` đầu và cuối trong tệp. Hậu quả phụ: vài trăm dòng đầu mở cổng có thể là dữ liệu cũ (thời gian `t_us` nhỏ hơn).
- Hàng đợi 2048 bản ghi; mẫu từ task đọc (lõi 1, ưu tiên 20), cạnh từ ISR (IRAM, `gpio_ll_get_level` + `xQueueSendFromISR`), task in ở lõi 0.
- Có tiếng "rác" trước giao thức: ROM bootloader của ESP32-S3 in vài dòng khi reset; log ESP-IDF và bootloader đã tắt. Các dòng này, và dòng panic nếu có, vào `bad_lines` của `capture.py`.
- `gpio` marker cấu hình kéo xuống nội bộ; nếu devkit chưa cấp nguồn, đầu vào ở mức thấp.
- `sdkconfig.defaults` **không** liên quan `sdkconfig.esp32s3` của devkit (khác bo): console = USB Serial/JTAG, log tắt, `-O2`, tick 1 kHz, flash 8 MB, không PSRAM, bỏ kiểm idle task lõi 1 của watchdog. `board = seeed_xiao_esp32s3` có trong `espressif32 @ 6.9.0`.

## Build (trên PC)

```powershell
cd firmware\energy-logger-xiao
pio run -j 1
```

`scripts/gen_build_info.py` sinh `src/build_info.h` (commit, clean/dirty, UTC) mỗi lần build. `sdkconfig.seeed_xiao_esp32s3` do PlatformIO sinh ra, đã bỏ qua trong git.

## Nạp bo — dành cho người kiểm tra

```powershell
cd firmware\energy-logger-xiao
pio run -t upload --upload-port <COM>
```

XIAO là **bo logger riêng**: chỉ nạp vào XIAO ESP32S3 dùng làm logger. **Không nạp firmware dự án vào bo khác.**
Nếu XIAO không vào chế độ nạp, giữ nút **B** (boot) khi cắm USB. Sau khi nạp, cổng USB của XIAO là cổng COM mà `tools/energy/capture.py` dùng.

## Giới hạn

- INA226 lấy mẫu cỡ 2,2 ms: chỉ cho **năng lượng trung bình theo khối nhiều suy luận**, không thấy dòng từng phép toán. Xung rỗng ~1 ms chỉ có 0–1 mẫu.
- `R_shunt` danh nghĩa, **chưa đo**; chưa đối chiếu hệ đo bằng tải ổn định/đồng hồ chuẩn; một bo; điều kiện đo phải ghi lại.
- Thời điểm mẫu là sau khi đọc xong thanh ghi bus, chưa bù trễ chuyển đổi (cỡ một chu kỳ + thời gian đọc I2C).
- Chưa thử trên bo: hành vi mở cổng USB Serial/JTAG (DTR/RTS có thể reset XIAO), tốc độ thực của vòng poll, độ trễ ISR, việc hàng đợi có tràn không khi host đọc chậm.
- **Không cắm USB của devkit khi đang cấp nguồn qua INA226** (hai đường cấp nguồn song song làm sai phép đo và có thể ngược dòng qua INA226).

## Địa chỉ I2C của module INA226 trên bàn đo (23/11/2026)

Quét I2C trên bo thật thấy **một thiết bị ở 0x44**, không phải 0x40; đọc ID cho `mfr_id=0x5449`, `die_id=0x2260`, tức INA226 với chân A1 nối VCC và A0 nối GND. `platformio.ini` đặt `-DLOGGER_INA226_ADDR=0x44` cho module này. Nếu nối A0 và A1 xuống GND thì bỏ dòng `build_flags` (địa chỉ về 0x40). Khi INA226 không trả lời, dòng lỗi lặp lại mỗi 5 s có thêm `scan=<các địa chỉ thấy>` và mức `sda`/`scl` để chẩn đoán.

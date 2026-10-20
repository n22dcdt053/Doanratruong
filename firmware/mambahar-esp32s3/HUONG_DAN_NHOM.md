# Hướng dẫn nhóm — chạy Mamba HAR trên ESP32-S3 (proxy)

Mục tiêu: từ máy sạch → clone → build → nạp → đọc log → lấy bằng chứng.
Phạm vi: **ESP32-S3 chỉ là proxy** (Xtensa / ESP-IDF / build C), **không** thay nghiệm thu Portenta H7.
Chi tiết kỹ thuật và số liệu: [README.md](README.md).

## 0. Cần có

- Windows + PowerShell, Git.
- VS Code + extension **PlatformIO IDE** (hoặc `pip install platformio`).
- Driver USB-UART **CH343** (Windows 10/11 thường tự nhận; không thấy COM thì cài driver của board).
- Cáp USB-C **data** (cáp sạc không truyền được).
- Bo ESP32-S3-WROOM-1 N16R8 (DevKitC-1), PSRAM tắt.

## 1. Clone đúng nhánh + upstream

```powershell
git clone https://github.com/n22dcdt053/Doanratruong.git
cd Doanratruong
git switch dev
```

Repo **không chứa** upstream MambaLite-Micro (cố ý, để nguyên bản gốc). Firmware include trực tiếp từ đó, nên phải clone đúng commit:

```powershell
git clone https://github.com/Whiten-Rock/MambaLite-Micro.git MambaLite-Micro
git -C MambaLite-Micro checkout 44d51fce0f17ddadb6111c5e5554d1f7f6c67aff
git -C MambaLite-Micro rev-parse --short HEAD
```

Kết quả phải là `44d51fc`. **Không sửa file nào** trong `MambaLite-Micro/`; mọi thay đổi làm ở `firmware/common/`.

## 2. Cắm bo, tìm cổng

- Dùng cổng **USB-UART** (chip CH343), không phải cổng USB native/OTG.
- `pio device list` → lấy `COMx` (ngày 20/10 là COM11; máy khác có thể khác).
- Không thấy cổng: đổi cáp data, thử cổng USB khác, hoặc giữ **BOOT** khi cắm.

## 3. Build + nạp + bắt log (một lệnh)

```powershell
cd firmware\mambahar-esp32s3
powershell -ExecutionPolicy Bypass -File .\scripts\flash_and_log.ps1 -Port COMx -DurationSec 155
```

- Thay `COMx`; máy chỉ có một cổng USB thì bỏ `-Port`.
- Tổng ~3 phút: build (lần đầu 3–5 phút) + 155 s chạy 1.000 lượt.
- Script lưu 3 file vào `logs\`: `build_*.txt`, `upload_*.txt`, `esp32s3_har_*.txt`.
- Muốn xem lại log mà không nạp: `-SkipBuild -SkipUpload`, nhưng **phải bấm RST** sau khi capture bắt đầu — firmware chỉ in một lần lúc boot.
- `-SkipBuild` chỉ bỏ bước build riêng; lúc nạp PlatformIO vẫn rebuild nếu cần.

## 4. Log đúng trông thế nào

Các dòng khóa (log thật 20/10):

```text
FW commit <sha> (clean) built <UTC> | opt=debug(-Og)
Reset: reason=1 (POWERON) | boot #1 since RTC_NOINIT init
Test start: boot #1 | free heap 385668 bytes
BENCH DONE: runs=1000 samples=20 invalid=0 label_mismatch=0
proxy numerics (Xtensa/ESP-IDF/C; NOT tier-B): comparisons=6000 max|dlogit|=7.629e-06 MAE=9.157e-07
time_us: min=122165 p50=122230 p95=122265 max=122505 mean=122228 sd=30
Resets: boot_start=1 boot_end=1 | no reset during test
```

- Đúng **một** dòng `Test start`; `boot_start == boot_end`.
- `invalid=0`, `label_mismatch=0`, `comparisons=6000`.
- `max|dlogit|` cỡ `7.6e-06`, MAE cỡ `9.2e-07` (1 ULP float32).
- p50 cỡ `122230 us`; heap 21 mốc phẳng `385668`.
- Khác các mốc trên: **giữ log, báo lại**, không tự sửa hay chạy lại để "cho đẹp".

## 5. Quy trình lấy bằng chứng (bắt buộc)

1. Commit code trước.
2. Chạy script **một lần** (build + nạp + log).
3. Commit 3 file log vừa sinh.
4. Báo trong nhóm: commit hash + đường dẫn log + các dòng khóa ở mục 4.

Không sửa log, không ghép log từ nhiều lần chạy, không đổi ngưỡng sau khi xem số.

## 6. Lỗi thường gặp

| Hiện tượng | Xử lý |
|---|---|
| `port is closed`, `Write timeout` | Rút/cắm lại USB, chạy lại; script tự mở lại cổng và vẫn lưu phần đã bắt. |
| `No serial data received` | Sai COM hoặc cáp sạc; kiểm `pio device list`, bấm RST sau khi capture mở. |
| Build chết ở `esp_lcd_panel_rgb.c` / `ira` | ICE của xtensa-gcc; chạy lại (script đã dùng `-j 1`). |
| Upload fail | Giữ **BOOT** khi cắm, thử cáp/ cổng khác. |
| Log có **2** dòng `Test start` | Bo bị reset giữa chừng; chạy lại, không dùng log đó. |
| Có `task_wdt` | Không sửa vòng lặp; giữ log và báo. |

## 7. Giới hạn — đừng nói quá

- Đây là **proxy**, không phải tier-B. Tier-B cần Portenta H7 (build C++) + ngưỡng GVHD xác nhận.
- 20 mẫu luân phiên, không phải 1.000 mẫu khác nhau; `host_pred` là dự đoán host, không phải nhãn thật.
- 122 ms là build `-Og`; chưa có số `-O2`/`-Os`.
- Không đưa số ESP32 vào bảng so sánh Mamba↔MLP.

## 8. Quy ước git

- Việc riêng: `git switch -c ten/viec dev` → commit → push → PR vào `dev`.
- Không commit thẳng `main`; không force push.
- `docs/`, `HUONG_PHAT_TRIEN.md`, `YEU_CAU_DE_CUONG.md`, đề cương… bị `.gitignore` chặn (tài liệu nội bộ). Không `git add -f`.

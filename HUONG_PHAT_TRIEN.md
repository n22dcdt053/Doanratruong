# HƯỚNG PHÁT TRIỂN — ĐATN Mamba HAR trên STM32H7

File điều hướng công việc của nhóm. Nguồn: đối chiếu **Đề cương chi tiết** (Bảng 8 — tiêu chí nghiệm thu; Phụ lục A — hồ sơ bàn giao) với trạng thái repo ngày **18/10/2026**.

Cách dùng: tick ✅ vào ô *Trạng thái* khi có minh chứng thật. Mọi thay đổi phạm vi/cấu hình ghi vào **mục 6 — Nhật ký quyết định**, không sửa âm thầm.

---

## 1. Đích "đủ để ra trường"

Đủ = thỏa **9 tiêu chí Bảng 8** + có đủ **hồ sơ tối thiểu Phụ lục A.1**. Không phát minh thêm phạm vi.

| # | Tiêu chí (Bảng 8) | Trạng thái 18/10 | Minh chứng cần |
|---|---|---|---|
| 1 | Nguồn và khả năng tái lập: commit, license, checksum trọng số, môi trường, hướng dẫn build | 🟡 chuỗi commit 18/10; `source_manifest.json` **đã có checksum trọng số + 2 file vendor + 2 file upstream 1:1** — còn thiếu duy nhất: checksum checkpoint retrain (chờ gate #1) | lịch sử commit + `environment/` |
| 2 | Hoạt động trên phần cứng: Portenta H7 thật, nhiều mẫu, xuất logits/nhãn/lỗi | 🟡 20/10: ESP32-S3 (proxy) — **1.000 lượt liên tục, 0 invalid, khớp nhãn 1000/1000**, max\|Δlogit\| **7,6e-6** / MAE **9,2e-7** trên 6.000 so sánh (tier-B tính ngay trên bo); Portenta H7 thật vẫn ❌ | firmware H7 + log nhận gói |
| 3 | Tương đương số học: bảng sai số, tỷ lệ khớp, hồ sơ mẫu khác biệt, dung sai chốt trước | ❌ | `predictions.csv` + bảng sai số |
| 4 | Chất lượng phân loại: accuracy, macro-F1, F1/lớp, confusion matrix trên test + nêu trạng thái checkpoint | 🟡 host C + trọng số công khai: acc **0,9267** / macro-F1 **0,9265** trên 2.947 mẫu test (18/10) — **chỉ dùng MT1/MT3, không đưa vào bảng so sánh Mamba↔MLP** (checkpoint gốc chọn bằng val chia ngẫu nhiên); checkpoint chốt còn ở mục 2 | bảng chỉ số + hình |
| 5 | Đối chứng MLP chạy cùng bo, kiểm chứng riêng | ❌ | firmware MLP + bảng so sánh |
| 6 | Độ ổn định: ≥1.000 lượt không reset ngoài dự kiến, theo dõi bộ nhớ/lỗi đầu vào/NaN | 🟡 host PC: 1000/4000 lượt RSS phẳng sau sửa leak; wrapper báo `-2` khi logits có NaN/inf (18/10); chờ bo thật | nhật ký stability test trên H7 |
| 7 | Năng lượng: dữ liệu nguồn thô, GPIO, sơ đồ cấp nguồn, điều kiện đo, mJ/lượt | ❌ | `raw_measurements/` + `hardware_manifest.md` |
| 8 | Tài nguyên và thống kê: Flash, RAM theo phương pháp, phân bố thời gian, biến thiên giữa phiên | 🟡 có build log ESP32-S3 + Portenta (số PlatformIO, **chưa phải map file**; ESP32 không thay thế H7). RAM 77.256 B = **phần tĩnh (.data+.bss)**; heap đỉnh + stack đo riêng ở P2. Trên bo ESP32-S3 (proxy, 1.000 lượt × 20 mẫu): p50 **123,201 ms**, p95 123,237, max 123,460 @160 MHz; heap cuối 385.540 B, min ever 342.284 B; flash 406.024 B, RAM tĩnh 17.124 B (gồm 4 KB mảng thời gian) | map file + linker script H7 |
| 9 | Báo cáo: phân biệt kết quả / giới hạn / giả thuyết / hướng phát triển | ❌ | thuyết minh 5 chương (mục 13.2) |

---

## 2. Quyết định gate #1 — nguồn checkpoint (CHỐT NGAY)

**Phát hiện (18/10):** script huấn luyện gốc `MambaLite-Micro/Python/train.py` dùng:
- `random_split` 80/20 trên tập train — **không chia theo subject**;
- chọn checkpoint theo **accuracy validation**, 20 epoch, không seed, không early stop.

**Hệ quả:** dùng trọng số công khai cho so sánh Mamba↔MLP (MT5) là **không công bằng** — MLP của nhóm train bằng GroupShuffleSplit seed 42 theo đề cương mục 4.3, Mamba thì không.

**Chốt (đề cương mục 4.4 cho phép):**
- [ ] Huấn luyện lại Mamba đúng **Bảng 2**: Adam, lr 1e-3, batch 64, ≤100 epoch, early stop 10 epoch không cải thiện macro-F1 val, chọn checkpoint macro-F1 cao nhất, seed 42.
- [ ] Trọng số công khai giữ lại chỉ để phục vụ MT1/MT3 (kiểm chứng số học C↔PyTorch↔MCU), ghi rõ trong báo cáo.
- [ ] Kiểm tra cài `mamba_ssm` trên máy Windows trước cuối tuần. Nếu vướng build CUDA/triton → dùng Colab/WSL **một lần** để retrain rồi đóng băng checkpoint (model nhỏ: 7.352 mẫu, seq 10, d_model 64 — CPU cũng train được, không cần GPU).

### Dung sai MT3 — chốt 18/10/2026, **trước khi so số thật** (chờ GVHD xác nhận)

Hai tầng, tách nguồn sai khác mô hình khỏi nguồn sai khác nền tảng:

| Tầng | Cặp so | max&#124;Δlogit&#124; | MAE | Nguồn lệch chấp nhận |
|---|---|---|---|---|
| A | C-PC ↔ PyTorch | ≤ 1e-3 | ≤ 1e-4 | `logf(1+expf)` vs `log1p`; thứ tự cộng dồn; libm khác; trọng số trong header đã làm tròn `%.8f` (~1e-8) |
| B | MCU ↔ C-PC | ≤ 1e-4 | ≤ 1e-5 | **cùng mã nguồn**, chỉ khác libm + trình biên dịch/flags → phải chặt hơn |

Quy tắc nhãn (cả hai tầng): khớp **100% trừ** các mẫu có **biên top-2 < ngưỡng tầng tương ứng** — các mẫu này **liệt kê riêng** thành "hồ sơ mẫu khác biệt" (tiêu chí #3), không tính là sai nhưng không giấu.

Nếu vượt ngưỡng ngay từ lần so đầu → **nghi ánh xạ trọng số trước khi nghi code C** (layout dễ sai chuyển vị/thứ tự chiều hơn là số học từng dòng).

**Layout khi nạp ngược `mamba_weights.h`** (đọc `export_weights.py` + header ngày 18/10):
- Thứ tự mảng trong header = thứ tự `state_dict`: `linear_in.weight (64,57)` → `linear_in.bias (64)` → `mamba.A_log (128,16)` → `mamba.D (128)` → `mamba.in_proj.weight (256,64)` → `mamba.conv1d.weight (128,4)` → `mamba.conv1d.bias (128)` → `mamba.x_proj.weight (36,128)` → `mamba.dt_proj.weight (128,4)` → `mamba.dt_proj.bias (128)` → `mamba.out_proj.weight (64,128)` → `classifier.weight (6,64)` → `classifier.bias (6)`.
- **Không chuyển vị**: mảng 2D ghi theo `.flatten()` row-major = đúng layout PyTorch `[out, in]`; reshape về `(_rows, _cols)` là đủ.
- `conv1d.weight` bị `squeeze(1)` khi export (128,1,4 → 128,4) → khi nạp lại phải `unsqueeze(1)`.
- **Không** map ngược bằng `cname.replace('_','.')` (tên module nhiều `_`: `linear_in`, `A_log`, `in_proj` → sai) — dùng bảng tên tường minh.
- Dùng **trọng số đọc từ header** làm nguồn chuẩn cho MT3 (không dùng `.pth` gốc, vốn lệch ~1e-8 do làm tròn).
- `mamba_ssm` module `Mamba`: `A_log` shape `(d_inner, d_state)`; `dt_proj` Linear(4→128); `x_proj` Linear(128→36) — khớp header, không cần đảo.

**Kỷ luật đã áp dụng**: ngưỡng ghi ở đây ngày **18/10/2026, trước khi nhìn bất kỳ kết quả so nào**. Khi chạy thật giữ nguyên ngưỡng; mọi điều chỉnh sau đó phải có lý do kỹ thuật và dòng nhật ký riêng.

---

## 3. Lộ trình P0 → P4 (mỗi bước ra một minh chứng)

### P0 — Tuần này, không cần bo
- [ ] **Commit toàn bộ repo**; `.gitignore` cho `.pio/`; tách nhánh `dev` (đề cương 6.3 bắt buộc giữ bản gốc chưa sửa + nhánh phát triển). *(18/10: chuỗi commit: `a72d025` baseline + log leak trước sửa → bản vendor sửa → vendor `mamba.c` + kiểm UCI; tag `baseline-upstream-44d51fc` + nhánh `dev` đã tạo; checksum trọng số + 2 vendor + 2 upstream đã ghi trong `source_manifest.json` — còn: checksum checkpoint retrain (gate #1).)*
- [ ] Tải UCI HAR; sinh `split_manifest.csv` (sample_id, subject_id, nhãn, tập) bằng GroupShuffleSplit seed 42; kiểm tra danh sách người không giao nhau giữa các tập. *(18/10: đã tải về `data/UCI HAR Dataset/`; đã chuyển + chấm điểm **tập test** — acc 0,9267, xem mục 6; còn `split_manifest.csv`.)*
- [x] **Vendor wrapper mô hình**: copy `mambahar.c` → `firmware/common/mambahar.c` (1:1, sha256 `84AC465D…`), trỏ ESP32-S3 sang bản vendor; upstream giữ nguyên. *(18/10/2026)*
- [x] **Dựng bản C tham chiếu trên PC**: `MambaLite-Micro/csrc/*.c` + **`firmware/common/mambahar.c`** (dùng chung bản vendor với firmware để MT3 so đúng một nguồn), biên dịch native (gcc), chạy N mẫu, in 6 logits. *(18/10/2026 — `firmware/host/`: `run_host_test.ps1` chạy 1 mẫu/1000/4000 lượt; `--batch` đọc file .f32 → CSV 6 logits; ASan qua `run_asan.sh`. Bằng chứng: `firmware/host/logs/`.)*
- [ ] Đối chiếu logits C-PC ↔ PyTorch (`mamba_ssm` + trọng số công khai) → xác nhận tuyên bố "100% khớp" của paper bằng số liệu của nhóm. *(18/10: repo upstream **không có file `.pth` công khai** (chỉ placeholder trong `train.py`/`export_weights.py`) → phải nạp ngược từ `mamba_weights.h` vào `state_dict` hoặc dùng checkpoint nhóm tự train. Dung sai **đã chốt trước** ngày 18/10/2026 — xem mục 2, "Dung sai MT3"; chờ GVHD xác nhận.)*
- [ ] Huấn luyện lại Mamba (gate #1) → lưu checkpoint + lịch sử train.

### P1 — Firmware (ESP32 tiếp tục, chuyển H7 khi bo về)
- [x] Sửa **`firmware/common/mambahar.c`** (bản vendor — không sửa upstream): forward trả **cả 6 logits** trước softmax (hiện trả `int` argmax); ghi diff so với upstream vào mục 6. *(18/10/2026 — kèm sửa leak 8.128 B/lượt; đối chiếu bit-exact trước/sau: `firmware/host/logs/baseline_logits.csv` ≡ `fixed_logits.csv`; xem mục 6.)*
- [x] **Vendor `csrc/mamba.c`**: sửa 1 dòng vòng chép `xz` (`di < d` thay `di < self->d_inner`) — hết đọc quá biên (ASan), bit-exact giữ nguyên. Diff: `firmware/common/mamba_vs_upstream.diff`. *(18/10/2026)*
- [ ] Giao thức nhận gói PC→MCU: `[sample_id | 570 float | checksum]`; từ chối gói sai độ dài/checksum; quản lý timeout; kiểm đầu vào không hữu hạn/vượt khoảng giá trị → log là **mẫu không hợp lệ**, không đưa vào thống kê (đáp lại yêu cầu "kiểm khoảng giá trị đầu vào" của tồn đọng #2).
- [ ] Bỏ vòng `NVIC_SystemReset` sau 1 mẫu → vòng lặp nhiều mẫu có mã định danh.
- [ ] Thêm GPIO marker bao vùng suy luận; **không in log trong vùng đo**.
- [ ] Chạy thử 1.000 lượt liên tiếp, giám sát reset ngoài dự kiến / đầu ra không hữu hạn / mức dùng bộ nhớ.

### P2 — Đo lường
- [ ] Flash/RAM từ **map file + linker script Portenta H7** (không dùng số ESP32 thay thế); tách riêng **tĩnh (.data+.bss) / heap đỉnh (high-water mark) / stack** / working buffer — **không gộp thành một con số "RAM" duy nhất** trong báo cáo.
- [ ] **Đặt lịch mượn PPK2 ngay** (hoặc chốt phương án INA226 — cần thêm thời gian thiết kế mạch).
- [ ] Bố trí nguồn 1 đường duy nhất, loại USB cấp nguồn song song, kiểm tra cực tính/điện áp/dòng đỉnh.
- [ ] Đo nền + 5 phiên × 6 khối × 10 lượt mỗi cấu hình (mục 9.3); hoán đổi thứ tự Mamba/MLP giữa phiên.

### P3 — Đối chứng + phân tích
- [ ] MLP 561-64-6 (ReLU), cùng protocol, export C, **verify riêng trên PC trước khi đo trên bo** — cùng split/seed với Mamba retrain (gate #1) và verify bằng **cùng runner host** (một nguồn tham chiếu duy nhất).
- [ ] Bootstrap CI 95% theo cụm người, 2.000 lần, seed cố định; chênh lệch macro-F1 theo điểm phần trăm; chênh lệch năng lượng theo mJ/lượt.
- [ ] Hoàn tất `predictions.csv`, `measurements.csv`, `model_manifest.json`; dựng hình: confusion matrix, sai số logits, phân bố độ trễ, dòng theo thời gian, trade-off macro-F1–năng lượng.

### P4 — Viết + bàn giao
- [ ] Thuyết minh 5 chương theo mục 13.2; phân biệt rõ kết quả đạt được / giới hạn / giả thuyết giải thích.
- [ ] README: một chuỗi lệnh tái tạo được toàn bộ bảng + hình từ dữ liệu bàn giao.
- [ ] Gom đủ 10 mục Phụ lục A.1; kiểm tra toàn vẹn (sample_id duy nhất, số dòng dự đoán khớp số mẫu gửi, đơn vị đo thống nhất).

---

## 4. Gate tiến độ — xử lý sớm, không để trôi

| Gate | Vì sao gấp | Trạng thái |
|---|---|---|
| Mua **Portenta H7 (ABX00042)** + cáp USB-C truyền dữ liệu | Lead time; không có bo = không nghiệm thu. ESP32 chỉ là proxy, đề cương ghi rõ **không thay thế**. | ❌ chưa có |
| Chốt **trọng số công khai vs huấn luyện lại** | Chặn MT5 + mọi số liệu so sánh. | ❌ chưa chốt (xem mục 2) |
| **PPK2 / bộ đo năng lượng** | Mắt xích dài nhất: mượn phòng lab / mua / dựng mạch INA226. | ❌ chưa có |
| **Git commit** | Sản phẩm bàn giao yêu cầu commit + checksum; hiện bằng 0. | 🟡 đã có: chuỗi commit 18/10 (baseline → vendor sửa → vendor `mamba.c` + kiểm UCI), tag `baseline-upstream-44d51fc`, nhánh `dev`, checksum trọng số + 2 vendor + 2 upstream trong `source_manifest.json`; còn: checksum checkpoint retrain |

---

## 5. Hướng phát triển vượt mức (chỉ sau khi xong MT1–MT5 — mục 2.4 đề cương)

Xếp theo giá trị/độ rủi ro. Dùng làm phần "hướng phát triển" của Chương 5, hoặc điểm cộng nếu còn thời gian:

1. **Suy luận streaming mang trạng thái SSM qua cửa sổ** — đúng điểm mạnh kiến trúc Mamba (trạng thái O(1) giữa các bước); hiện tại reset trạng thái mỗi mẫu nên lợi thế đó bị vứt bỏ. Thí nghiệm thú vị nhất về mặt học thuật, và là chỗ duy nhất Mamba có cơ sở vượt MLP.
2. **Lượng tử hóa INT8** — công sức lớn nhất: toàn bộ toán tử C đang FP32, phải làm số học fixed-point cho vòng lặp SSM. Rủi ro cao, novelty cao.
3. **IMU thật (6 trục)** — đóng gap lớn nhất của cấu hình kế thừa: đầu vào là 561 đặc trưng đã xử lý trước, trục "10 bước thời gian" chỉ là cách reshape (mục 4.2). Cần pipeline đặc trưng mới + đồng bộ thu thập.
4. **So sánh chạy trên lõi M4 vs M7** — rẻ nhất, dùng chính phần cứng có sẵn, giàu dữ liệu cho phần năng lượng.
5. **Đo năng lượng theo chu kỳ nhiệm vụ** (sleep giữa các lần suy luận) — mở rộng tự nhiên của P2, phù hợp kịch bản thiết bị đeo.

Nguyên tắc giữ nguyên (mục 12.3): nghiệm thu theo **quy trình + độ đúng + chất lượng bằng chứng**, không áp đặt ngưỡng độ chính xác hay mức giảm năng lượng. Kết quả Mamba không vượt MLP vẫn có giá trị nếu so sánh được tổ chức đúng.

---

## 6. Nhật ký quyết định

| Ngày | Quyết định | Lý do | Người xác nhận |
|---|---|---|---|
| 18/10/2026 | Tạo file này; phát hiện train.py gốc dùng random_split → đề xuất retrain Mamba theo Bảng 2 | Đảm bảo công bằng MT5 | |
| 18/10/2026 | Vendor wrapper mô hình: `MambaLite-Micro/examples/mambahar-arduino-6/include/mambahar.c` → **`firmware/common/mambahar.c`**. ESP32-S3 include bản vendor (`#include "../../common/mambahar.c"` thay cho `"mambahar.c"`). Weights + `sample_input.h` vẫn tham chiếu tại chỗ upstream. | Đề cương 6.3 yêu cầu giữ một bản nguồn gốc không sửa + nhánh phát triển. Kế hoạch trước đó ghi "sửa mambahar.c" mâu thuẫn với "upstream không sửa". | |
| 18/10/2026 | **Dựng runner host PC** (`firmware/host/`) — cùng chuỗi nguồn C của firmware, chạy bằng gcc trong WSL, chế độ batch + 6 logits. Phát hiện **rò rỉ 8.128 B/lượt** (ASan/LSan `8128 byte(s) leaked in 6 allocation(s)`; RSS +8,4 MB/1000 lượt, +32,5 MB/4000 lượt). | Bằng chứng leak **trước** khi sửa đã commit riêng: `a72d025` (log `baseline_leak_1000runs.txt`, `baseline_leak_4000runs.txt`). | |
| 18/10/2026 | **Sửa bản vendor `mambahar.c`**: free toàn bộ cấp phát (3 tensor + 2 matrix + model), kiểm tra NULL mọi cấp phát, kiểm tra `Mamba_Forward != Mamba_OK`, trả `-1` khi lỗi (logits = NaN); thêm `mambahar_forward_logits()` lộ 6 logits (MT2). Diff: `firmware/common/mambahar_vs_upstream.diff`. | Yêu cầu ≥1.000 lượt không reset (Bảng 8 #6) không thể đạt nếu giữ leak ~8 KB/lượt (RAM H7 hết sau ~60 lượt). MT2 cần logits. Upstream không sửa. | |
| 18/10/2026 | Không vendor `csrc/mamba.c`: ASan xác nhận đọc quá biên tại `mamba.c:94` (vòng chép `xz`), nhưng **không đổi kết quả** (giá trị đọc thừa không được dùng) và bit-exact đã chứng minh. Ghi vào tồn đọng. | Sửa cần vendor thêm file lõi — chốt sau khi có số đo trên bo hoặc khi bắt buộc. | |
| 18/10/2026 | **Đảo quyết định trên — vendor `csrc/mamba.c`**: copy → `firmware/common/mamba.c`, sửa 1 dòng `di < d` (hết đọc quá biên). Nghiệm thu: `cmp` **bit-exact** 201 mẫu (`fixed_logits.csv` ≡ `v2_batch201_logits.csv`) **và** 2.947 mẫu UCI (`uci_test_logits_pre_mamba.csv` ≡ `uci_test_logits_post_mamba.csv`); ASan/LSan sạch hẳn. Diff: `firmware/common/mamba_vs_upstream.diff`. | UB thật (ASan xác nhận); sửa 1 dòng; hàng `xz` ≥ `d_model` không bao giờ được dùng → không thể đổi kết quả, kiểm chứng bằng bit-exact. | |
| 18/10/2026 | Chạy **toàn bộ 2.947 mẫu test UCI HAR** trên runner host với trọng số công khai: acc **0,9267**, macro-F1 **0,9265**, **0 mẫu NaN**; F1/lớp 0,879–0,978. Nhãn `y_test.txt` (1..6) phải trừ 1 khi chấm (khớp `train.py` dòng 39). Công cụ: `firmware/host/uci_har.py` (to-f32 / score). | Kiểm tra sớm chất lượng mô hình; xác nhận NaN của mẫu demo là do **sai thang đầu vào**, dữ liệu chuẩn hóa không NaN. | |
| 18/10/2026 | **Thay đổi #3 của bản vendor `mambahar.c`**: kiểm `isfinite` cả 6 logits → trả **`-2`** ("đầu ra không hợp lệ") + logits = NaN; `mambahar_forward` cũng trả -2. Host + firmware ESP32 in rõ dòng `Output: INVALID`. | `val > max_val` với NaN luôn sai → mọi mẫu hỏng trước đây **âm thầm thành lớp 0 (WALKING)** và làm đẹp số liệu; Bảng 8 #6 yêu cầu theo dõi NaN. | |
| 18/10/2026 | **Đính chính lỗi cấu hình**: `-I../../common` trong `platformio.ini` Portenta trỏ `D:\DoanNhomQuy\common` (**không tồn tại**) → 3 lần build trước đó PlatformIO lặng lẽ bỏ qua cờ và biên dịch bản **upstream**, không phải bản vendor. Phát hiện vì flash size không đổi qua 3 phiên bản code; xác nhận bằng `compile_commands.json` + probe `-H`. Sửa thành `-I../common`, include đã trỏ đúng `firmware/common/{mamba,mambahar}.c`; flash 307.096 → **307.368 B**. Kèm sửa lỗi C++: `goto` vượt khởi tạo `int max_idx` (khai báo lên đầu hàm). | Các số build cũ (307.096 B "y hệt") **không chứng minh bản vendor**; đã thay bằng build log mới. Bài học: flash size không đổi = dấu hiệu nghi vấn, phải soi đường include. | |
| 18/10/2026 | **Chốt dung sai MT3 (trước khi so số thật)** — hai tầng: A) C-PC ↔ PyTorch max\|Δlogit\| ≤ 1e-3, MAE ≤ 1e-4; B) MCU ↔ C-PC max ≤ 1e-4, MAE ≤ 1e-5 (cùng mã nguồn, chỉ khác libm/compiler). Nhãn khớp 100% **trừ** mẫu có biên top-2 < ngưỡng tầng → liệt kê riêng ("hồ sơ mẫu khác biệt", tiêu chí #3). Vượt ngưỡng ngay lần đầu → nghi **ánh xạ trọng số** trước khi nghi code C. | Dung sai gộp một tầng không phân biệt được lỗi mô hình vs lỗi nền tảng; mẫu biên hẹp không nên bị tính là sai. Chi tiết + layout nạp ngược: mục 2. | |
| 18/10/2026 | **92,67% chỉ là điểm tham chiếu cho MT1/MT3** (trọng số công khai) — **không** đưa vào bảng so sánh Mamba↔MLP; mọi so sánh chất lượng dùng checkpoint retrain gate #1 cùng split/seed. | Checkpoint công khai được chọn bằng accuracy val chia ngẫu nhiên → không công bằng với MLP (giữ kỷ luật gate #1). | |
| 18/10/2026 | Tạo tag `baseline-upstream-44d51fc` tại `a72d025` (trước mọi thay đổi bản vendor) + nhánh `dev` tại `c081e3e`; từ đây phát triển trên `dev`, `master` giữ làm mốc tổng hợp. Bản gốc chưa sửa đầy đủ = clone `MambaLite-Micro/` @ `44d51fce` (nguồn ngoài, ghi trong `source_manifest.json`); tại commit được tag, `firmware/common/mambahar.c` vẫn là bản 1:1 chưa commit (sha `84AC465D…`). | Đề cương 6.3 yêu cầu giữ bản gốc chưa sửa + một nhánh phát triển. | |
| 18/10/2026 | **A/B compiler C vs C++** (firmware Portenta biên dịch mô hình bằng C++ qua `main.cpp`): build host `g++ -x c++` ≡ `gcc` **bit-exact trên 2.947 mẫu** (`firmware/host/logs/cpp_vs_c_cmp_20261018.txt`); xác nhận `mambahar_forward()` gọi đúng `mambahar_forward_logits(input, NULL)` — cùng một thân hàm. | Loại trừ nguồn lệch ngôn ngữ/compiler của tầng B (còn lại: target ARM Cortex-M7 + newlib/FPU — chỉ chốt được khi có bo). | |
| 18/10/2026 | **A/B upstream 1:1 vs bản dev** (cùng runner host, chỉ khác 2 file mô hình; `-DUPSTREAM_ONLY` vì upstream không lộ logits): pred **bit-exact trên 2.947 mẫu thật** (`firmware/host/logs/upstream_vs_final_cmp_20261018.txt`). Chốt câu đúng phạm vi: chỉ khẳng định bit-exact cho **đầu ra hữu hạn**; lô 201 mẫu chỉ là bằng chứng phụ. | Tuyên bố "sửa 2 lỗi… bit-exact trên 2.947 mẫu" cũ quá rộng so với bằng chứng. | |
| 18/10/2026 | **ASan/LSan mở rộng độ phủ**: 1 mẫu (2 chế độ) + **1.000 lượt liên tiếp** + **batch 2.947 mẫu UCI hữu hạn** — không còn report nào (`firmware/host/logs/asan_extended_20261018.txt`); build ASan (-O1) cũng bit-exact với bằng chứng (-O2). RSS tăng trong ASan là artifact allocator (quarantine/redzone), không phải rò rỉ. | Một lượt 1 mẫu chưa đủ để nói "sạch hoàn toàn". | |
| 18/10/2026 | **Đổi tên phụ lục** `docs/NGHIEM_THU_SO_HOC_HOST_20261020.md` → `docs/KIEM_CHUNG_SO_HOC_PC_20261020.md` (tránh chữ "nghiệm thu" mâu thuẫn mục 0/Bảng 8: bằng chứng PC không phải nghiệm thu). `YEU_CAU_DE_CUONG.md` bỏ phần "Phân tích khoảng cách" (trùng lặp, lệch số build cũ) — chỉ còn tóm tắt đề cương + câu hỏi GVHD; trạng thái duy nhất ở file này. `datn_docx.txt` (toàn văn đề cương 504 dòng) đặt tại gốc repo để trích dẫn kiểm được. | Một nguồn sự thật cho trạng thái; tránh hiểu sai. | |
| 18/10/2026 | `uci_har.py score` in thêm **confusion matrix + tên lớp**; sửa chú thích sai "sklearn LabelEncoder" → đúng: `train.py` trừ 1 ở dòng 37/39 (không dùng LabelEncoder). `source_manifest.json` thêm sha256 **2 file upstream 1:1** (`BA59A6AF…` mamba.c, `84AC465D…` mambahar.c). | Tiêu chí 4 (tái lập) + hết chỗ ghi "thiếu checksum" sai thực tế. | |
| 20/10/2026 | **Lần đầu nạp + chạy trên phần cứng thật**: ESP32-S3-WROOM-1 N16R8, cổng USB-UART CH343 (COM11). Flash `firmware.bin` "Hash of data verified" + bắt log 35 s. Kết quả: `Prediction: -2` / `Output: INVALID (non-finite logits)` (đúng dự kiến với mẫu demo sai thang), **124,27 ms/lượt @160 MHz**, heap 373.756 → 373.540 B (Δ216 B), min free heap 330.284 B. Bằng chứng: `firmware/mambahar-esp32s3/logs/upload_20261020_114637.txt` + `esp32s3_har_20261020_114637.txt`. | Xác nhận chuỗi build→flash→log chạy được trước khi bo Portenta về; **ESP32 là proxy giao thức, không thay nghiệm thu H7** (gate mua bo vẫn ❌). | |
| 20/10/2026 | Sửa `firmware/mambahar-esp32s3/scripts/flash_and_log.ps1` (lỗi chỉ lộ khi chạy thật): (1) khởi tạo `SerialPort` theo từng thuộc tính — PS 5.1 méo enum trong `New-Object -ArgumentList`; DTR/RTS = false để không kéo chân reset sau khi esptool hard-reset; (2) tạm hạ `$ErrorActionPreference` quanh `pio` — warning gcc đi ra **stderr** làm script dừng sai, nguồn sự thật là `$LASTEXITCODE`; (3) tee log upload → `logs/upload_<ts>.txt`. Gặp **1 lần xtensa-gcc segfault nội bộ** khi build lại toàn bộ (build trước bị dừng giữa chừng) — build lại sạch, 0 warning trong log 20/10. | "Hash verified" là bằng chứng nạp; không lưu log upload = mất bằng chứng. ICE là lỗi toolchain tạm thời, không phải code nhóm. | |
| 20/10/2026 | **Mẫu UCI thật trên bo ESP32-S3**: bỏ `sample_input.h` (demo 4.000 float sai thang) → `src/uci_sample.h` = đúng 570 float mẫu 0 của `firmware/host/logs/uci_test.f32`; in 6 logits qua `mambahar_forward_logits`. Kết quả: pred **4** khớp host; **max\|Δlogit\| 1,35e-6, MAE 5,0e-7** (ngưỡng tầng B 1e-4/1e-5; số in 6 chữ số nên có cả sai số làm tròn khi in); 123,37 ms/lượt @160 MHz; heap 387.468 → 387.252 B, min ever 343.996 B; flash 362.080 B, RAM tĩnh 15.412 B (giảm ~13,5 KB do bỏ mảng 4.000 float). Bằng chứng: `logs/esp32s3_har_20261020_120946.txt`, `logs/upload_20261020_120946.txt`. | Có lớp thật + logits trên MCU thật = mảnh bằng chứng **tầng B sớm**; vẫn là proxy ESP32, số chính thức phải chạy lại trên Portenta H7. | |
| 20/10/2026 | xtensa-gcc **ICE segfault lặp lại** ở `esp_lcd_panel_rgb.c` (RTL pass `ira`) khi rebuild một phần; `pio run -j 1` → SUCCESS. | Lỗi toolchain tạm thời (không phải code nhóm); ghi để lần sau gặp thì giảm song song, không đoán mò. | |
| 20/10/2026 | **Sửa bài 1.000 lượt theo phản biện**: (1) vòng lặp **im lặng** — bỏ in từng lượt, `vTaskDelay(1)` ngoài cửa sổ đo → hết **24 trigger task watchdog IDLE0** và hết ngoại lệ 161–171 ms (trước: avg 124,171 ms bị kéo, p95 123,211); (2) thay 20 mẫu liên tiếp (cùng lớp 4) bằng **20 mẫu trải đủ 6 lớp** — chỉ số 79,80,81,128,133,134,109,110,111,31,33,34,0,1,2,55,56,57,112,35; (3) nhúng logits/nhãn host → bo tự tính tier-B trên **6.000 so sánh**: max\|Δ\| **7,629e-6**, MAE **9,157e-7**, lệch nhãn **0/1000**; thời gian p50 **123,201 ms**, max 123,460 ms; heap cuối 385.540 B, min ever 342.284 B; flash 406.024 B, RAM tĩnh 17.124 B. Bằng chứng: `logs/esp32s3_har_20261020_125259.txt`, `upload_..._125259.txt`, `build_..._130420.txt`. | Phản biện chỉ ra log cũ có 24 WDT, avg nhiễu do in log trong vùng đo, logits chỉ in ở `r%100` (luôn mẫu 0) và mảng 20 mẫu thực chất cùng lớp. Nhãn phạm vi: **bring-up ESP32 (proxy)** — không dùng làm bằng chứng tiêu chí 6 (cần Portenta H7); không ngoại suy 123 ms sang H7. | |

### Diff của bản vendor so với upstream

- Upstream: `MambaLite-Micro/examples/mambahar-arduino-6/include/mambahar.c`
- Upstream commit: `44d51fce0f17ddadb6111c5e5554d1f7f6c67aff` (MIT)
- Diff đầy đủ (unified, chuẩn hóa CRLF): **`firmware/common/mambahar_vs_upstream.diff`**
- sha256 bản vendor: ban đầu `84AC465D…` (= upstream, copy 1:1); sau thay đổi 18/10/2026: `8FC09A4A932552046F4F31E271022704382C36E631CFDA59EE328C2AFB594A20`; sau thay đổi #3 (`isfinite`): `C4E20633ECEFFAF8839611A81C63BF33706903CA09987091D900F0859D4EE19D`

**18/10/2026 — ba nhóm thay đổi: (1) hết rò rỉ bộ nhớ + phòng lỗi cấp phát, (2) lộ 6 logits (MT2), (3) báo đầu ra không hợp lệ khi logits không hữu hạn.**

| Thay đổi | Chi tiết | Vì sao |
|---|---|---|
| `mambahar_forward_logits(input, logits)` | Bản mở rộng của `mambahar_forward`; điền 6 logits trước softmax; `mambahar_forward` giữ nguyên chữ ký (gọi wrapper, `logits = NULL`). Vòng tính toán giữ nguyên từng dòng so với upstream. | MT2 yêu cầu xuất 6 logits |
| Trả `-1` khi thất bại; logits = NaN | Mọi `tensor_zeros`/`matrix_zeros`/`Mamba_Init` được kiểm NULL; `Mamba_Forward` được kiểm `!= Mamba_OK`. Trước đây: cấp phát lỗi → gọi vào NULL. | Chống undefined behavior khi hết RAM |
| Kiểm `isfinite` 6 logits → trả `-2` | Logits có NaN/inf → `pred = -2` ("đầu ra không hợp lệ"), logits điền NaN; áp dụng cho cả `mambahar_forward`. `int max_idx` khai báo đầu hàm (C++ không cho `goto` vượt qua khởi tạo). | `val > max_val` với NaN luôn sai → mẫu hỏng trước đây thành lớp 0 (WALKING) âm thầm; Bảng 8 #6 yêu cầu theo dõi NaN |
| `cleanup:` free toàn bộ | `matrix_free(y, pooled)`; `tensor_free(output_T, output, mamba_input)`; `free(model)` | LSan: 8.128 B/lượt × ~60 lượt = chết RAM H7 (511 KB) |
| `#include <stdlib.h>` | csrc không kéo stdlib vào | dùng `free()` tường minh, hết implicit declaration |

Nghiệm thu (bằng chứng trong `firmware/host/logs/`):

| Kiểm tra | Trước sửa | Sau sửa |
|---|---|---|
| RSS 1000 lượt | +8.416 KB (tuyến tính 8,4 KB/lượt) | **+496 KB** |
| RSS 4000 lượt | +32.460 KB | **+500 KB** (tăng 4 KB so với 1000 lượt) |
| LSan | `8128 byte(s) leaked in 6 allocation(s)` (`asan_prefix.txt`) | không còn report (`asan_fixed.txt`) |
| Bit-exact logits (201 mẫu — *lô phụ: 1 mẫu demo NaN + 200 mẫu ngẫu nhiên*) | `baseline_logits.csv` | `fixed_logits.csv` — **`cmp` khớp từng byte**; phạm vi chặt dùng cặp 2.947 mẫu thật (2 dòng dưới) |
| `isfinite` (thay đổi #3) — mẫu demo | `Prediction: 0` (argmax trên NaN) | `Prediction: -2` + dòng `Output: INVALID (non-finite logits)` |
| Test 2.947 mẫu (trọng số công khai) | — | acc **0,9267** / macro-F1 **0,9265**, 0 NaN, 0 invalid (`uci_test_logits_final.csv`) |
| Bit-exact sau thay đổi #3 (201 mẫu) | `v2_batch201_logits.csv` | `v3_batch201_logits.csv` — khác 1 dòng (mẫu 0): cột `pred` (0 → −2) **và cả 6 cột logit** (`-nan` → `nan`); kích thước 15.052 → 15.047 B (khớp −6 ký tự logit +1 ký tự pred); 2.947 mẫu test: pre/post/final giữ nguyên bit-exact từng byte |

Rebuild 2 target với bản vendor (18/10, sau khi sửa lỗi `-I` + lỗi C++ — xem nhật ký): Portenta H7 `SUCCESS` **Flash 307.368 B (+272 B so với bản upstream)** / **RAM tĩnh 77.256 B (.data+.bss — heap đỉnh/stack đo riêng ở P2)**; ESP32-S3 `SUCCESS` **Flash 375.332 B (+160 B)** / RAM tĩnh 29.124 B. *(Ba lần build trước đó ghi "flash 307.096 B y hệt" thực chất biên dịch bản upstream do lỗi đường `-I` — số đó không còn giá trị minh chứng.)*

### Diff của bản vendor `mamba.c` so với upstream

- Upstream: `MambaLite-Micro/csrc/mamba.c` (commit `44d51fc`, MIT)
- Bản vendor: `firmware/common/mamba.c` — sha256 `A4A2AEBB3D77CC5E5D8E8457CBFB8ABB6F80E0F5AE54A38B5D31DE41554FB5E3`
- Diff đầy đủ: **`firmware/common/mamba_vs_upstream.diff`** (1 dòng chức năng + chú thích đầu file)

**18/10/2026 — sửa đọc quá biên (tồn đọng #1):** vòng chép `xz` chạy `di < self->d_inner` trong khi `hidden_states` chỉ có `d_model` chiều → ASan heap-buffer-overflow (đọc 4 B) tại dòng upstream 94. Đổi thành `di < d`. Các hàng `xz` từ `d_model` trở lên **không bao giờ được đọc** về sau → kết quả không đổi.

| Kiểm tra | Kết quả |
|---|---|
| Bit-exact 201 mẫu | `fixed_logits.csv` ≡ `v2_batch201_logits.csv` (`cmp`) |
| Bit-exact 2.947 mẫu UCI | `uci_test_logits_pre_mamba.csv` ≡ `uci_test_logits_post_mamba.csv` (`cmp`) |
| ASan/LSan | sạch hẳn, không còn finding (`asan_vendored.txt`; trước sửa: heap-buffer-overflow `mamba.c:94`) |
| Build | Portenta + ESP32-S3 `SUCCESS` (số ở trên) |

#### Tồn đọng đã biết

1. ✅ **Đã xử lý 18/10/2026**: `csrc/mamba.c:94` đọc quá biên — vendor `mamba.c`, sửa 1 dòng (xem mục trên); bit-exact + ASan sạch.
2. `softplus()` trong `mamba.c` không có nhánh chống tràn (bản guard đã bị comment trong upstream). **Cập nhật 18/10**: 2.947 mẫu test chuẩn hóa cho **0 NaN** → tràn chỉ xảy ra với đầu vào sai thang (mẫu demo). Giữ nguyên (gần PyTorch hơn nếu thêm guard, nhưng chưa cần); theo dõi qua kiểm `isfinite` (mã `-2`).
3. Mẫu demo `sample_input.h` (thang thô ~ -39) cho **logits NaN** — **đã rõ nguyên nhân 18/10**: đầu vào sai thang/khác tiền xử lý, dữ liệu UCI chuẩn hóa không NaN; wrapper giờ báo `-2` thay vì âm thầm trả lớp 0. Còn nợ: đối chiếu PyTorch khi khóa checkpoint (P0).
4. `Mamba_Init()` không tự kiểm `malloc` nội bộ (chỉ kiểm được sau khi trả về) — hết RAM sâu vẫn crash bất định; chấp nhận trong phạm vi hiện tại.

Quy tắc: từ đây **chỉ sửa bản vendor**. Mỗi lần sửa, thêm một mục con bên dưới ghi: ngày, mục tiêu (MT…), và diff unified so với upstream. Không bao giờ sửa `MambaLite-Micro/**`.

---

*Tài liệu tham chiếu: `De_cuong_chi_tiet_DATN_Mamba_HAR_STM32H7.docx` (Bảng 2, Bảng 8, mục 4.4, 6.3, 9.3, 13.2, Phụ lục A), `source_manifest.json`, `Yêu Cầu`, `firmware/mambahar-esp32s3/README.md`.*

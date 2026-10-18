# HƯỚNG PHÁT TRIỂN — ĐATN Mamba HAR trên STM32H7

File điều hướng công việc của nhóm. Nguồn: đối chiếu **Đề cương chi tiết** (Bảng 8 — tiêu chí nghiệm thu; Phụ lục A — hồ sơ bàn giao) với trạng thái repo ngày **18/10/2026**.

Cách dùng: tick ✅ vào ô *Trạng thái* khi có minh chứng thật. Mọi thay đổi phạm vi/cấu hình ghi vào **mục 6 — Nhật ký quyết định**, không sửa âm thầm.

---

## 1. Đích "đủ để ra trường"

Đủ = thỏa **9 tiêu chí Bảng 8** + có đủ **hồ sơ tối thiểu Phụ lục A.1**. Không phát minh thêm phạm vi.

| # | Tiêu chí (Bảng 8) | Trạng thái 18/10 | Minh chứng cần |
|---|---|---|---|
| 1 | Nguồn và khả năng tái lập: commit, license, checksum trọng số, môi trường, hướng dẫn build | ❌ git **chưa có commit nào**; còn lại đã có (`source_manifest.json`) | lịch sử commit + `environment/` |
| 2 | Hoạt động trên phần cứng: Portenta H7 thật, nhiều mẫu, xuất logits/nhãn/lỗi | ❌ mới có bản 1 mẫu trên ESP32-S3 (proxy) | firmware H7 + log nhận gói |
| 3 | Tương đương số học: bảng sai số, tỷ lệ khớp, hồ sơ mẫu khác biệt, dung sai chốt trước | ❌ | `predictions.csv` + bảng sai số |
| 4 | Chất lượng phân loại: accuracy, macro-F1, F1/lớp, confusion matrix trên test + nêu trạng thái checkpoint | ❌ | bảng chỉ số + hình |
| 5 | Đối chứng MLP chạy cùng bo, kiểm chứng riêng | ❌ | firmware MLP + bảng so sánh |
| 6 | Độ ổn định: ≥1.000 lượt không reset ngoài dự kiến, theo dõi bộ nhớ/lỗi đầu vào/NaN | 🟡 host PC: 1000/4000 lượt RSS phẳng sau sửa leak; chờ bo thật | nhật ký stability test trên H7 |
| 7 | Năng lượng: dữ liệu nguồn thô, GPIO, sơ đồ cấp nguồn, điều kiện đo, mJ/lượt | ❌ | `raw_measurements/` + `hardware_manifest.md` |
| 8 | Tài nguyên và thống kê: Flash, RAM theo phương pháp, phân bố thời gian, biến thiên giữa phiên | 🟡 có build log ESP32 (proxy, không thay thế H7) | map file + linker script H7 |
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

---

## 3. Lộ trình P0 → P4 (mỗi bước ra một minh chứng)

### P0 — Tuần này, không cần bo
- [ ] **Commit toàn bộ repo**; `.gitignore` cho `.pio/`; tách nhánh `dev` (đề cương 6.3 bắt buộc giữ bản gốc chưa sửa + nhánh phát triển). *(18/10: đã có commit `a72d025` — baseline host + log leak trước sửa; phần còn lại chưa commit.)*
- [ ] Tải UCI HAR; sinh `split_manifest.csv` (sample_id, subject_id, nhãn, tập) bằng GroupShuffleSplit seed 42; kiểm tra danh sách người không giao nhau giữa các tập.
- [x] **Vendor wrapper mô hình**: copy `mambahar.c` → `firmware/common/mambahar.c` (1:1, sha256 `84AC465D…`), trỏ ESP32-S3 sang bản vendor; upstream giữ nguyên. *(18/10/2026)*
- [x] **Dựng bản C tham chiếu trên PC**: `MambaLite-Micro/csrc/*.c` + **`firmware/common/mambahar.c`** (dùng chung bản vendor với firmware để MT3 so đúng một nguồn), biên dịch native (gcc), chạy N mẫu, in 6 logits. *(18/10/2026 — `firmware/host/`: `run_host_test.ps1` chạy 1 mẫu/1000/4000 lượt; `--batch` đọc file .f32 → CSV 6 logits; ASan qua `run_asan.sh`. Bằng chứng: `firmware/host/logs/`.)*
- [ ] Đối chiếu logits C-PC ↔ PyTorch (`mamba_ssm` + trọng số công khai) → xác nhận tuyên bố "100% khớp" của paper bằng số liệu của nhóm.
- [ ] Huấn luyện lại Mamba (gate #1) → lưu checkpoint + lịch sử train.

### P1 — Firmware (ESP32 tiếp tục, chuyển H7 khi bo về)
- [x] Sửa **`firmware/common/mambahar.c`** (bản vendor — không sửa upstream): forward trả **cả 6 logits** trước softmax (hiện trả `int` argmax); ghi diff so với upstream vào mục 6. *(18/10/2026 — kèm sửa leak 8.128 B/lượt; đối chiếu bit-exact trước/sau: `firmware/host/logs/baseline_logits.csv` ≡ `fixed_logits.csv`; xem mục 6.)*
- [ ] Giao thức nhận gói PC→MCU: `[sample_id | 570 float | checksum]`; từ chối gói sai độ dài/checksum; quản lý timeout.
- [ ] Bỏ vòng `NVIC_SystemReset` sau 1 mẫu → vòng lặp nhiều mẫu có mã định danh.
- [ ] Thêm GPIO marker bao vùng suy luận; **không in log trong vùng đo**.
- [ ] Chạy thử 1.000 lượt liên tiếp, giám sát reset ngoài dự kiến / đầu ra không hữu hạn / mức dùng bộ nhớ.

### P2 — Đo lường
- [ ] Flash/RAM từ **map file + linker script Portenta H7** (không dùng số ESP32 thay thế); tách tĩnh/heap/stack/working buffer.
- [ ] **Đặt lịch mượn PPK2 ngay** (hoặc chốt phương án INA226 — cần thêm thời gian thiết kế mạch).
- [ ] Bố trí nguồn 1 đường duy nhất, loại USB cấp nguồn song song, kiểm tra cực tính/điện áp/dòng đỉnh.
- [ ] Đo nền + 5 phiên × 6 khối × 10 lượt mỗi cấu hình (mục 9.3); hoán đổi thứ tự Mamba/MLP giữa phiên.

### P3 — Đối chứng + phân tích
- [ ] MLP 561-64-6 (ReLU), cùng protocol, export C, **verify riêng trên PC trước khi đo trên bo**.
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
| **Git commit** | Sản phẩm bàn giao yêu cầu commit + checksum; hiện bằng 0. | 🟡 1 commit baseline (`a72d025`) + commit bản vendor sửa; chưa commit toàn bộ repo |

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
| | | | |

### Diff của bản vendor so với upstream

- Upstream: `MambaLite-Micro/examples/mambahar-arduino-6/include/mambahar.c`
- Upstream commit: `44d51fce0f17ddadb6111c5e5554d1f7f6c67aff` (MIT)
- Diff đầy đủ (unified, chuẩn hóa CRLF): **`firmware/common/mambahar_vs_upstream.diff`**
- sha256 bản vendor: ban đầu `84AC465D…` (= upstream, copy 1:1); sau thay đổi 18/10/2026: `8FC09A4A932552046F4F31E271022704382C36E631CFDA59EE328C2AFB594A20`

**18/10/2026 — hai nhóm thay đổi: (1) hết rò rỉ bộ nhớ + phòng lỗi cấp phát, (2) lộ 6 logits (MT2).**

| Thay đổi | Chi tiết | Vì sao |
|---|---|---|
| `mambahar_forward_logits(input, logits)` | Bản mở rộng của `mambahar_forward`; điền 6 logits trước softmax; `mambahar_forward` giữ nguyên chữ ký (gọi wrapper, `logits = NULL`). Vòng tính toán giữ nguyên từng dòng so với upstream. | MT2 yêu cầu xuất 6 logits |
| Trả `-1` khi thất bại; logits = NaN | Mọi `tensor_zeros`/`matrix_zeros`/`Mamba_Init` được kiểm NULL; `Mamba_Forward` được kiểm `!= Mamba_OK`. Trước đây: cấp phát lỗi → gọi vào NULL. | Chống undefined behavior khi hết RAM |
| `cleanup:` free toàn bộ | `matrix_free(y, pooled)`; `tensor_free(output_T, output, mamba_input)`; `free(model)` | LSan: 8.128 B/lượt × ~60 lượt = chết RAM H7 (511 KB) |
| `#include <stdlib.h>` | csrc không kéo stdlib vào | dùng `free()` tường minh, hết implicit declaration |

Nghiệm thu (bằng chứng trong `firmware/host/logs/`):

| Kiểm tra | Trước sửa | Sau sửa |
|---|---|---|
| RSS 1000 lượt | +8.416 KB (tuyến tính 8,4 KB/lượt) | **+496 KB** |
| RSS 4000 lượt | +32.460 KB | **+500 KB** (tăng 4 KB so với 1000 lượt) |
| LSan | `8128 byte(s) leaked in 6 allocation(s)` (`asan_prefix.txt`) | không còn report (`asan_fixed.txt`) |
| Bit-exact logits (201 mẫu) | `baseline_logits.csv` | `fixed_logits.csv` — **`cmp` khớp từng byte** |

Rebuild 2 target với bản vendor sửa (18/10): Portenta H7 `SUCCESS` Flash 307.096 B / RAM 77.256 B (y hệt trước), ESP32-S3 `SUCCESS` Flash 375.172 B (+252 B do code logits/free) / RAM 29.124 B.

#### Tồn đọng đã biết (chưa sửa — chờ quyết định vendor `csrc/mamba.c`)

1. `csrc/mamba.c:94` **đọc quá biên** tensor (ASan: heap-buffer-overflow, đọc 4 B ngay sau vùng 2.576 B). Vòng chép `xz` chạy tới `d_inner` trong khi chiều đọc chỉ có `d_model`; giá trị đọc thừa **không được dùng** nên kết quả không đổi (bit-exact đã chứng minh). Sửa cần vendor `mamba.c` (diff 1 dòng).
2. `softplus()` trong `mamba.c` không có nhánh chống tràn (bản guard đã bị comment trong upstream) — nghi vấn liên quan finding #3.
3. Mẫu demo `sample_input.h` (thang thô ~ -39) cho **logits NaN** trên cả đường host; 200 mẫu N(0,1) còn lại hữu hạn → nghi đầu vào chưa chuẩn hóa/khác tiền xử lý. Cần đối chiếu PyTorch khi khóa checkpoint (P0). Trước đây log "Prediction: 0" của mẫu này thực chất là argmax trên NaN — không phải dự đoán thật.
4. `Mamba_Init()` không tự kiểm `malloc` nội bộ (chỉ kiểm được sau khi trả về) — hết RAM sâu vẫn crash bất định; chấp nhận trong phạm vi hiện tại.

Quy tắc: từ đây **chỉ sửa bản vendor**. Mỗi lần sửa, thêm một mục con bên dưới ghi: ngày, mục tiêu (MT…), và diff unified so với upstream. Không bao giờ sửa `MambaLite-Micro/**`.

---

*Tài liệu tham chiếu: `De_cuong_chi_tiet_DATN_Mamba_HAR_STM32H7.docx` (Bảng 2, Bảng 8, mục 4.4, 6.3, 9.3, 13.2, Phụ lục A), `source_manifest.json`, `Yêu Cầu`, `firmware/mambahar-esp32s3/README.md`.*

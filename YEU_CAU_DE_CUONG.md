# TỔNG HỢP YÊU CẦU ĐỀ CƯƠNG CHI TIẾT — DATN Mamba HAR trên STM32H7

> **Nguồn:** `De_cuong_chi_tiet_DATN_Mamba_HAR_STM32H7.docx` → bản trích `datn_docx.txt` (504 dòng).
> **Cách đọc:** 4 agent đọc song song 4 dải (§1–§5, §6–§8, §9–§12, §13–Phụ lục B) + đọc lại toàn văn. Số dòng trong ngoặc = dòng của bản trích.
> **Ngày tổng hợp:** 18/10/2026. GVHD: TS. Nguyễn Thanh Bình.

---

## 0. Khung bắt buộc — đọc trước mọi thứ

- Tên đề tài (dòng 56): *"Triển khai mô hình Mamba nhận dạng hoạt động người trên STM32H7 và đánh giá năng lượng tiêu thụ."*
- 3 trục bắt buộc (dòng 58): **suy luận trên vi điều khiển + kiểm chứng tính tương đương số học + đo năng lượng trên phần cứng**. "Không dừng ở việc biên dịch mô hình" (61).
- Sản phẩm (58): hệ thống thử nghiệm "nhận dữ liệu đặc trưng, thực hiện phân loại và xuất kết quả phục vụ đánh giá định lượng".
- Sản phẩm phân loại đúng 1 mẫu "chưa đủ để xác lập khả năng hoạt động của hệ thống" (61).
- Năng lượng đo trong cửa sổ suy luận **không được** trình bày như năng lượng toàn thiết bị đeo (62).
- Đề cương **không giả định Mamba thắng MLP** (65): *"không đặt giả định Mamba phải vượt trội so với mô hình đối chứng, cũng không xem kiến trúc và mã nguồn kế thừa là đóng góp mới của sinh viên."*
- Mục tiêu tổng quát (68): *"Xây dựng hệ thống thử nghiệm nhận dạng sáu hoạt động người trên STM32H7 bằng mô hình Mamba kế thừa; kiểm chứng tính đúng của bản nhúng và đánh giá mối quan hệ giữa chất lượng phân loại, tài nguyên tính toán và năng lượng tiêu thụ."*
- Ba đóng góp kỹ thuật (64): *"hoàn thiện chương trình thử nghiệm nhiều mẫu trên STM32H7; xây dựng quy trình đối chiếu kết quả và quản lý tài nguyên; tổ chức phép đo năng lượng có đồng bộ với hoạt động suy luận."* MLP nhỏ dùng làm đối chứng *"nhằm xác định chi phí triển khai của cấu hình Mamba trong cùng điều kiện"* (64).

## 1. Mục tiêu MT1–MT5 + minh chứng (dòng 70–87)

| Mã | Mục tiêu | Minh chứng |
|---|---|---|
| MT1 | Tái lập mô hình và cấu hình phần cứng tham chiếu. | "Phiên bản nguồn, trọng số, tệp cấu hình và nhật ký biên dịch." |
| MT2 | Phát triển **suy luận nhiều mẫu**, xuất **nhãn và sáu giá trị đầu ra trước softmax**. | "Chương trình máy tính, firmware và dữ liệu dự đoán." |
| MT3 | Kiểm chứng đầu ra giữa bản tham chiếu và vi điều khiển. | "Bảng sai số số học và tỷ lệ khớp nhãn dự đoán." |
| MT4 | Đo độ trễ, Flash, RAM và năng lượng suy luận. | "Dữ liệu đo thô, phạm vi đo và báo cáo thống kê." |
| MT5 | So sánh với một MLP FP32 trong điều kiện được kiểm soát. | "Cùng tập chia, cùng đầu vào thông tin và cùng bo thử nghiệm." |

## 2. Câu hỏi nghiên cứu (dòng 90)

1. Bản C/C++ trên STM32H7 bảo toàn kết quả của bản tham chiếu ở mức nào (cùng dữ liệu, trọng số, kiểu số)?
2. Chi phí suy luận của cấu hình Mamba được triển khai là bao nhiêu?
3. Chênh lệch chất lượng phân loại Mamba vs MLP đi kèm mức thay đổi nào về thời gian, bộ nhớ, năng lượng?

## 3. Phạm vi và giới hạn (dòng 92–93)

- Đối tượng: Mamba FP32, thực thi trên **lõi Cortex-M7**, hệ đo nguồn của **Portenta H7**. Huấn luyện trên PC, suy luận trên MCU.
- **KHÔNG thuộc phạm vi bắt buộc** (93): thu IMU trực tiếp, chẩn đoán sức khỏe, phát hiện té ngã, **triển khai đồng thời trên ESP32**, thiết kế mạch in riêng.
- Tích hợp cảm biến và lượng tử hóa: **chỉ xem xét SAU khi xong MT1–MT5**.
- ⚠️ *"Mọi thay đổi phạm vi phải được thống nhất trước khi thu số liệu chính thức."*

## 4. Kế thừa (Bảng 1, dòng 96–122)

**Cơ sở Mamba (96–98):** `hₜ = Āₜ hₜ₋₁ + B̄ₜ xₜ; yₜ = Cₜ hₜ + D xₜ` (1). Nguyên văn cảnh báo: *"Biểu thức này chỉ mô tả phần không gian trạng thái, không thay thế toàn bộ các phép chiếu, tích chập và cơ chế cổng trong khối Mamba. Lợi ích tính toán của kiến trúc cần được kiểm tra trong cấu hình cụ thể, không suy ra trực tiếp từ kết quả trên mô hình ngôn ngữ lớn."*

**Nguồn chính (100):** MambaLite-Micro của Xu và cộng sự — arXiv:2509.05488v1 (2025), **giấy phép MIT**, trọng số dạng **mảng C**, ví dụ HAR cho môi trường **portenta_h7_m7** [2],[4],[6].

**Bối cảnh mẫu gốc (122):** *"Mẫu chương trình hiện thực hiện suy luận với dữ liệu lưu sẵn rồi khởi động lại bo [7]. Đây là cơ sở để kiểm tra bước đầu, chưa thay thế một chương trình đánh giá liên tục."* Việc kế thừa được công bố trong báo cáo; sửa đổi phải có nhật ký và đối chiếu được với mã gốc.

| Thành phần | Nguồn kế thừa | Việc phải làm |
|---|---|---|
| Mô hình + trọng số | MambaLite-Micro, tệp trọng số HAR [8] | Kiểm tra kích thước, nguồn gốc, tương thích |
| Ví dụ chạy trên bo | `mambahar-arduino-6` [6],[7] | **Chuyển từ MỘT mẫu sang bộ thử NHIỀU mẫu; bổ sung xử lý lỗi** |
| Thực thi toán tử C | Kho mã [4] | Kiểm tra vòng đời bộ nhớ + đối chiếu đầu ra |
| Dữ liệu | UCI HAR [3] | Bảng phân chia theo người + tổ chức đánh giá |
| Đo năng lượng | (tự xây) | Thiết kế đường nguồn, tín hiệu đánh dấu, xử lý số liệu |

Kế thừa phải ghi trong báo cáo; mọi sửa đổi phải có nhật ký, đối chiếu được với mã gốc (122).

## 5. Dữ liệu UCI HAR (dòng 125–134)

- 30 người, 6 hoạt động (đi bộ, lên cầu thang, xuống cầu thang, ngồi, đứng, nằm); 50 Hz; cửa sổ 128 mẫu = 2,56 s, chồng lấn 50%; **561 đặc trưng** + nhãn + mã người.
- Tập train/test gốc chia theo người với tỷ lệ **70% / 30%** [3]; đồ án **giữ nguyên tập kiểm tra gốc**. Số mẫu của từng phần và phân bố nhãn kiểm tra trực tiếp từ tệp dữ liệu, lưu vào bảng thống kê.
- Chuẩn bị đầu vào (128): giữ thứ tự 561 đặc trưng; **padding 9 giá trị 0 cuối vector** → **570 phần tử** → sắp hàng thành **ma trận 10 × 57** [5]. FP32. Kiểm tra: kích thước, giá trị không hữu hạn, nhãn ngoài miền, mã mẫu trùng.
- 10 hàng là cách tổ chức lại đặc trưng, **không phải 10 thời điểm đo**; không diễn giải như học thời gian IMU thô (129).
- Chia validation (131): từ train gốc giữ **~20% số người** làm validation, theo `subject_id`, **seed = 42**, dùng **GroupShuffleSplit** [13]. Danh sách người/mẫu **lưu cố định trước khi chọn cấu hình**. Các tập **không được trùng người**.
- Khi dùng trọng số công khai: **không chuẩn hóa lại** theo quy trình khác nếu chưa xác minh quy trình huấn luyện (132).
- Khi huấn luyện lại: mọi bước ước lượng tiền xử lý chỉ dùng train. **Không dùng test** để chọn hyperparam/epoch/trọng số/dung sai (132).
- Điều kiện dùng trọng số có sẵn (134): trọng số công khai dùng **trước hết để tái lập thực thi**. Muốn so sánh phân loại với MLP → **phải xác minh dữ liệu huấn luyện của trọng số**. Không đủ thông tin → **huấn luyện lại trên tập chia của đồ án**. Chưa huấn luyện lại được → chỉ báo cáo như "khảo sát mô tả có giới hạn về nguồn gốc", không kết luận mô hình nào tổng quát hóa tốt hơn.

## 6. Mô hình (dòng 137–160)

### 6.1. Mamba kế thừa
- Đầu vào **10 × 57**, hidden **64**, **một khối Mamba**, classifier **6 lớp**.
- Tham số: `d_state = 16`, `d_conv = 4`, `expand = 2`, `dt_rank = 4` [7],[8]. **"Trước triển khai, các kích thước được đối chiếu với từng mảng trọng số."** (137)
- Luồng: `10×57 → Linear 57→64 → Mamba → mean-pool → 6 outputs` (138).
- **Batch = 1, FP32**; trọng số cố định khi suy luận; **trạng thái reset theo từng mẫu độc lập** (139).
- Hàm dự đoán trả **cả nhãn và vector 6 đầu ra trước softmax** để kiểm chứng số học (139). *(Quan sát ngoài đề cương, từ mã nguồn [7]: `mambahar.c` hiện chỉ trả argmax → phải sửa để đủ MT2.)*

### 6.2. MLP đối chứng (141–142)
- **561–64–6, ReLU** sau lớp ẩn; nhận đủ 561 đặc trưng (đệm 0 không thêm thông tin); cùng kiểu số, tập chia, điều kiện đo.
- **Xuất sang C/C++ và kiểm chứng riêng** trước khi đo trên cùng bo.
- Khác biệt số tham số/phép toán **phải báo cáo**, không coi là đã cân bằng. Nguyên văn (141–142): *"Đây là thiết kế đối chứng của đồ án, không phải cấu hình được trích từ công trình MambaLite-Micro"*; phép so sánh *"nhằm khảo sát hai phương án triển khai cụ thể, không xác lập ưu thế phổ quát của một họ kiến trúc."*

### 6.3. Huấn luyện khi cần (Bảng 2, dòng 144–160)
| Tham số | Thiết lập |
|---|---|
| Optimizer / loss | Adam / cross-entropy 6 lớp |
| LR / batch | **10⁻³** / **64** (giảm batch khi không đủ bộ nhớ) |
| Epoch / early stop | **100** / dừng sau **10 epoch** không cải thiện **macro-F1 validation** |
| Chọn checkpoint | Macro-F1 validation cao nhất; **cùng quy tắc cho 2 mô hình** |
| Seed | **42** chính; **43, 44** kiểm tra độ nhạy nếu đủ nguồn lực |
| Thiết bị | PC; **"cần kiểm tra phụ thuộc CUDA của mã Mamba"** |

- Thay đổi cấu hình phải **kết thúc trước khi mở tập test** (160). Huấn luyện 1 lần → **không suy diễn độ ổn định giữa các lần khởi tạo**.

## 7. Phần mềm nhúng (dòng 163–184)

### 7.1. Hệ thống 3 khối (163)
PC điều phối (quản lý mã mẫu, gửi dữ liệu, lưu kết quả) — firmware trên Portenta H7 (kiểm tra đầu vào, thực thi, trả kết quả) — bộ đo nguồn độc lập (**ghi dòng đồng bộ với chân GPIO đánh dấu vùng suy luận**).

### 7.2. Sáu mô-đun bắt buộc phải phát triển (Bảng 3, dòng 164–178)
| Mô-đun | Chức năng + yêu cầu đầu ra |
|---|---|
| Quản lý dữ liệu | Đọc đặc trưng, nhãn, `subject_id`; **tạo `split_manifest.csv`**; xác nhận thứ tự đặc trưng |
| Điều phối thử nghiệm | Gửi **mã mẫu + 570 giá trị FP32**; kiểm tra thứ tự phản hồi; **"không dùng nhãn thật trong hàm suy luận"** |
| Giao tiếp nhúng | Kiểm tra độ dài gói, số thứ tự, **checksum**; từ chối gói không hợp lệ; quản lý timeout |
| Thực thi mô hình | Nạp trọng số; quản lý buffer; **xuất 6 logits, nhãn và trạng thái thực thi** |
| Đánh dấu phép đo | **GPIO bao vùng thực thi**; lưu thời điểm đầu/cuối; **"không in log trong vùng đo"** |
| Tổng hợp kết quả | Ghép dự đoán với nhãn trên PC; bảng chỉ số + báo cáo sai lệch |

### 7.3. Bộ nhớ và ổn định (181–182)
- Rà soát **vòng đời mọi vùng nhớ**; vùng tạm giải phóng/tái sử dụng có kiểm soát; model khởi tạo 1 lần khi phù hợp; vùng làm việc **reset trước mỗi lần suy luận**; kiểm tra lỗi cấp phát trước khi dùng con trỏ; **không suy luận tiếp với dữ liệu chưa đầy đủ**.
- Tách 3 tình huống: khởi tạo sau cấp nguồn / suy luận ổn định / kiểm thử lỗi.
- **≥ 1.000 lần suy luận liên tiếp** với đầu vào thay đổi; theo dõi **số reset ngoài dự kiến, đầu ra không hữu hạn, mức dùng bộ nhớ**. Bài test hữu hạn chỉ chứng minh độ ổn định trong điều kiện đã thử (182).

### 7.4. Kiểm soát phiên bản (184)
Lưu: commit kho nguồn, **checksum trọng số**, phiên bản compiler, thư viện, tệp cấu hình phần cứng. **Giữ một bản nguồn gốc KHÔNG sửa + một nhánh phát triển có lịch sử thay đổi.** Rà soát phụ thuộc, cách chia dữ liệu, thiết bị tính toán của chương trình mẫu/mã huấn luyện [5]–[7].

## 8. Phần cứng và môi trường (dòng 187–251)

### 8.1. Bo (187–188)
- **Arduino Portenta H7, mã ABX00042**, STM32H747XI, M7 tối đa 480 MHz, định danh PlatformIO `portenta_h7_m7`.
- **"Đề tài sử dụng một lõi M7 cho suy luận và giữ trạng thái lõi M4 thống nhất giữa các phép đo."**
- Giới hạn ứng dụng: **768 KB Flash, ~511,35 KB RAM** [10]. Báo cáo **căn cứ linker script + map file bản firmware thực tế**; bộ nhớ ngoài hạch toán riêng.

### 8.2. Danh mục phần cứng (Bảng 4, dòng 190–228)
| Hạng mục | SL | Yêu cầu |
|---|---|---|
| **Arduino Portenta H7** | 1 | **BẮT BUỘC; đúng bo tham chiếu, lõi M7** |
| **Cáp USB-C truyền dữ liệu** | 1 | Bắt buộc; **không dùng cáp chỉ sạc** |
| **PPK2 hoặc bộ đo tương đương** | 1 | **Bắt buộc có quyền sử dụng**; có thể dùng chung phòng lab |
| Nguồn DC ổn định | 1 | Phù hợp đường 5 V; đáp ứng dòng đỉnh đã kiểm tra |
| Dây đo, adapter, đầu nối | 1 bộ | **Toàn bộ dòng cấp phải đi qua điểm đo**; không để USB cấp nguồn song song |
| Đồng hồ vạn năng | 1 | Dùng chung; đo điện áp thực tại đầu vào bo + kiểm cực tính |
| PC phát triển | 1 | USB; khuyến nghị RAM 16 GB |
| USB–UART mức logic 3,3 V | 0–1 | Chỉ nếu phương án trao đổi dữ liệu cần; không nối chân cấp nguồn phụ |
| Máy hiện sóng / logic analyzer | Dùng chung | Khuyến nghị (xác nhận GPIO, sụt áp, vùng đo) |
| ST-LINK và đầu nối tương thích | Tùy chọn | Gỡ lỗi mức thấp; không bắt buộc cho nạp DFU |
| IMU sáu trục và mạch ghép nối | Tùy chọn | **Không thuộc cấu hình nghiệm thu bắt buộc** |

- **"Không thay Portenta H7 bằng một bo STM32 bất kỳ mà vẫn xem đó là tái lập nguyên cấu hình."** (228) — đổi nền tảng phải có kế hoạch riêng. Màn hình/camera/Wi-Fi/pin không bắt buộc.

### 8.3. Đo nguồn (230–233)
- PPK2: **100 kS/s**, input số đồng bộ GPIO, cấp nguồn **0,8–5 V / tối đa 1 A** [11]; chỉ dùng khi dòng khởi động và dòng đỉnh nằm trong giới hạn; **"Độ phân giải đo không được đồng nhất với độ chính xác của toàn hệ thống."**
- Bố trí nguồn: **đường duy nhất**, 5 V qua adapter đúng đầu vào Portenta; dòng **đi qua bộ đo trước khi đến bo**; **ngắt pin và nguồn phụ**; **sau khi nạp, loại bỏ đường USB không qua bộ đo**. *"Sơ đồ thực tế phải ghi rõ cả dây nguồn, dây đất và dây GPIO."* (232)
- Trong đo: nạp sẵn đầu vào theo khối TRƯỚC khi kích hoạt vùng đo; **kết quả gửi SAU khi vùng đo kết thúc**; UART phải kiểm mức logic/nối đất chung/không dòng cấp ngược.
- INA226 thay thế khi không có PPK2 [12]: shunt phù hợp, bộ ghi độc lập, thời gian chuyển đổi xác định trước; nếu tốc độ không đủ phân giải từng lượt → chỉ dùng năng lượng trung bình khối đủ dài, **không khẳng định quan sát được dạng dòng từng phép toán**.

### 8.4. Môi trường phần mềm (Bảng 5, dòng 235–251)
PlatformIO/ststm32 (`portenta_h7_m7` + `arduino`) — C/C++ + thư viện toán — Python (dữ liệu, điều phối, chỉ số, biểu đồ) — PyTorch + `mamba_ssm` (huấn luyện/khôi phục, khóa phiên bản sau kiểm thử) — Power Profiler — **Git + tệp khóa môi trường**.
- **"GPU không bắt buộc cho giai đoạn sử dụng trọng số có sẵn và biên dịch firmware. Phương án huấn luyện lại cần xác nhận khả năng truy cập môi trường phù hợp ngay trong hai tuần đầu."** (251) — ⚠️ deadline thực tế: **cuối tuần 2**.

## 9. Kiểm chứng số học và đo hiệu năng (dòng 253–264)

### 9.1. Quy trình (254)
1. Xây **bản C trên máy tính** dùng cùng toán tử + trọng số với firmware (kiểm chứng ảnh hưởng compiler/nền tảng).
2. **Chỉ đối chiếu PyTorch sau khi khôi phục được kiến trúc, checkpoint và quy trình xử lý đầu vào tương ứng.** "Đối chiếu C–MCU không tự chứng minh mã C thực hiện đúng toàn bộ mô hình PyTorch."

### 9.2. Sai số (255–258)
- Mỗi mẫu: lưu **6 logits** của ref và MCU.
- `e_max = max |z_ij(MCU) − z_ij(ref)|` (2)
- `MAE = [1/(6N)] Σ_i Σ_j |z_ij(MCU) − z_ij(ref)|` (3)
- Báo cáo thêm **tỷ lệ nhãn dự đoán trùng** + danh sách ca khác biệt. Hai giá trị đầu ra lớn nhất gần nhau → kiểm tra biên quyết định trước khi kết luận lỗi.
- **"Ngưỡng sai số chấp nhận được xác lập trên tập phát triển và khóa trước khi đánh giá tập kiểm tra."** ⚠️ (cần GVHD xác nhận — dòng 503)

### 9.3. Phân loại (260)
Chỉ số chính **macro-F1**; bổ sung accuracy, F1 từng lớp, confusion matrix [14]. **Nhãn thật chỉ ghép ở bước đánh giá.** Tỷ lệ khớp 2 bản thực thi trình bày riêng, **không dùng thay độ chính xác**.

### 9.4. Đo thời gian/bộ nhớ (262–264)
- Đo riêng **khởi tạo** vs **suy luận ổn định**. Vùng đo = toàn bộ hàm suy luận (từ lúc đầu vào sẵn trong RAM → có logits+nhãn); **không bao truyền dữ liệu hoặc in log**; đường xử lý đầy đủ nếu đo thêm phải đặt tên riêng.
- Ghi: xung lõi thực tế, trạng thái cache, cờ tối ưu, trạng thái ngắt, M4, ngoại vi. Timer đơn điệu/bộ đếm chu kỳ đã kiểm tràn.
- Mỗi kết quả: **trung vị, trung bình, độ lệch chuẩn, phân vị 95**; **"phân vị 95 không được gọi là giới hạn trễ xấu nhất"**.
- Flash từ **báo cáo liên kết**; RAM tách **tĩnh / heap / stack / vùng làm việc**; **"không cộng cơ học các đỉnh khác thời điểm"** để gọi là RAM đỉnh toàn hệ thống; nêu rõ cách lấy mẫu/theo dõi bộ nhớ + mọi vùng SDRAM dùng.

## 10. Đo năng lượng (dòng 267–278)

- Đại lượng: **năng lượng điện toàn bo** trong cửa sổ suy luận; điểm đo **trước đầu vào nguồn bo** (gồm tổn hao cấp nguồn). **"Không gọi đại lượng này là năng lượng riêng của lõi M7 hoặc riêng phép nhân ma trận."**
- `E = ∫_{t0}^{t1} V(t)·I(t) dt` (4); `E ≈ Σ V_k I_k Δt_k; E(mJ) = 1000 × E(J)` (5).
- PPK2 chủ yếu ghi dòng → **điện áp phải đo kiểm tại đầu vào bo**; nếu dùng V cố định thì **báo cáo rõ giả định + mức biến thiên đã kiểm tra**; không coi V đặt trên phần mềm là đo tức thời.
- GPIO: lên mức **ngay trước** suy luận, trả về **sau khi có đầu ra**; ghi số đồng thời với dòng; **kiểm độ lệch timer–GPIO; đo riêng chi phí đánh dấu bằng vùng rỗng**; mọi phép trừ chi phí phải mô tả + **lưu cả giá trị chưa hiệu chỉnh**.
- Trước đo: kiểm cực tính, điện áp, dòng đỉnh, nguồn phụ; **đối chiếu hệ đo bằng tải kiểm tra ổn định + thiết bị tham chiếu phòng lab**, ghi rõ giới hạn phép đối chiếu; kiểm waveform không bão hòa/mất mẫu/cắt cạnh GPIO; **phép đo lỗi kỹ thuật đánh dấu và GIỮ trong nhật ký, không xóa vô cớ**.
- Thiết kế lặp (275–276): **5 phiên × 6 khối × 10 suy luận = 300 lượt/cấu hình**; **+20 lượt warmup** trước mỗi cấu hình; chọn trước **60 mẫu từ tập dev, đủ 6 lớp, cùng danh sách cho 2 mô hình**; **hoán vị thứ tự bằng seed được lưu**; **luân phiên Mamba/MLP** giảm ảnh hưởng thời gian/nhiệt; mã phiên/khối/mẫu/cấu hình phải liên kết được với tệp dòng thô. *"Số lượt này là thiết kế thực nghiệm dự kiến, không phải số liệu đã thu."*
- Nền (278): báo cáo **năng lượng tổng** là kết quả chính; năng lượng tăng thêm `E_tăng thêm = E_tổng − P_nền × T` (nền đo cùng cấu hình) — chỉ là giá trị so với trạng thái nền đã chọn. **"Ước lượng biến thiên giữa các lượt đo không thay thế thông tin sai số điện áp, sai số dòng và sai số đồng bộ của hệ đo."**

## 11. Phân tích số liệu (dòng 281–302)

- **Đơn vị độc lập = NGƯỜI tham gia**, không phải cửa sổ. Báo cáo chỉ số toàn test + phân bố theo người.
- **CI 95% bằng bootstrap theo cụm người**: lấy lại mã người có hoàn lại, **giữ toàn bộ cửa sổ**, tính lại chỉ số; **2.000 lần, seed cố định**.
- So sánh Mamba–MLP: **cùng cụm người trong từng lần bootstrap**, tính trực tiếp **Δ macro-F1**. Ít người test → diễn giải thận trọng; 1 seed → CI **không mô tả** biến thiên khởi tạo/huấn luyện.
- Năng lượng: **phiên và khối là cấu trúc lặp kỹ thuật** — tổng hợp theo khối/phiên, lấy mẫu lại giữ cấu trúc phiên; **"không coi 300 lượt đo là 300 thiết bị độc lập"**; 1 bo → kết luận chỉ áp dụng cho bo + điều kiện đã khảo sát.
- Bảng 6 — 3 phép so sánh có kiểm soát:
  1. **C trên máy tính vs MCU**: cùng đầu vào/trọng số/toán tử/kiểu số → mức tương đương thực thi.
  2. **Mamba vs MLP trên MCU**: cùng tập chia, cùng bo, nguồn và ranh giới đo → đánh đổi phân loại–tài nguyên.
  3. **Mamba trước/sau sửa quản lý bộ nhớ**: cùng model/trọng số/công cụ → ảnh hưởng thay đổi triển khai.
- Trình bày: Δ macro-F1 theo **điểm phần trăm**, Δ năng lượng theo **mJ/lần suy luận**; nêu rõ cấu hình đối chứng + mẫu số; **"không diễn giải thời gian xử lý ngắn hơn như bằng chứng tự động của năng lượng thấp hơn"**.
- Bảng kết quả phải có: số mẫu, số người, số phiên đo, phiên bản firmware. Biểu đồ (chỉ dựng sau khi có dữ liệu): confusion matrix, sai số đầu ra, phân bố độ trễ, dòng theo thời gian, đánh đổi macro-F1–năng lượng. **Không đặt số liệu minh họa vào phần kết quả thực nghiệm.**
- Thảo luận: lớp dễ nhầm, ảnh hưởng biểu diễn đặc trưng, sai khác compiler, giới hạn mô hình kế thừa; nguyên nhân chưa kiểm chứng = **giả thuyết**, không thành kết luận nhân quả.

## 12. Tiến độ 12 tuần (Bảng 7, dòng 307–347)

**Sáu nội dung công việc (305):** (1) khảo sát công trình và xác minh điều kiện tái lập; (2) chuẩn bị dữ liệu và bản tham chiếu; (3) phát triển firmware và kiểm thử ổn định; (4) xây dựng MLP đối chứng và hoàn thiện hồ sơ huấn luyện; (5) thiết lập phép đo và thu số liệu; (6) phân tích, hoàn thiện thuyết minh và bàn giao.

| Tuần | Công việc chính | Minh chứng hoàn thành |
|---|---|---|
| 1 | Khảo sát nguồn; kiểm kê bo và bộ đo; xác minh dữ liệu. | Danh mục nguồn, phần cứng và rủi ro ban đầu. |
| 2 | Biên dịch mẫu gốc; kiểm tra đầu vào và nguồn checkpoint. | Firmware chạy mẫu; quyết định dùng trọng số hay huấn luyện lại. |
| 3 | Lập tập chia; xây bản C tham chiếu và bộ điều phối. | Manifest dữ liệu; đầu ra tham chiếu trên nhiều mẫu. |
| 4 | Hoàn thiện nhận gói và xuất logits trên MCU. | Bảng đối chiếu ban đầu; kiểm thử gói lỗi. |
| 5 | Rà soát bộ nhớ; xây MLP; huấn luyện lại khi cần. | Checkpoint và lịch sử huấn luyện; báo cáo RAM. |
| 6 | Kiểm thử ≥ 1.000 lượt; khóa cấu hình phát triển. | Nhật ký ổn định; phiên bản firmware dùng để đo. |
| 7 | Bố trí nguồn, GPIO và kiểm tra hệ đo. | Sơ đồ đấu nối; dữ liệu kiểm tra điện áp và tải. |
| 8 | Đo thử; hoàn thiện quy trình và danh sách mẫu năng lượng. | Biên bản phương pháp; quy tắc loại lỗi kỹ thuật. |
| 9 | Thực hiện các phiên đo chính thức; đánh giá tập test. | Tệp dự đoán, dòng điện thô và bảng tài nguyên. |
| 10 | Phân tích theo người và phiên đo; kiểm tra kết quả. | Bảng chỉ số, CI và phân tích chênh lệch. |
| 11 | Viết thuyết minh; rà soát tài liệu và hướng dẫn tái lập. | Bản thuyết minh; README và cấu hình môi trường. |
| 12 | Kiểm thử bàn giao; trình diễn và hoàn thiện hồ sơ. | Sản phẩm phần cứng, mã nguồn và dữ liệu được nghiệm thu. |

- Phân công (349) nguyên văn: *"Phân công theo ba mảng: dữ liệu và mô hình; firmware và bộ nhớ; đo lường và phân tích. Với nhóm hai sinh viên, phân chia lại mảng đo lường nhưng cả hai phải tham gia kiểm chứng hệ thống."* ⚠️ Đề cương ghi "nhóm hai sinh viên" nhưng nhóm có **3 sinh viên** → đưa vào câu hỏi GVHD bên dưới.
- **Điểm kiểm soát bắt buộc:** hết tuần 2 — đánh giá khả năng tái lập; **hết tuần 6 — xác nhận phần mềm ổn định; hết tuần 8 — phê duyệt quy trình đo TRƯỚC khi thu số liệu chính thức.**

## 13. Sản phẩm và tiêu chí nghiệm thu (dòng 352–378)

### 13.1. Sản phẩm bàn giao (352)
Portenta H7 nạp firmware; chương trình chuẩn bị dữ liệu/huấn luyện/điều phối; **mã C/C++ của HAI mô hình**; dự đoán + đo; sơ đồ đấu nối; thuyết minh + hướng dẫn vận hành. Các tệp liên kết bằng **mã cấu hình và mã phiên**, đủ để kiểm tra lại từ dữ liệu thô.

### 13.2. Tiêu chí nghiệm thu (Bảng 8, dòng 354–374)
1. **Nguồn & tái lập:** commit, giấy phép, checksum trọng số, môi trường, hướng dẫn biên dịch; công bố phần mã đã sửa.
2. **Hoạt động trên phần cứng:** thực thi trên **Portenta H7 thực**; nhiều mẫu có mã định danh; xuất logits, nhãn, lỗi.
3. **Tương đương số học:** bảng sai số + tỷ lệ khớp + hồ sơ mẫu khác biệt; dung sai **chốt trước khi dùng test**.
4. **Chất lượng phân loại:** accuracy, macro-F1, F1 từng lớp, confusion matrix trên test; **nêu rõ trạng thái xác minh checkpoint**.
5. **Đối chứng MLP:** chạy trên cùng bo, được kiểm chứng; kết luận phù hợp nguồn gốc tập chia.
6. **Ổn định:** ≥1.000 lượt không reset ngoài dự kiến; theo dõi bộ nhớ, lỗi đầu vào, giá trị không hữu hạn.
7. **Năng lượng:** dữ liệu nguồn thô, GPIO, sơ đồ cấp nguồn, điều kiện đo, kết quả **mJ/lần suy luận**.
8. **Tài nguyên & thống kê:** Flash, RAM theo phương pháp xác định rõ; phân bố thời gian; biến thiên giữa phiên đo.
9. **Báo cáo:** phân biệt kết quả đạt được / giới hạn / giả thuyết / hướng phát triển; trích dẫn đầy đủ.

### 13.3. Nguyên tắc xác nhận (377–378)
- Nghiệm thu theo **mức độ hoàn thành quy trình + tính đúng + chất lượng bằng chứng**; **"không áp đặt độ chính xác hoặc mức giảm năng lượng chưa có cơ sở"**.
- **"Kết quả Mamba không vượt MLP vẫn có giá trị khi phép so sánh được tổ chức đúng và diễn giải trung thực."**
- Không xác minh/tái huấn luyện được checkpoint → **giới hạn kết luận về tổng quát hóa**; không được lấy 1 ảnh dự đoán/1 đầu vào lưu sẵn làm minh chứng cho cả bài toán.

## 14. Rủi ro (Bảng 9, dòng 381–402)

| Rủi ro | Hệ quả | Biện pháp |
|---|---|---|
| Mẫu không biên dịch được | Chậm tích hợp | Khóa phiên bản; rà soát include/thư viện/đường dẫn; lưu lỗi và bản sửa |
| Không rõ nguồn checkpoint | Không đủ cơ sở so sánh tổng quát hóa | Xác minh sớm; huấn luyện lại khi cần; giới hạn kết luận nếu chưa giải quyết |
| Rò rỉ/tràn bộ nhớ | Reset, số đo không ổn định | Theo dõi vòng đời buffer; kiểm giới hạn; thử nhiều lượt |
| Sụt áp/nguồn đi vòng | Sai số năng lượng hoặc lỗi bo | Kiểm đường nguồn duy nhất, điện áp tải, dòng đỉnh trước đo |
| Đo lặp thiếu độc lập | CI bị diễn giải quá mức | Giữ cấu trúc người/phiên/khối; công bố số bo thực tế |
| Mở rộng IMU quá sớm | Vượt thời gian, lệch phạm vi | Chỉ làm sau khi xong mô hình, đối chứng và phép đo |

- Thuyết minh 5 chương (405): 1 bối cảnh–vấn đề–mục tiêu–phạm vi; 2 HAR/Mamba/STM32H7/kế thừa; 3 dữ liệu–mô hình–phần mềm–hệ đo; 4 kết quả gắn bảng–hình–dữ liệu gốc; 5 thảo luận–giới hạn–kết luận–hướng phát triển; phụ lục cấu hình–sơ đồ–hướng dẫn chạy lại.
- Liêm chính (407–408): trích dẫn nguồn; giữ thông báo giấy phép; **không nhận kiến trúc/thư viện kế thừa là thiết kế mới**; số liệu tác giả nguồn phải phân biệt với kết quả đồ án; **"không điền các giá trị dự kiến vào bảng kết quả như số đo đã có"**. Không thu dữ liệu cá nhân mới trong phạm vi bắt buộc. Khi mở rộng sang cảm biến trên người: cần **sự đồng ý phù hợp, mô tả mục đích thu thập và biện pháp bảo vệ dữ liệu**. Mọi tuyên bố về tính ứng dụng **chỉ giới hạn ở điều kiện kiểm chứng** — không mở rộng sang thiết bị y tế hoặc độ tin cậy vận hành dài hạn khi chưa có bằng chứng (408).

## 15. Phụ lục A — Hồ sơ bàn giao (dòng 428–455)

| Tệp/thư mục | Nội dung cần lưu |
|---|---|
| `source_manifest.json` | Địa chỉ nguồn, commit, giấy phép, **checksum trọng số**, ngày tiếp nhận |
| `split_manifest.csv` | sample_id, subject_id, nhãn, tập chia, đường dẫn dữ liệu |
| `model_manifest.json` | Kiến trúc, chiều tensor, kiểu số, quy trình tiền xử lý, nguồn checkpoint |
| `predictions.csv` | Mã mẫu, nhãn thật, nhãn dự đoán, logits ref + MCU, mã cấu hình |
| `measurements.csv` | Mã phiên/khối/lượt, mẫu, thời gian, năng lượng, điện áp, trạng thái hợp lệ |
| `raw_measurements/` | Dòng điện + GPIO nguyên gốc; thiết lập lấy mẫu và hệ số quy đổi |
| `build_artifacts/` | Firmware, map file, linker script, cờ biên dịch, báo cáo tài nguyên |
| `environment/` | Tệp khóa phiên bản, thông tin OS, hướng dẫn tạo môi trường |
| `hardware_manifest.md` | Bo, mã thiết bị đo, trạng thái ngoại vi, sơ đồ nguồn, ảnh bố trí |
| `README.md` | Trình tự chuẩn bị–chạy thử–đo–phân tích + giới hạn đã biết |

- **A.2 toàn vẹn:** mỗi `sample_id` duy nhất và liên kết `subject_id`; số dòng dự đoán = số mẫu thực gửi (trừ lỗi ghi riêng); mỗi phép đo có cấu hình + mã phiên + tệp nguồn; **kiểm đơn vị trước khi ghép** (giây/µs, A, J/mJ).
- **A.3 bảo quản:** giữ riêng thô–đã xử lý–bảng kết quả; **không ghi đè bản gốc**; **một lệnh/chuỗi lệnh trong README tạo lại bảng và hình từ dữ liệu bàn giao**; **trường chưa đo không thay bằng 0** — dùng trạng thái thiếu dữ liệu có giải thích.

## 16. Phụ lục B — Biểu mẫu kiểm soát (dòng 457–503)

- **B.1 Phiếu xác nhận cấu hình trước đo** — 8 trường: ngày/người đo; mã bo–vi điều khiển–lõi; firmware–commit–checksum trọng số; xung CPU–cache–M4–ngoại vi; thiết bị đo–chế độ–tốc độ lấy mẫu; điểm cấp nguồn–điện áp thực–dòng đỉnh; chân GPIO + ranh giới đo; danh sách mẫu–seed–số phiên/khối.
- **B.2 Trình tự:** *Trước* — kiểm điện áp/cực tính, không nguồn đi vòng, thử 1 đầu vào hợp lệ, kiểm GPIO + tệp ghi. *Trong* — không đổi cấu hình, theo dõi lỗi kỹ thuật, giữ nguyên dữ liệu thô. *Sau* — kiểm số lượt, đơn vị, tệp nguồn, đối chiếu đầu ra. **Chỉ phân tích khi hồ sơ cấu hình đầy đủ.**
- **B.3 Bảng B1** — 6 chỉ tiêu chờ thực nghiệm (accuracy/macro-F1; sai số logits + tỷ lệ khớp; trung vị + p95 thời gian; Flash/RAM theo phạm vi đo; năng lượng tổng mJ/lượt; số người–phiên–bo) — hiện ghi "Chưa thực nghiệm"/"Chưa xác nhận".
- **⚠️ Dòng 503 (chốt):** *"Ngưỡng số học, thông số đo và mọi thay đổi so với đề cương phải được giảng viên hướng dẫn xác nhận trước khi đánh giá chính thức. Các ô trên chỉ được thay bằng số liệu đã có tệp nguồn và điều kiện thực nghiệm tương ứng."*

---

# PHÂN TÍCH KHOẢNG CÁCH — HIỆN TRẠNG vs YÊU CẦU (18/10/2026)

> Nguồn số liệu: build Portenta tại `firmware/mambahar-portenta-h7/logs/build_20261018_191542.txt` (307.096/786.432 B Flash; 77.256/523.624 B RAM); commit upstream `44d51fce…` ghi trong `source_manifest.json`. Các mục đánh dấu "quan sát ngoài đề cương" là kết quả làm việc của nhóm, không phải yêu cầu trong đề cương.

## Đã có (khớp yêu cầu)

| Yêu cầu | Trạng thái |
|---|---|
| Tuần 1 — khảo sát nguồn | ✅ Đã clone MambaLite-Micro @ `44d51fc` + `source_manifest.json` (còn thiếu **checksum trọng số**) |
| Tuần 2 — biên dịch mẫu gốc | ✅ Build thành công **Portenta H7** (307.096/786.432 B Flash = 39,0%; 77.256/523.624 B RAM = 14,8%) + ESP32-S3 (bước đệm, ngoài phạm vi bắt buộc) |
| Nguồn gốc không sửa + nhánh phát triển (§7.4) | ✅ Upstream clone nguyên bản; project dev tách riêng `firmware/mambahar-portenta-h7` + `firmware/mambahar-esp32s3` |
| Giới hạn bộ nhớ (768 KB / 511,35 KB) | ✅ Số build khớp linker: 786.432 B = 768 KB, 523.624 B ≈ 511,4 KB |

## Chưa làm — cần hành động

| # | Việc | Thuộc | Hạn |
|---|---|---|---|
| 1 | Kiểm kê phần cứng: Portenta ABX00042; cáp USB-C data; **PPK2 (lab không có sẵn → phải mua hoặc mượn bộ tương đương)**; nguồn DC 5V; VOM; dây/adapter | Tuần 1 | Ngay |
| 2 | **Xác nhận khả năng truy cập môi trường huấn luyện lại (GPU) — trong 2 tuần đầu** | §7.4 | Cuối tuần 2 |
| 3 | Tải UCI HAR; kiểm số mẫu/nhãn **từ tệp thực** (không suy từ tỷ lệ người) | Tuần 1–2 | Cuối tuần 2 |
| 4 | Kiểm tra **nguồn checkpoint** trọng số [8] → quyết định **dùng trọng số hay huấn luyện lại** (minh chứng tuần 2) | Tuần 2 | Cuối tuần 2 |
| 5 | Bổ sung **checksum trọng số** vào `source_manifest.json` | §7.4/A1 | Cuối tuần 2 |
| 6 | Firmware **chạy mẫu trên bo thật** (cần bo Portenta) | Tuần 2 | Khi có bo |

## Điểm kỹ thuật phải nhớ khi viết code (từ đọc kỹ)

- MT2: firmware phải xuất **6 logits + nhãn + trạng thái** — sửa `mambahar.c` (hiện chỉ argmax).
- Nhiều mẫu + mã định danh + checksum + timeout + **không in log trong vùng đo** (Bảng 3).
- Reset trạng thái giữa các mẫu (batch=1); vùng làm việc reset trước mỗi inference; ≥1.000 lượt liên tiếp không reset.
- Bản C tham chiếu chạy trên PC **trước** khi so MCU (tuần 3).
- Dung sai số học: chốt trên dev set **trước khi mở test** — ⚠️ cần GVHD xác nhận con số.
- Bộ điều phối: gửi **570 FP32** mỗi mẫu; nhãn thật không vào hàm suy luận.

## Câu hỏi cần chốt với GVHD

1. Ngưỡng dung sai số học (e_max/MAE) đề xuất bao nhiêu? (đề cương chưa cho số — dòng 503 buộc GVHD xác nhận)
2. Có được dùng phòng lab/GPU trường để huấn luyện lại không (nếu checkpoint không xác minh được)? — phải trả lời **trong 2 tuần đầu** (§7.4, dòng 251)
3. **PPK2 chắc chắn không có trong lab** → chọn đường nào: (a) nhóm tự mua PPK2 (đưa vào dự toán mua sắm), (b) dùng INA226 + bộ ghi độc lập làm phương án chính (hệ quả: nếu tốc độ không đủ phân giải từng lượt → chỉ báo cáo năng lượng trung bình khối), hay (c) liên hệ mượn bộ đo tương đương nơi khác? Phải chốt **trước khi thu số liệu chính thức** (dòng 503).
4. Nguồn DC 5 V cho Portenta: đấu vào đầu vào nguồn được chỉ định nào, qua adapter nào? (theo sơ đồ nguồn chính thức [9])
5. §11.3 ghi *"Với nhóm hai sinh viên..."* nhưng nhóm có 3 sinh viên — xác nhận chia 3 mảng (1 người/mảng) hay giữ cách chia khác?
6. Cách chọn 60 mẫu năng lượng từ tập phát triển (đảm bảo đủ 6 lớp) — xác nhận phương án chọn trước khi đo.

---

## 17. Tài liệu tham khảo (dòng 409–424)

[1] Gu & Dao — Mamba, arXiv:2312.00752. [2] Xu et al. — MambaLite-Micro, arXiv:2509.05488v1. [3] Reyes-Ortiz et al. — UCI HAR, DOI 10.24432/C54S4K. [4] Repo MambaLite-Micro (MIT). [5] `Python/train.py`. [6] `examples/mambahar-arduino-6/platformio.ini`. [7] `main.cpp` + `include/mambahar.c`. [8] `include/mamba_weights.h`. [9] Arduino Portenta H7 docs (ABX00042/45/46). [10] PlatformIO `portenta_h7_m7`. [11] Nordic PPK2. [12] TI INA226. [13] sklearn GroupShuffleSplit. [14] sklearn f1_score.

*Tài liệu trực tuyến đối chiếu ngày **22/09/2026**; bản dùng trong đồ án phải lưu thêm commit/phiên bản cụ thể (410).*

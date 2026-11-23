# tools/energy — công cụ PC cho phép đo năng lượng

Ba công cụ và bộ kiểm thử bằng **dữ liệu tổng hợp** (chưa có số đo thật). Chỉ dùng thư viện chuẩn Python 3 (không cần numpy/pandas; `capture.py --port` cần `pyserial`).

| Tệp | Việc |
|---|---|
| `schedule.py` | Lập lịch phiên: `xorshift32`, hoán vị 60 mẫu, `pulse_plan`, phân tích lệnh `START`. Khớp bản C `firmware/energy-esp32s3/src/energy_sched.c` (Brief 07). |
| `capture.py` | Thu dòng từ USB-CDC của XIAO vào một tệp CSV **nguyên văn**, kèm `sha256`. |
| `merge_blocks.py` | Ghép tệp logger với log UART devkit → năng lượng theo khối. |
| `test/` | `make_synthetic.py` (dựng phiên giả), `test_*.py`, `run_tests.sh`. |

## Quy trình một phiên (do người kiểm tra làm)

1. Nối dây theo `firmware/energy-logger-xiao/README.md` và `firmware/energy-esp32s3/README.md`. Devkit chạy từ nguồn qua INA226, **không cắm USB devkit**.
2. PC: mở capture **trước** khi gửi lệnh (capture phải bao trùm toàn phiên):
   ```powershell
   py -3 tools\energy\capture.py --port COM7 --out logs\s1_logger.csv
   ```
   (`--send P` gửi `PING` sau khi mở cổng; `--seconds N` tự dừng. Dòng cuối bị cắt dở khi dừng không được ghi; dòng đầu có thể bị cắt do mở cổng giữa dòng và vào `bad_lines`. Vài trăm dòng `S` đầu tiên có thể là dữ liệu cũ trong vòng đệm USB của logger, có `t_us` nhỏ hơn hẳn.)
3. Gửi lệnh tới devkit qua adapter USB-TTL (UART0, 115200 8N1), và **lưu log UART của devkit ra một tệp văn bản**. **Gửi một dòng trống (chỉ `LF`) và chờ ~0,5 s trước `START`**: lần đầu gửi `START` ngay thì devkit trả `ERR cmd` (nghi một byte rác từ adapter dính vào đầu lệnh; chưa chứng minh nguyên nhân). Devkit trả `ERR cmd` cho dòng trống, vô hại. Lệnh:
   `START <session 1..5> <MF|LF> <seed>` (ví dụ `START 1 MF 42`). Devkit in `ACK …` rồi chạy.
4. Chờ dòng `SESSION_DONE session=<s>` ở log devkit, rồi dừng capture (Ctrl-C).
5. Ghép:
   ```powershell
   py -3 tools\energy\merge_blocks.py --logger logs\s1_logger.csv --devkit logs\s1_devkit.txt --session 1 --rshunt 0.1 --outdir logs\s1_out
   ```
   Ra `measurements_session1.csv` và `merge_report_session1.md`. Mã thoát 0 = phiên qua các kiểm tra của code ghép, 1 = phiên không hợp lệ (vẫn ghi tệp), 2 = lỗi đầu vào.

Lập lịch: `py -3 tools\energy\schedule.py --selftest` in hoán vị/START/`pulse_plan` đúng định dạng `sched_expected.txt` của Brief 07 và so từng byte nếu tệp đó có trong cây (`firmware/energy-esp32s3/test/sched_expected.txt`); nếu vắng thì in `bo qua: chua co sched_expected.txt (Brief 07)`. Công cụ không tự tạo tệp đó.

## Định dạng

- **Tệp logger**: dòng `S,t_us,shunt_raw,bus_raw`, `E,t_us,level`, `X,t_us,code`, `STAT,…`; `#` là chú thích (`# host_time_utc=` do capture thêm, `# fw=…` do logger). Chi tiết: `firmware/energy-logger-xiao/README.md`.
- **Log devkit**: dòng `ACK`, `EMP`, `BLK`, `SESSION_DONE` (Brief 07 mục 3, chép ở `firmware/energy-esp32s3/README.md`). Dòng khác bị bỏ qua.
- **`measurements_session<N>.csv`**: dòng `#` mô tả, rồi tiêu đề cột
  `session,block,cfg,kind,pulse,t_rise_us,t_fall_us,dur_ms,n_samples,V_mean,I_mean_A,P_mean_W,I_max_A,E_raw_mJ,E_net_mJ,E_per_inf_raw_mJ,E_per_inf_net_mJ,P_idle_W,devkit_maxdl,devkit_invalid,valid,flags`.
  Đơn vị nằm trong tên cột; `t_rise_us`, `t_fall_us` là thời gian **của logger**. Đọc bằng `pandas.read_csv(..., comment="#")`.

## Cách tính (đều là quy ước của code ghép, không phải ngưỡng của phép đo)

- **Quy đổi** (mã thô → đơn vị): `V_bus = raw·1,25 mV`, `V_shunt = raw·2,5 µV` (có dấu), `I = V_shunt / R_shunt`, `P = V·I`. `R_shunt` là tham số `--rshunt`, mặc định **0,1 Ω danh nghĩa, chưa đo**, và được ghi trong mọi đầu ra. Số liệu là **chưa hiệu chỉnh**.
- **Ghép xung**: hai đồng hồ khác nhau (XIAO, devkit) nên ghép **theo số thứ tự xung** (xung thứ k của logger ↔ `pulse=k`), không theo giá trị thời gian. Phiên là toàn bộ đoạn capture; phải có đúng 32 xung (cặp lên–xuống), xen kẽ đúng. Thừa/thiếu → phiên không hợp lệ và được liệt kê, không tự sửa. Kiểm thêm: `cfg/kind/block` và `idx` (hoán vị theo `seed` trong `ACK`) khớp `schedule.py`.
- **Cảnh báo lệch timer/GPIO** (`flags`): `width_mismatch` nếu độ rộng xung logger lệch quá ±20% so với `t_fall_us − t_rise_us` của devkit; `interval_mismatch` nếu khoảng cách hai xung liên tiếp lệch quá 2 ms + 0,1%.
- **Năng lượng khối** `E_raw`: tích phân hình thang `P(t)` theo thời gian giữa các mẫu nằm trong `[cạnh lên, cạnh xuống]`, cộng hai đoạn biên (cạnh lên → mẫu đầu, mẫu cuối → cạnh xuống) **giữ giá trị mẫu gần nhất**. `P_mean = E_raw / thời lượng`; `V_mean`, `I_mean` là trung bình các mẫu; `E_per_inf = E/10` (chưa hiệu chỉnh).
- **Công suất nền** `P_idle` (trung bình mẫu, độ lệch chuẩn ghi trong báo cáo) từ các cửa sổ: (init) 10 s nghỉ đầu phiên, (rest) 2 s trước xung rỗng đầu mỗi cấu hình, (gap) mọi khoảng nghỉ ≥ 1,6 s giữa hai xung cùng cấu hình; bỏ 300 ms mỗi đầu. `E_net = E_raw − P_idle · thời lượng`. Ghi cả hai, **không** thay `E_raw` bằng `E_net`.
  *Sai khác với brief:* brief viết cửa sổ nền đầu là "ACK+2 s đến xung đầu − 1 s", nhưng firmware chạy 20 lượt ổn định (CPU đang tính) sau 10 s nghỉ nên khoảng đó không yên. Thời điểm `ACK` không có trong đồng hồ logger, nên cửa sổ (init) được suy từ xung đầu tiên và độ dài khối 0 (20 lượt ≈ 2 × khối 0). Nếu giao thức firmware đổi thì cửa sổ này phải đổi theo.
- **Xung rỗng** (`EMP`): báo năng lượng đo được và độ rộng để ước chi phí marker, không trừ vào đâu. Xung ~1 ms với chu kỳ 2,2 ms có 0–1 mẫu; hàng không có mẫu được đánh `no_samples`, `valid=0`.
- **`flags`**: `few_samples` (khối < 20 mẫu), `saturated` (`|shunt_raw| ≥ 32767`), `i2c_gap` (có dòng `X` trong khối hoặc khoảng cách hai mẫu liên tiếp quanh khối > 3 × chu kỳ trung vị), `no_samples`, `no_idle`, `session_invalid`, `unpaired`, `logger_drops` (tăng `drops` giữa `STAT` đầu và cuối).
  `valid=1` khi phiên hợp lệ, hàng có mẫu, không `saturated`, không `i2c_gap`. `few_samples`, `width_mismatch`, `interval_mismatch`, `logger_drops` chỉ là cảnh báo.
- Thời điểm mẫu = ngay sau khi đọc xong thanh ghi bus; chưa bù trễ chuyển đổi của INA226. Mô hình trễ trong test tổng hợp cho thấy ảnh hưởng ở hai biên khối là sai số hệ thống, đáng kể với khối ngắn (MLP ~107 ms).

## Kiểm thử

```bash
bash tools/energy/test/run_tests.sh
```

Dữ liệu tổng hợp: công suất nền và công suất khối là hằng số đã biết; test khẳng định `E_raw`/`E_net` khôi phục được trong 1% (đây là **ngưỡng kiểm thử code**, không phải ngưỡng của phép đo), cùng các ca lỗi (thiếu/thừa xung, mất mẫu giữa khối, shunt bão hòa, dòng `X`, ít mẫu, lệch độ rộng, devkit lệch kế hoạch). Các test này **không** chứng minh phép đo chính xác.

## Giới hạn

INA226 chỉ cho năng lượng theo khối; `R_shunt` danh nghĩa chưa đo; chưa đối chiếu hệ đo bằng tải ổn định; một bo; điều kiện đo (nguồn, nhiệt độ, cáp, firmware commit) phải ghi lại. Chưa có số đo thật nào đi qua các công cụ này.

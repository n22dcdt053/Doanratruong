# ml — MLP đối chứng cho UCI HAR

Thư mục này chứa split theo người, huấn luyện MLP 561-64-6, đánh giá test và xuất
trọng số sang C. Tất cả chạy trên PC; không dùng bo, không dùng cổng COM.

## Môi trường

```powershell
py -3.14 -m venv --system-site-packages .venv-ml
.\.venv-ml\Scripts\python -m pip install scikit-learn
.\.venv-ml\Scripts\python -m pip freeze
```

`ml/requirements.txt` là bản `pip freeze` của môi trường đã dùng (dòng đầu ghi phiên bản Python).
Mọi script dưới đây chạy bằng `.venv-ml\Scripts\python` từ thư mục gốc repo.

## Thứ tự chạy

```powershell
# N2 — kiểm dữ liệu và chia tập
.\.venv-ml\Scripts\python ml\check_dataset.py
.\.venv-ml\Scripts\python ml\make_split.py

# N3 — huấn luyện (chỉ đọc train/val); commit checkpoint TRƯỚC khi đánh giá
.\.venv-ml\Scripts\python ml\train_mlp.py

# N3 — đánh giá test, đúng một lần, sau khi checkpoint đã commit
.\.venv-ml\Scripts\python ml\eval_mlp.py

# N4 — xuất trọng số C và chạy runner host (WSL)
.\.venv-ml\Scripts\python ml\export_mlp_c.py
wsl -e bash -c 'cd /mnt/c/StudyStuff/QBA/DoanNhomQuy && bash firmware/host/run_mlp_host_test.sh --batch firmware/host/logs/uci_test.f32 ml/results/mlp_c_logits_test.csv'
.\.venv-ml\Scripts\python ml\verify_mlp_c.py

# N4 — bảng kích thước và manifest
.\.venv-ml\Scripts\python ml\model_size.py
.\.venv-ml\Scripts\python ml\verify_ml_manifest.py --write
.\.venv-ml\Scripts\python ml\verify_ml_manifest.py
```

## Cảnh báo

- **Không chạy `eval_mlp.py` trước khi commit checkpoint.** Tập test chỉ được đọc một lần,
  sau khi `ml/results/mlp_seed42.pt` đã nằm trong commit.
- Không đổi siêu tham số, seed, kiến trúc hay ngưỡng. Không chạy lại để chọn kết quả đẹp.
- `mlp_weights.h` là file sinh tự động; sửa trọng số bằng `export_mlp_c.py`, không sửa tay.
- Nếu thiếu `firmware/host/logs/uci_test.f32` (gitignored), tạo lại bằng:
  `py -3.14 firmware/host/uci_har.py to-f32 "data/UCI HAR Dataset" firmware/host/logs/uci_test.f32`.

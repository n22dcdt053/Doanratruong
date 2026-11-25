#!/usr/bin/env python3
"""Kiem thu capture.py o che do --replay (khong can cong COM / bo). Chay: py -3 -I tools/energy/test/test_capture.py"""
import hashlib
import io
import re
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import capture  # noqa: E402

SRC_LINES = [
    b"ESP-ROM:esp32s3-20210327",                       # dong rac luc reset: khong khop mau
    b"# fw=abc cfg=0x4127 avg=1 vct_us=1100 rshunt_nominal_ohm=0.1 marker_gpio=1",
    b"S,1000,2400,4000",
    b"S,3200,-12,3999",
    b"E,3300,1",
    b"X,3400,263",
    b"E,4300,0",
    b"STAT,5000000,samples=2,edges=2,drops=0,i2c_err=1",
    b"PING,5000100",
    b"SELFTEST_DONE",
    b"ERR cmd",
    b"S,12,x,9",                                        # sai dinh dang -> bad_lines, van ghi nguyen
    b"E,1,2",                                           # muc 2 khong hop le -> bad_lines
]


def main():
    d = Path(tempfile.mkdtemp(prefix="energy_test_cap_"))
    src = d / "nguon.csv"
    src.write_bytes(b"\r\n".join(SRC_LINES) + b"\r\n\r\n")        # CRLF + dong trong
    out = d / "logs" / "ra.csv"
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = capture.main(["--replay", str(src), "--out", str(out)])
    assert rc == 0
    data = out.read_bytes()
    lines = data.split(b"\n")
    assert lines[-1] == b""
    lines = lines[:-1]
    assert re.fullmatch(rb"# host_time_utc=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", lines[0]), lines[0]
    assert lines[1:] == SRC_LINES, "phai ghi nguyen van moi dong (chi doi ket dong thanh LF)"
    assert b"\r" not in data
    side = Path(str(out) + ".sha256").read_text()
    assert side == "%s  ra.csv\n" % hashlib.sha256(data).hexdigest(), side
    text = buf.getvalue()
    assert "S=2 E=2 X=1 STAT=1 comment=1 other=3 bad_lines=3" in text, text
    assert "ESP-ROM" in text          # dong khong khop mau dau tien duoc in ra
    print("PASS replay_ghi_nguyen_van_sha256_va_dem_dong")

    # --replay doc tep khong co: ma thoat 2
    assert capture.main(["--replay", str(d / "khong_co"), "--out", str(d / "x.csv")]) == 2
    # --send chi di voi --port
    assert capture.main(["--replay", str(src), "--out", str(d / "y.csv"), "--send", "P"]) == 2
    print("PASS dau_vao_sai_tra_ma_2")
    print("test_capture: 2 ca PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

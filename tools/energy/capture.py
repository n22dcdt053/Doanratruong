#!/usr/bin/env python3
"""Thu du lieu tu logger XIAO (USB-CDC) vao mot tep CSV nguyen van (Brief 08, H3).

  py -3 -I tools/energy/capture.py --port COM7 --out logs/session1_logger.csv [--seconds 120] [--send P]
  py -3 -I tools/energy/capture.py --replay tep_mau.csv --out ra.csv          (kiem thu, khong can cong COM)

Ghi NGUYEN VAN tung dong (chi doi ket dong thanh LF), khong sua so. Dong dau tien do capture them:
  # host_time_utc=<ISO 8601>
Dong cuoi khong ket thuc bang LF (bi cat luc dung) khong duoc ghi; dong dau tien co the bi cat (mo cong giua dong) va vao bad_lines.
Khi ket thuc ghi sha256 cua tep ra <out>.sha256 va in tom tat so dong S/E/X/STAT. Dong khong khop mau van duoc ghi
nguyen va tang bad_lines (vd: dong boot cua ROM luc XIAO reset). Cong noi tiep can pyserial (--port); --replay thi khong.

Luu y: mo cong USB Serial/JTAG co the reset XIAO tuy he dieu hanh; script dat DTR/RTS = False truoc khi mo.
Chua thu voi bo that (Brief 08 chi build/kiem thu tren PC).
"""
import argparse
import datetime
import hashlib
import re
import sys
import time
from pathlib import Path

PATTERNS = [
    ("S", re.compile(rb"^S,\d+,-?\d+,\d+$")),
    ("E", re.compile(rb"^E,\d+,[01]$")),
    ("X", re.compile(rb"^X,\d+,-?(0x[0-9a-fA-F]+|\d+)$")),
    ("STAT", re.compile(rb"^STAT,\d+,samples=\d+,edges=\d+,drops=\d+,i2c_err=\d+$")),
    ("comment", re.compile(rb"^#")),
    ("other", re.compile(rb"^(PING,\d+|SELFTEST_DONE|ERR .+)$")),
]


def classify(line):
    for name, rx in PATTERNS:
        if rx.match(line):
            return name
    return "bad_lines"


def iter_replay(path):
    with open(path, "rb") as f:
        for raw in f:
            yield raw


def iter_serial(port, baud, seconds, send):
    try:
        import serial  # pyserial
    except ImportError:
        print("can pyserial de doc cong COM: py -3 -m pip install pyserial (hoac dung --replay)", file=sys.stderr)
        raise SystemExit(2)
    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = port, baud, 0.5
    ser.dtr = False
    ser.rts = False
    ser.open()
    try:
        if send:
            ser.write(send.encode("ascii") + b"\n")
        end = None if seconds is None else time.monotonic() + seconds
        buf = b""
        while end is None or time.monotonic() < end:
            chunk = ser.read(4096)
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                yield line + b"\n"
        # Phan du khong ket thuc bang '\n' la dong BI CAT khi dung capture (da gap: 'S,<t>,1262,43' thay vi
        # 'S,<t>,1262,4306' van khop mau S va se thanh mau sai). Bo di, khong ghi.
        if buf:
            print("(bo dong cuoi bi cat: %r)" % buf.decode("latin-1"), file=sys.stderr)
    finally:
        ser.close()


def run(source, out_path):
    counts = {k: 0 for k in ("S", "E", "X", "STAT", "comment", "other", "bad_lines")}
    total = 0
    first_bad = None
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(out_path, "wb") as f:
        f.write(("# host_time_utc=%s\n" % stamp).encode("ascii"))
        try:
            for raw in source:
                line = raw.rstrip(b"\r\n")
                if not line:
                    continue
                f.write(line + b"\n")
                total += 1
                kind = classify(line)
                counts[kind] += 1
                if kind == "bad_lines" and first_bad is None:
                    first_bad = line
        except KeyboardInterrupt:
            print("(dung theo Ctrl-C)", file=sys.stderr)
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    Path(str(out_path) + ".sha256").write_bytes(("%s  %s\n" % (digest, out_path.name)).encode("utf-8"))
    return counts, total, digest, first_bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--port", help="cong USB-CDC cua XIAO, vd COM7")
    g.add_argument("--replay", type=Path, help="doc tu tep thay cho cong (kiem thu)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--seconds", type=float, help="dung sau N giay (mac dinh: den khi Ctrl-C; --replay: het tep)")
    ap.add_argument("--baud", type=int, default=115200, help="khong anh huong USB-CDC")
    ap.add_argument("--send", help="gui mot lenh (mot ky tu, vd P hoac T) sau khi mo cong")
    a = ap.parse_args(argv)
    if a.send is not None and (len(a.send) != 1 or not a.port):
        print("--send can dung mot ky tu va di voi --port", file=sys.stderr)
        return 2
    if a.replay:
        if not a.replay.is_file():
            print("khong thay tep: %s" % a.replay, file=sys.stderr)
            return 2
        source = iter_replay(a.replay)
    else:
        source = iter_serial(a.port, a.baud, a.seconds, a.send)
    counts, total, digest, first_bad = run(source, a.out)
    print("ghi %s: %d dong (+1 dong host_time_utc)" % (a.out, total))
    print("  S=%(S)d E=%(E)d X=%(X)d STAT=%(STAT)d comment=%(comment)d other=%(other)d bad_lines=%(bad_lines)d" % counts)
    if first_bad is not None:
        print("  dong khong khop mau dau tien: %r" % first_bad.decode("latin-1"))
    print("  sha256 %s -> %s.sha256" % (digest, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

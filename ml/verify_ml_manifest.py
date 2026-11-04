#!/usr/bin/env python3
"""Kiem sha256 cac file cot loi cua MLP theo ml/model_manifest.json.

Chay tu goc repo:
    .venv-ml\\Scripts\\python ml\\verify_ml_manifest.py

Tao manifest (mot lan, khi da co du file):
    .venv-ml\\Scripts\\python ml\\verify_ml_manifest.py --write

Quy uoc hash: file van ban chuan hoa CRLF -> LF truoc khi bam; file nhi phan
(.pt) bam byte tho.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ml" / "model_manifest.json"
DATA = ROOT / "data" / "UCI HAR Dataset"

FILES = [
    "ml/split_manifest.csv",
    "ml/results/mlp_seed42.pt",
    "firmware/common/mlp_weights.h",
    "firmware/common/mlp_har.c",
    "ml/results/test_metrics.json",
    "ml/dataset_checksums.json",
]


def sha256_file(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    if not rel.endswith(".pt"):
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def write_manifest() -> None:
    payload = {
        "hash_basis": "text files: CRLF->LF normalized; .pt: raw bytes",
        "files": {rel: sha256_file(rel) for rel in FILES},
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8", newline="\n")
    print(f"wrote {MANIFEST.relative_to(ROOT).as_posix()}")
    for rel in FILES:
        print(f"  {payload['files'][rel]}  {rel}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="ghi lai ml/model_manifest.json")
    args = ap.parse_args()

    if args.write:
        write_manifest()
        return 0

    if not MANIFEST.is_file():
        print(f"FAIL: khong thay {MANIFEST.relative_to(ROOT).as_posix()}")
        return 1

    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = payload.get("files", {})
    ok = True
    for rel in FILES:
        want = expected.get(rel)
        if want is None:
            print(f"FAIL {rel}: khong co trong manifest")
            ok = False
            continue
        got = sha256_file(rel)
        status = "OK  " if got == want else "FAIL"
        print(f"{status} {rel} {got}")
        if got != want:
            ok = False

    checksums_path = ROOT / "ml" / "dataset_checksums.json"
    if DATA.is_dir() and checksums_path.is_file():
        checksums = json.loads(checksums_path.read_text(encoding="utf-8"))
        for rel, want in sorted(checksums.items()):
            path = DATA / rel
            if not path.is_file():
                print(f"SKIP {rel}: khong co file du lieu")
                continue
            got = hashlib.sha256(path.read_bytes()).hexdigest()
            status = "OK  " if got == want else "FAIL"
            print(f"{status} data/{rel} {got}")
            if got != want:
                ok = False

    print("KET QUA: " + ("tat ca OK" if ok else "co FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

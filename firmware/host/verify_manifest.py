#!/usr/bin/env python3
"""Verify sha256 of every file listed in source_manifest.json.

Hashes are computed over the raw file bytes with CRLF normalized to LF (see the
manifest's hash_basis field), so the same value reproduces on Windows and Linux.

Usage: python -I firmware/host/verify_manifest.py [--root DIR]
Exit 0 when every file matches; 1 when a hash differs or a file is missing.
"""
import argparse
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def normalized_digest(path):
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def manifest_entries(manifest):
    # weights.file is relative to local_checkout; the other entries are repo-relative
    yield manifest["local_checkout"] + manifest["weights"]["file"], manifest["weights"]["sha256"]
    for item in manifest["vendored"] + manifest["upstream_files"]:
        yield item["file"], item["sha256"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(REPO), help="repo root to verify (default: repository of this script)")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    manifest = json.loads((root / "source_manifest.json").read_bytes())
    failures = 0
    for rel, expected in manifest_entries(manifest):
        expected = expected.lower()
        path = root / rel
        if not path.is_file():
            print(f"MISSING {rel}")
            failures += 1
            continue
        got = normalized_digest(path)
        if got == expected:
            print(f"OK {rel}")
        else:
            print(f"MISMATCH {rel} expected={expected} got={got}")
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Generate src/build_info.h before every build so the firmware log names the
exact source revision it was built from (thesis form B.1: firmware-commit-checksum).

Run automatically by PlatformIO (extra_scripts = pre:scripts/gen_build_info.py),
not standalone: SCons provides env/$PROJECT_DIR.
"""
import datetime
import subprocess
from pathlib import Path

Import("env")  # noqa: F821 - injected by PlatformIO/SCons

PROJECT = Path(env["PROJECT_DIR"])  # noqa: F821
REPO = PROJECT.parents[1]
HEADER = PROJECT / "src" / "build_info.h"


def git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=REPO, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


commit = git("rev-parse", "--short", "HEAD")
dirty = "dirty" if git("status", "--porcelain", "--untracked-files=no") else "clean"
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

content = (
    "#pragma once\n"
    f'#define FW_GIT_COMMIT "{commit}"\n'
    f'#define FW_GIT_DIRTY "{dirty}"\n'
    f'#define FW_BUILD_UTC "{now}"\n'
)
# Only touch the header when it actually changes, otherwise main.c rebuilds every time.
if not HEADER.exists() or HEADER.read_text(encoding="ascii") != content:
    HEADER.write_text(content, encoding="ascii")
print(f"build_info: commit={commit} tree={dirty} utc={now}")

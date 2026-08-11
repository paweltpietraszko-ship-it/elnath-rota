#!/usr/bin/env python3
"""ROLE: append-only writer for log/session.txt. CLI: session_log.py "<entry>" """
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path("log/session.txt")
# characters that act as line/record boundaries to str.splitlines() (plus NUL)
FORBIDDEN_CHARS = {
    "\n", "\r", "\x00", "\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85",
    " ", " ",
}


def _needs_leading_newline() -> bool:
    exists = getattr(LOG_FILE, "exists", None)
    if not callable(exists) or not exists():
        return False
    read_text = getattr(LOG_FILE, "read_text", None)
    if not callable(read_text):
        return False
    existing = read_text(encoding="utf-8")
    return bool(existing) and not existing.endswith("\n")


def append_entry(entry: str) -> None:
    if entry.strip() == "":
        raise ValueError("empty entry rejected")
    if FORBIDDEN_CHARS & set(entry):
        raise ValueError("control character in entry rejected")
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    prefix = "\n" if _needs_leading_newline() else ""
    line = f"{prefix}TIMESTAMP: {timestamp} | ENTRY: {entry}\n"
    stream = LOG_FILE.open("a", encoding="utf-8") if isinstance(LOG_FILE, Path) else LOG_FILE.open("a")
    with stream as f:
        written = f.write(line)
    if written != len(line):
        raise OSError(f"partial write: wrote {written} of {len(line)} characters")
    print(f"STATUS: APPENDED\n{line}", end="")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: session_log.py \"<entry>\"")
        sys.exit(1)
    try:
        append_entry(sys.argv[1])
    except (OSError, ValueError) as exc:
        print(f"STATUS: FAIL\nREASON: {exc}")
        sys.exit(1)

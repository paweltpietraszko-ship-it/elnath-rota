#!/usr/bin/env python3
"""
ROLE: FROZEN.lock management for Elnath Ward
COMMANDS:
  guard freeze <file>              — compute SHA256, write FROZEN.lock
  guard freeze --recompute <file>  — recompute SHA256, update FROZEN.lock
  guard check <file>               — verify file matches FROZEN.lock
OUTPUT: structured key:value, no prose
NOTE: freeze only ever accepts arch/spec.md as its target (the sole
      frozen artifact in this repo) — see arch/spec.md invariants.
"""
import sys
import hashlib
from pathlib import Path

LOCK_FILE = Path("arch/FROZEN.lock")
FREEZE_TARGET = Path("arch/spec.md")


def compute_sha256(filepath: Path) -> str:
    return hashlib.sha256(filepath.read_bytes()).hexdigest()


def parse_lock() -> tuple[str | None, str | None, str | None]:
    """Returns (sha, file_field, error) — error is set on any malformed lock."""
    try:
        text = LOCK_FILE.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return None, None, f"FROZEN.lock is not valid text: {exc}"
    shas, files = [], []
    for line in text.splitlines():
        if line.startswith("SHA256:"):
            shas.append(line.split(":", 1)[1].strip())
        elif line.startswith("FILE:"):
            files.append(line.split(":", 1)[1].strip())
    if not shas:
        return None, None, "FROZEN.lock malformed — SHA256 field missing"
    if len(shas) > 1:
        return None, None, "FROZEN.lock contains conflicting SHA256 records"
    if len(files) != 1:
        return None, None, "FROZEN.lock malformed — FILE field missing or ambiguous"
    return shas[0], files[0], None


def write_lock(content: str) -> None:
    """Atomically replace LOCK_FILE on real Path targets; a failed write
    never leaves a partially-overwritten FROZEN.lock behind. Falls back to
    a direct write for non-Path test doubles that don't support the
    temp-file/replace protocol.
    """
    if not isinstance(LOCK_FILE, Path):
        written = LOCK_FILE.write_text(content)
        if written != len(content):
            raise OSError(f"partial write: wrote {written} of {len(content)} characters")
        return
    tmp = LOCK_FILE.with_suffix(".tmp")
    written = tmp.write_text(content, encoding="utf-8")
    if written != len(content):
        tmp.unlink(missing_ok=True)
        raise OSError(f"partial write: wrote {written} of {len(content)} characters")
    tmp.replace(LOCK_FILE)


def cmd_freeze(filepath: Path, recompute: bool) -> None:
    if filepath != FREEZE_TARGET:
        print(f"STATUS: FAIL\nREASON: freeze target must be {FREEZE_TARGET}")
        sys.exit(1)
    if not filepath.exists():
        print(f"STATUS: FAIL\nREASON: file not found: {filepath}")
        sys.exit(1)
    if LOCK_FILE.exists() and not recompute:
        print("STATUS: FAIL\nREASON: FROZEN.lock exists — use --recompute to update")
        sys.exit(1)
    sha = compute_sha256(filepath)
    posix_path = filepath.as_posix()
    write_lock(f"FILE: {posix_path}\nSHA256: {sha}\n")
    print(f"STATUS: FROZEN\nFILE: {posix_path}\nSHA256: {sha}")


def cmd_check(filepath: Path) -> None:
    if not filepath.exists():
        print(f"STATUS: FAIL\nREASON: file not found: {filepath}")
        sys.exit(1)
    if not LOCK_FILE.exists():
        print("STATUS: FAIL\nREASON: FROZEN.lock not found — run guard freeze first")
        sys.exit(1)
    lock_sha, file_field, error = parse_lock()
    if error:
        print(f"STATUS: FAIL\nREASON: {error}")
        sys.exit(1)
    if file_field is not None and Path(file_field) != filepath:
        print(f"STATUS: FAIL\nREASON: FROZEN.lock FILE record ({file_field}) does not match {filepath}")
        sys.exit(1)
    current_sha = compute_sha256(filepath)
    if current_sha == lock_sha:
        print(f"STATUS: PASS\nSHA256: {current_sha}")
    else:
        print(f"STATUS: FAIL\nREASON: hash mismatch\nEXPECTED: {lock_sha}\nACTUAL: {current_sha}")
        sys.exit(1)


def parse_freeze_args(args: list[str]) -> tuple[bool, str] | None:
    recompute, positional = False, []
    for a in args:
        if a == "--recompute":
            recompute = True
        elif a.startswith("--"):
            return None
        else:
            positional.append(a)
    if len(positional) != 1:
        return None
    return recompute, positional[0]


def parse_check_args(args: list[str]) -> str | None:
    positional = []
    for a in args:
        if a.startswith("--"):
            return None
        positional.append(a)
    if len(positional) != 1:
        return None
    return positional[0]


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] not in ("freeze", "check"):
        print("USAGE: guard freeze [--recompute] <file>\n       guard check <file>")
        sys.exit(1)

    cmd, rest = args[0], args[1:]

    if cmd == "freeze":
        parsed = parse_freeze_args(rest)
        if parsed is None:
            print("STATUS: FAIL\nREASON: invalid arguments for freeze")
            sys.exit(1)
        recompute, file_arg = parsed
        cmd_freeze(Path(file_arg), recompute)

    elif cmd == "check":
        file_arg = parse_check_args(rest)
        if file_arg is None:
            print("STATUS: FAIL\nREASON: invalid arguments for check")
            sys.exit(1)
        cmd_check(Path(file_arg))


if __name__ == "__main__":
    main()

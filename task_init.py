#!/usr/bin/env python3
"""
ROLE: create Task folder structure + snapshot repo state for Elnath Ward
CLI: task_init.py <task_id>
CREATES:
  tasks/<task_id>/
  tasks/<task_id>/repo_before.hash
  tasks/<task_id>/round_01/
  tasks/<task_id>/round_01/implementation/
  tasks/<task_id>/round_01/tests/
OUTPUT: structured key:value to stdout
"""
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TASKS_DIR = Path("tasks")
TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def get_head_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], capture_output=True, text=True, encoding="utf-8"
    )
    sha = result.stdout.strip()
    if result.returncode != 0 or not SHA_PATTERN.fullmatch(sha):
        print(f"STATUS: FAIL\nREASON: git did not return a valid HEAD sha: {sha!r}")
        sys.exit(1)
    return sha


def validate_task_id(task_id: str) -> None:
    invalid = not TASK_ID_PATTERN.fullmatch(task_id)
    reserved = task_id.upper() in WINDOWS_RESERVED_NAMES
    if invalid or reserved:
        print(f"STATUS: FAIL\nREASON: invalid task_id: {task_id!r}")
        sys.exit(1)


def create_task_structure(task_id: str) -> Path:
    validate_task_id(task_id)
    task_path = TASKS_DIR / task_id
    if task_path.exists():
        print(f"STATUS: FAIL\nREASON: tasks/{task_id}/ already exists")
        sys.exit(1)
    (task_path / "round_01" / "implementation").mkdir(parents=True)
    (task_path / "round_01" / "tests").mkdir(parents=True)
    return task_path


def write_repo_before_hash(task_path: Path, head_sha: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    content = f"HEAD_SHA: {head_sha}\nTIMESTAMP: {timestamp}\n"
    target = task_path / "repo_before.hash"
    tmp = target.with_suffix(".tmp")
    written = tmp.write_text(content, encoding="utf-8")
    if written != len(content):
        raise OSError(f"partial write: wrote {written} of {len(content)} characters")
    tmp.replace(target)


def run_task_init(task_id: str) -> None:
    head_sha = get_head_sha()
    task_path = TASKS_DIR / task_id
    try:
        create_task_structure(task_id)
        write_repo_before_hash(task_path, head_sha)
    except OSError:
        shutil.rmtree(task_path, ignore_errors=True)
        raise
    print(
        f"STATUS: CREATED\nTASK: {task_id}\nHEAD_SHA: {head_sha}\nPATH: {task_path}/"
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: task_init.py <task_id>")
        sys.exit(1)
    run_task_init(sys.argv[1])

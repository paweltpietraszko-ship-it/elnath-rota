#!/usr/bin/env python3
"""
ROLE: Mechanical gate for CC commits in Elnath Ward
RUNS: after CC commit, before Codex
INPUT: brief.md (TASK_SCOPE), before_sha, head_sha
OUTPUT: backend.txt — STATUS / HEAD_SHA / CHECKS / REASON
RULES: no interpretation, no negotiation — PASS or FAIL only

CHECKS:
  TASK_SCOPE    — brief declares a TASK_SCOPE section; entries are repo-relative
  STALE_HEAD    — head_sha argument matches actual repository HEAD
  GIT_DIFF      — git diff/rev-parse must succeed, never silently ignored
  FROZEN_LOCK   — arch/spec.md hash matches FROZEN.lock (single, unambiguous record)
  DIFF_SCOPE    — changed/new/deleted files (incl. renames) match TASK_SCOPE
  NEW_FILES     — at most 2 new files per Task
  DELETED_FILES — deleted files declared in TASK_SCOPE
  RUFF          — static analysis within limits (stdout + stderr)
  SIZE_FILE     — max 600 lines per file
  SIZE_FUNC     — max 50 lines per function
  RATIO         — insertions/deletions >5:1 → WYMAGA_DECYZJI
  TOTAL_LINES   — total changed lines >150 → WYMAGA_DECYZJI

KNOWN_LIMITATION (accepted 2026-08-08, see T007 DELIVERY):
  RATIO does not fire when deletions == 0 (pure insertions, e.g. a brand-new
  file). NEW_FILES and TOTAL_LINES already guard against runaway new-file
  Tasks; making every new file trigger WYMAGA_DECYZJI regardless of size was
  judged noise, not a real gap.
"""
import ast
import hashlib
import subprocess
import sys
from pathlib import Path

ARCH_FILE = Path("arch/spec.md")
LOCK_FILE = Path("arch/FROZEN.lock")
MAX_FILE_LINES = 600
MAX_FUNC_LINES = 50
MAX_NEW_FILES = 2
RATIO_THRESHOLD = 5
TOTAL_LINES_THRESHOLD = 150
CHECKS = (
    "TASK_SCOPE / STALE_HEAD / GIT_DIFF / FROZEN_LOCK / DIFF_SCOPE / NEW_FILES / "
    "DELETED_FILES / RUFF / SIZE_FILE / SIZE_FUNC / RATIO / TOTAL_LINES"
)


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def is_pipeline_artifact(filepath: str) -> bool:
    return filepath.startswith("tasks/") or filepath.startswith("log/")


def find_excluded_artifacts(changed: dict) -> list[str]:
    all_files = changed["added"] + changed["modified"] + changed["deleted"]
    return [f for f in all_files if is_pipeline_artifact(f)]


def check_frozen_lock() -> str | None:
    if not LOCK_FILE.exists():
        return "FROZEN.lock not found"
    if not ARCH_FILE.exists():
        return f"{ARCH_FILE} not found"
    current = hashlib.sha256(ARCH_FILE.read_bytes()).hexdigest()
    try:
        lock_text = LOCK_FILE.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return f"FROZEN.lock is not valid text: {exc}"
    shas = [
        line.split(":", 1)[1].strip()
        for line in lock_text.splitlines()
        if line.startswith("SHA256:")
    ]
    if not shas:
        return "FROZEN.lock malformed — SHA256 field missing"
    if len(shas) > 1:
        return "FROZEN.lock contains conflicting SHA256 records"
    if current != shas[0]:
        return "arch/spec.md modified outside guard"
    return None


def read_task_scope(brief_path: Path) -> list[str]:
    try:
        text = brief_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"unable to read brief: {exc}")
    scope, in_scope, found = [], False, False
    for line in text.splitlines():
        if line.startswith("TASK_SCOPE:"):
            in_scope, found = True, True
            continue
        if in_scope:
            stripped = line.strip()
            if stripped.startswith("-"):
                scope.append(stripped.lstrip("- ").strip())
            elif stripped and not stripped.startswith("#"):
                in_scope = False
    if not found:
        raise ValueError("TASK_SCOPE missing in brief")
    return scope


def check_scope_paths(scope: list[str]) -> list[str]:
    errors = []
    for entry in scope:
        p = Path(entry)
        if not entry:
            errors.append("TASK_SCOPE: empty scope entry")
        elif p.is_absolute() or p.drive or p.root:
            errors.append(
                f"TASK_SCOPE: entry is outside repository (absolute path): {entry}"
            )
        elif ".." in p.parts:
            errors.append(
                f"TASK_SCOPE: entry escapes repository (parent traversal): {entry}"
            )
    return errors


def check_head_freshness(head_sha: str) -> str | None:
    result = run_cmd(["git", "rev-parse", "HEAD"])
    if result.returncode != 0:
        return f"unable to resolve repository HEAD: {result.stderr.strip()}"
    actual = result.stdout.strip()
    if actual != head_sha:
        return f"head_sha {head_sha} does not match repository HEAD {actual}"
    return None


def classify_status(status: str, parts: list[str], buckets: dict) -> str | None:
    if status.startswith("R"):
        buckets["deleted"].append(parts[0])
        buckets["added"].append(parts[-1])
    elif status.startswith("C"):
        buckets["added"].append(parts[-1])
    elif status == "A":
        buckets["added"].append(parts[-1])
    elif status in ("M", "T"):
        buckets["modified"].append(parts[-1])
    elif status.startswith("D"):
        buckets["deleted"].append(parts[-1])
    else:
        return f"unrecognized git status {status!r} for {parts[-1] if parts else '?'}"
    return None


def get_changed_files(before_sha: str, head_sha: str) -> tuple[dict, str | None]:
    result = run_cmd(["git", "diff", "--name-status", before_sha, head_sha])
    empty = {"added": [], "modified": [], "deleted": []}
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        return empty, f"git diff failed for {before_sha}..{head_sha}: {error}"
    buckets = {"added": [], "modified": [], "deleted": []}
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        status, *parts = line.split("\t")
        error = classify_status(status, parts, buckets)
        if error:
            return empty, error
    return buckets, None


def get_diff_stats(before_sha: str, head_sha: str, scope: list[str]) -> tuple[dict, str | None]:
    paths = [f for f in scope if not is_pipeline_artifact(f)]
    empty = {"insertions": 0, "deletions": 0}
    if not paths:
        return empty, None
    result = run_cmd(["git", "diff", "--numstat", before_sha, head_sha, "--"] + paths)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        return empty, f"git diff --numstat failed: {error}"
    ins, dels = 0, 0
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            try:
                ins += int(parts[0])
                dels += int(parts[1])
            except ValueError:
                pass
    return {"insertions": ins, "deletions": dels}, None


def check_scope_and_files(changed: dict, scope: list[str]) -> list[str]:
    errors = []
    added = [f for f in changed["added"] if not is_pipeline_artifact(f)]
    modified = [f for f in changed["modified"] if not is_pipeline_artifact(f)]
    deleted = [f for f in changed["deleted"] if not is_pipeline_artifact(f)]
    for f in added + modified + deleted:
        if f not in scope:
            errors.append(f"DIFF_SCOPE: file outside TASK_SCOPE: {f}")
    if len(added) > MAX_NEW_FILES:
        errors.append(f"NEW_FILES: {len(added)} new files (max {MAX_NEW_FILES})")
    for f in deleted:
        if f not in scope:
            errors.append(f"DELETED_FILES: deleted file not in TASK_SCOPE: {f}")
    return errors


def max_func_lines(filepath: Path) -> tuple[int, str]:
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return 0, ""
    max_len, max_name = 0, ""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.end_lineno and node.lineno:
                length = node.end_lineno - node.lineno + 1
                if length > max_len:
                    max_len, max_name = length, node.name
    return max_len, max_name


def check_sizes(scope: list[str]) -> list[str]:
    errors = []
    for f in scope:
        p = Path(f)
        if not p.exists() or p.suffix != ".py":
            continue
        lines = len(p.read_text(encoding="utf-8").splitlines())
        if lines > MAX_FILE_LINES:
            errors.append(f"SIZE_FILE: {f} has {lines} lines (max {MAX_FILE_LINES})")
        func_len, func_name = max_func_lines(p)
        if func_len > MAX_FUNC_LINES:
            errors.append(f"SIZE_FUNC: {f}:{func_name} has {func_len} lines (max {MAX_FUNC_LINES})")
    return errors


def check_ruff(scope: list[str]) -> list[str]:
    py_files = [f for f in scope if f.endswith(".py") and Path(f).exists()]
    if not py_files:
        return []
    try:
        result = run_cmd(["ruff", "check"] + py_files)
    except OSError as exc:
        return [f"RUFF: unable to launch ruff: {exc}"]
    if result.returncode != 0:
        output_lines = result.stdout.splitlines() + result.stderr.splitlines()
        return [f"RUFF: {line}" for line in output_lines if line.strip()]
    return []


def check_ratio(stats: dict) -> list[str]:
    ins, dels = stats["insertions"], stats["deletions"]
    total = ins + dels
    wymaga = []
    if dels > 0 and ins / dels > RATIO_THRESHOLD:
        wymaga.append(f"RATIO: {ins}/{dels} = {ins/dels:.1f}:1 (threshold {RATIO_THRESHOLD}:1)")
    if total > TOTAL_LINES_THRESHOLD:
        wymaga.append(f"TOTAL_LINES: {total} lines changed (threshold {TOTAL_LINES_THRESHOLD})")
    return wymaga


def find_importers(scope: list[str]) -> list[str]:
    scope_modules = {Path(f).stem for f in scope if f.endswith(".py")}
    importers = []
    for py_file in Path(".").rglob("*.py"):
        if str(py_file) in scope:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[-1] in scope_modules:
                    importers.append(str(py_file))
                    break
            elif isinstance(node, ast.Import):
                if any(a.name.split(".")[-1] in scope_modules for a in node.names):
                    importers.append(str(py_file))
                    break
    return importers


def build_output(status: str, head_sha: str, blockers: list, wymaga: list, importers: list, excluded: list) -> str:
    lines = [f"STATUS: {status}", f"HEAD_SHA: {head_sha}", f"CHECKS: {CHECKS}"]
    if blockers:
        lines += ["REASON:"] + [f"  - {b}" for b in blockers]
    if wymaga:
        lines += ["WYMAGA_DECYZJI:"] + [f"  - {w}" for w in wymaga]
    if importers:
        lines += ["IMPORTERS_FOR_REVIEW:"] + [f"  - {i}" for i in importers]
    if excluded:
        lines += ["EXCLUDED_ARTIFACTS:"] + [f"  - {e}" for e in excluded]
    else:
        lines.append("EXCLUDED_ARTIFACTS: NONE")
    return "\n".join(lines)


def run_backend(brief_path: Path, before_sha: str, head_sha: str, output_path: Path) -> None:
    blockers: list[str] = []
    try:
        scope = read_task_scope(brief_path)
    except ValueError as exc:
        scope = []
        blockers.append(f"TASK_SCOPE: {exc}")

    blockers += check_scope_paths(scope)

    head_err = check_head_freshness(head_sha)
    if head_err:
        blockers.append(f"STALE_HEAD: {head_err}")

    changed, diff_err = get_changed_files(before_sha, head_sha)
    if diff_err:
        blockers.append(f"GIT_DIFF: {diff_err}")
    stats, stats_err = get_diff_stats(before_sha, head_sha, scope)
    if stats_err:
        blockers.append(f"GIT_DIFF: {stats_err}")

    err = check_frozen_lock()
    if err:
        blockers.append(f"FROZEN_LOCK: {err}")
    blockers += check_scope_and_files(changed, scope)
    blockers += check_ruff(scope)
    blockers += check_sizes(scope)

    wymaga = check_ratio(stats)
    importers = find_importers(scope)
    excluded = find_excluded_artifacts(changed)

    status = "FAIL" if blockers else "WYMAGA_DECYZJI" if wymaga else "PASS"
    output = build_output(status, head_sha, blockers, wymaga, importers, excluded)

    write_output(output_path, output)
    print(output)

    if status == "FAIL":
        sys.exit(1)


def write_output(output_path: Path, output: str) -> None:
    if isinstance(output_path, Path):
        written = output_path.write_text(output, encoding="utf-8")
    else:
        written = output_path.write_text(output)
    if written != len(output):
        raise OSError(f"partial write: wrote {written} of {len(output)} characters")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("USAGE: backend.py <brief.md> <before_sha> <head_sha> <output_backend.txt>")
        sys.exit(1)
    run_backend(Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4]))

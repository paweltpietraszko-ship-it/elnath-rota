#!/usr/bin/env python3
"""
ROLE: mechanical "how does this fit the whole program" locator.
No LLM, no summarization, no invented relationships. Given a Python file,
reports its layer, its own top-level symbols, what it imports, and where
each symbol is referenced elsewhere in the repo via `git grep` — split
into PRODUCTION references (rota/api/frontend, tests/tasks/arch excluded)
vs TEST-only references. Reuses the exact git-grep pattern AUDIT-1 used
by hand to classify KEEP vs TEST_ONLY.
CLI:
  where.py <path/to/file.py>
  where.py <path/to/file.py> --symbol NAME
OUTPUT: structured text to stdout.
"""
import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

PRODUCTION_PATHS = ["rota", "api", "frontend/src"]
EXCLUDE_PATHSPECS = [":!tests/**", ":!tasks/**", ":!arch/**", ":!.worktrees/**"]
NON_PRODUCTION_PATHS = ["tests", "tasks", "arch"]


def layer_of(path: Path) -> str:
    parts = path.as_posix().split("/")
    if parts[0] == "rota" and len(parts) > 1:
        return f"rota/{parts[1]}"
    if parts[0] in ("api", "frontend", "tests", "tasks", "arch"):
        return parts[0]
    return "UNKNOWN"


def parse_tree(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


def top_level_symbols(tree: ast.Module) -> list[str]:
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def imports_of(tree: ast.Module) -> list[str]:
    mods: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.append(node.module)
    seen: list[str] = []
    for m in mods:
        if m not in seen:
            seen.append(m)
    return seen


def git_grep(symbol: str, pathspecs: list[str]) -> list[str]:
    cmd = ["git", "grep", "-n", "-w", symbol, "HEAD", "--", *pathspecs]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode not in (0, 1):
        return [f"ERROR running git grep: {result.stderr.strip()}"]
    return [line for line in result.stdout.splitlines() if line]


def looks_like_call(symbol: str, line: str) -> bool:
    """Heuristic only: does this line actually invoke the symbol, or just
    mention its name in prose/docstring/comment? A text match tool cannot
    tell for certain — this narrows the common false-positive case where
    a name is spelled out in a comment/docstring without being called."""
    return re.search(rf"\b{re.escape(symbol)}\s*\(", line) is not None


def report_symbol(symbol: str, own_path: Path) -> None:
    own_prefix = f"HEAD:{own_path.as_posix()}:"
    prod_hits = git_grep(symbol, PRODUCTION_PATHS + EXCLUDE_PATHSPECS)
    prod_hits = [h for h in prod_hits if not h.startswith(own_prefix)]
    test_hits = git_grep(symbol, NON_PRODUCTION_PATHS)
    real_calls = [h for h in prod_hits if looks_like_call(symbol, h)]
    text_only = [h for h in prod_hits if h not in real_calls]

    print(f"SYMBOL: {symbol}")
    print(f"  PRODUCTION_REFERENCES: {len(prod_hits)} (call-shaped: {len(real_calls)}, text-only mention: {len(text_only)})")
    for h in real_calls:
        print(f"    CALL  {h}")
    for h in text_only:
        print(f"    TEXT  {h}")
    print(f"  TEST_TASK_ARCH_REFERENCES: {len(test_hits)}")
    for h in test_hits:
        print(f"    {h}")
    if not real_calls:
        print("  REACHABILITY: TEST_ONLY (no call-shaped production reference found via git grep -w)")
    print("  NOTE: text-match evidence, not a verdict — read the flagged lines yourself before relying on this.")
    print()


def run(path_str: str, only_symbol: str | None) -> None:
    path = Path(path_str)
    if not path.exists():
        print(f"STATUS: FAIL\nREASON: file not found: {path_str}")
        sys.exit(1)

    print(f"FILE: {path.as_posix()}")
    print(f"LAYER: {layer_of(path)}")

    if path.suffix != ".py":
        print("NOTE: non-Python file, symbol/import analysis skipped.")
        return

    tree = parse_tree(path)
    if tree is None:
        print("STATUS: FAIL\nREASON: could not parse file as Python")
        sys.exit(1)

    imports = imports_of(tree)
    print(f"IMPORTS ({len(imports)}):")
    for m in imports:
        print(f"  {m}")
    print()

    symbols = top_level_symbols(tree)
    if only_symbol is not None:
        symbols = [s for s in symbols if s == only_symbol]
        if not symbols:
            print(f"STATUS: FAIL\nREASON: symbol {only_symbol!r} not found at top level of {path_str}")
            sys.exit(1)

    print(f"TOP_LEVEL_SYMBOLS ({len(symbols)}):")
    for s in symbols:
        print(f"  {s}")
    print()

    for s in symbols:
        report_symbol(s, path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--symbol")
    args = parser.parse_args()
    run(args.path, args.symbol)

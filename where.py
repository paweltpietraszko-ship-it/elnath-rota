#!/usr/bin/env python3
"""
ROLE: mechanical raw-hit finder for "where does this name appear".
No LLM, no reachability verdict, no ownership claim. Given a file, lists
its layer, its own top-level Python symbols (if .py) and its imports,
then for a symbol prints every text occurrence found via `git grep`,
tagged DEF/CALL/TEXT and SAME_FILE/OTHER_FILE. This is a raw-hit list to
speed up manual search, not a classification of live/dead/test-only code
— read every flagged line yourself.
CLI:
  where.py <path>                  # .py: lists top-level symbols, no search
  where.py <path> --symbol NAME    # search occurrences of NAME everywhere
OUTPUT: structured text to stdout.
"""
import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

NON_PRODUCTION_PREFIXES = ("tests/", "tasks/", "arch/")
ALWAYS_EXCLUDE_PATHSPECS = [
    ":(exclude).worktrees/**", ":(exclude)node_modules/**",
    ":(exclude)__pycache__/**", ":(exclude).git/**",
]
DEF_RE_TEMPLATE = r"^\s*(async\s+def|def|class)\s+{sym}\b"
CALL_RE_TEMPLATE = r"\b{sym}\s*\("


def _use_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def layer_of(path: Path) -> str:
    parts = path.as_posix().split("/")
    if parts[0] == "rota" and len(parts) > 1:
        return f"rota/{parts[1]}"
    if parts[0] in ("api", "frontend", "tests", "tasks", "arch"):
        return parts[0]
    if len(parts) == 1:
        return "root-script"
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


def is_tracked(path: Path) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    return result.returncode == 0


def working_tree_differs_from_head(path: Path) -> bool:
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", str(path)],
        capture_output=True,
    )
    return result.returncode == 1


def git_grep_word(symbol: str) -> list[str]:
    cmd = ["git", "grep", "-n", "-w", symbol, "HEAD", "--", ".", *ALWAYS_EXCLUDE_PATHSPECS]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode not in (0, 1):
        return [f"ERROR running git grep: {result.stderr.strip()}"]
    return [line for line in result.stdout.splitlines() if line]


def parse_hit(line: str) -> tuple[str, str, str] | None:
    # "HEAD:path/to/file:123:content..." — path never contains ':' in this repo.
    m = re.match(r"^HEAD:([^:]+):(\d+):(.*)$", line)
    if m is None:
        return None
    return m.group(1), m.group(2), m.group(3)


def classify_hit(symbol: str, hit_path: str, content: str, own_path_posix: str) -> str:
    if re.search(DEF_RE_TEMPLATE.format(sym=re.escape(symbol)), content):
        return "DEF"
    if re.search(CALL_RE_TEMPLATE.format(sym=re.escape(symbol)), content):
        return "CALL"
    return "TEXT"


def search_symbol(symbol: str, own_path: Path) -> None:
    own_posix = own_path.as_posix()
    raw_hits = git_grep_word(symbol)
    rows = []
    for line in raw_hits:
        parsed = parse_hit(line)
        if parsed is None:
            print(f"  UNPARSED  {line}")
            continue
        hit_path, lineno, content = parsed
        kind = classify_hit(symbol, hit_path, content, own_posix)
        location = "SAME_FILE" if hit_path == own_posix else "OTHER_FILE"
        category = "TEST_TASK_ARCH" if hit_path.startswith(NON_PRODUCTION_PREFIXES) else "PRODUCTION"
        rows.append({
            "path": hit_path, "line": lineno, "content": content.strip(),
            "kind": kind, "location": location, "category": category,
        })

    def_sites = sorted({r["path"] for r in rows if r["kind"] == "DEF"})

    print(f"SYMBOL: {symbol}")
    print(f"  TOTAL_RAW_HITS: {len(rows)}")
    if len(def_sites) > 1:
        print(f"  WARNING: name defined in {len(def_sites)} different files — hits below may belong to a different symbol of the same name:")
        for d in def_sites:
            print(f"    DEF SITE: {d}")
    for r in rows:
        print(f"    {r['kind']:<4} {r['location']:<10} {r['category']:<14} {r['path']}:{r['line']}: {r['content']}")
    print("  NOTE: raw text-match evidence only — no reachability/ownership verdict is computed. "
          "Read each flagged line yourself, especially DEF hits (possible duplicate name) "
          "and CALL hits in files other than the one you're analyzing.")
    print()


def run(path_str: str, only_symbol: str | None) -> None:
    path = Path(path_str)
    if not path.exists():
        print(f"STATUS: FAIL\nREASON: file not found: {path_str}")
        sys.exit(1)

    print(f"FILE: {path.as_posix()}")
    print(f"LAYER: {layer_of(path)}")

    if not is_tracked(path):
        print("WARNING: file is not tracked by git — reference search (git grep) always targets HEAD, "
              "so an untracked file's own content cannot be cross-checked against committed references.")
    elif working_tree_differs_from_head(path):
        print("WARNING: working tree differs from HEAD for this file — symbols/imports below are read from "
              "the WORKING TREE, but reference search always targets HEAD. Commit or stash for a consistent view.")

    if path.suffix != ".py":
        print("NOTE: non-Python file — no import/top-level-symbol analysis (no parser for this language). "
              "Not a claim that the file has no structure, just that this tool doesn't read it.")
        if only_symbol is None:
            print("Pass --symbol NAME to at least get raw text occurrences of a name across the repo.")
            return
        print()
        search_symbol(only_symbol, path)
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
        search_symbol(s, path)


if __name__ == "__main__":
    _use_utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--symbol")
    args = parser.parse_args()
    run(args.path, args.symbol)

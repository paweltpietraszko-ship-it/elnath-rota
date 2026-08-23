"""ROTA-T023b round-6 audit: explicit Site regime at production call sites."""
from __future__ import annotations

import ast
from pathlib import Path


def test_r6_every_production_site_constructor_supplies_explicit_regime() -> None:
    """R5-3 invariant: no production path may infer ORDINARY by omission."""
    missing: list[str] = []
    for path in Path("rota").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "Site":
                continue
            has_keyword = any(keyword.arg == "planning_regime" for keyword in node.keywords)
            if len(node.args) < 5 and not has_keyword:
                missing.append(f"{path.as_posix()}:{node.lineno}")
    assert missing == []

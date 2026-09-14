"""Independent mechanical equivalence checks for ROTA-FILES-REFACTOR-L1."""
from __future__ import annotations

import ast
import copy
import subprocess
from pathlib import Path

import rota.planning.validator as validator
import rota.planning.validator_shared as shared


BASE_SHA = "bad290f3b6953673266c80206765b45d5f0a2e74"
SPLIT_FILES = (
    "rota/planning/validator.py",
    "rota/planning/validator_shared.py",
    "rota/planning/validator_checks_integrity.py",
    "rota/planning/validator_checks_availability.py",
    "rota/planning/validator_checks_patterns.py",
    "rota/planning/validator_checks_rest_and_load.py",
)


def _symbols(source: str) -> dict[str, ast.AST]:
    tree = ast.parse(source)
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


def _normalized(node: ast.AST) -> str:
    """Ignore the two verified type/import-placement-only extraction edits."""
    node = copy.deepcopy(node)
    if isinstance(node, ast.FunctionDef) and node.name == "_demand_kind":
        node.returns = None
    if isinstance(node, ast.FunctionDef) and node.name == "_not_cancelled":
        node.body = [statement for statement in node.body if not isinstance(statement, ast.ImportFrom)]
    return ast.dump(node, include_attributes=False)


def test_every_original_symbol_has_an_ast_identical_single_definition():
    original = subprocess.run(
        ["git", "show", f"{BASE_SHA}:rota/planning/validator.py"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    expected = _symbols(original)

    observed: dict[str, ast.AST] = {}
    for filename in SPLIT_FILES:
        for name, node in _symbols(Path(filename).read_text(encoding="utf-8")).items():
            assert name not in observed, f"duplicate top-level definition after split: {name}"
            observed[name] = node

    assert set(observed) == set(expected)
    exact_mismatches = [
        name
        for name in sorted(expected)
        if ast.dump(observed[name], include_attributes=False)
        != ast.dump(expected[name], include_attributes=False)
    ]
    assert exact_mismatches == ["_demand_kind", "_not_cancelled"]
    semantic_mismatches = [
        name for name in sorted(expected) if _normalized(observed[name]) != _normalized(expected[name])
    ]
    assert not semantic_mismatches, ", ".join(semantic_mismatches)


def test_public_import_path_reexports_the_same_objects():
    assert validator.ViolationDetail is shared.ViolationDetail
    assert validator.IndependentValidationReport is shared.IndependentValidationReport
    assert validator.coverage_segments is shared.coverage_segments
    assert callable(validator.validate)


def test_split_modules_form_the_declared_one_way_import_graph():
    for filename in SPLIT_FILES[1:]:
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"))
        imported = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        assert "rota.planning.validator" not in imported
        assert not any(module.startswith("rota.planning.validator_checks_") for module in imported)


def test_every_split_file_is_below_the_600_line_limit():
    for filename in SPLIT_FILES:
        assert len(Path(filename).read_text(encoding="utf-8").splitlines()) <= 600, filename

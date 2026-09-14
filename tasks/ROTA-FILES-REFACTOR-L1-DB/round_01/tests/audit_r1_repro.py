"""Independent, narrow equivalence check for the db.py mechanical split."""

from __future__ import annotations

import ast
import copy
import sqlite3
import subprocess
import sys
from pathlib import Path


BASE_SHA = "8a9a6dfad1969295fdcaf59e7d9fd5a72fe00d65"
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
DB_PATH = ROOT / "rota" / "persistence" / "db.py"
MOVED_PATHS = (
    ROOT / "rota" / "persistence" / "db_migrations_1_2.py",
    ROOT / "rota" / "persistence" / "db_migrations_3_9.py",
    ROOT / "rota" / "persistence" / "db_migrations_10_17.py",
    ROOT / "rota" / "persistence" / "db_migrations_18_21.py",
)


def _base_source() -> str:
    return subprocess.run(
        ["git", "show", f"{BASE_SHA}:rota/persistence/db.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout


def _symbols(source: str) -> dict[str, ast.AST]:
    result: dict[str, ast.AST] = {}
    for node in ast.parse(source).body:
        names: list[str] = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
        for name in names:
            if name in result:
                raise AssertionError(f"duplicate top-level owner: {name}")
            result[name] = node
    return result


class _WithoutDocstrings(ast.NodeTransformer):
    def _strip(self, node: ast.AST) -> ast.AST:
        body = getattr(node, "body", None)
        if (
            isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            node.body = body[1:]  # type: ignore[attr-defined]
        return self.generic_visit(node)

    visit_FunctionDef = _strip
    visit_AsyncFunctionDef = _strip
    visit_ClassDef = _strip


def _dump(node: ast.AST) -> str:
    executable = _WithoutDocstrings().visit(copy.deepcopy(node))
    return ast.dump(executable, annotate_fields=True, include_attributes=False)


def _schema(conn: sqlite3.Connection) -> list[tuple[str, str, str]]:
    return conn.execute(
        "SELECT type, name, sql FROM sqlite_master "
        "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()


def main() -> None:
    base_source = _base_source()
    base = _symbols(base_source)
    current_db = _symbols(DB_PATH.read_text(encoding="utf-8"))

    combined: dict[str, ast.AST] = dict(current_db)
    for path in MOVED_PATHS:
        for name, node in _symbols(path.read_text(encoding="utf-8")).items():
            if name in combined:
                raise AssertionError(f"duplicate owner after split: {name}")
            combined[name] = node

    moved_names = {f"_MIGRATION_{number}" for number in range(1, 22) if number != 18} | {
        "_FINAL_CHILD_TABLES",
        "_final_guard_triggers",
        "_migration_18_encrypt_existing_persisted_names",
    }
    retained_names = {
        "LATEST_SCHEMA_VERSION",
        "UnsupportedSchemaVersion",
        "MIGRATIONS",
        "connect",
        "migrate",
        "init_schema",
    }
    expected = moved_names | retained_names
    assert expected <= base.keys(), sorted(expected - base.keys())
    assert expected <= combined.keys(), sorted(expected - combined.keys())
    for name in sorted(expected):
        assert _dump(base[name]) == _dump(combined[name]), f"AST changed for {name}"

    # The four extracted modules form leaves; they must not import the old
    # orchestrator or one another and thereby introduce a cycle/second owner.
    for path in MOVED_PATHS:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module != "rota.persistence.db"
                assert not node.module.startswith("rota.persistence.db_migrations_")

    from rota.persistence import db
    from rota.persistence import db_migrations_1_2, db_migrations_3_9
    from rota.persistence import db_migrations_10_17, db_migrations_18_21

    owners = {
        **{number: db_migrations_1_2 for number in range(1, 3)},
        **{number: db_migrations_3_9 for number in range(3, 10)},
        **{number: db_migrations_10_17 for number in range(10, 18)},
        **{number: db_migrations_18_21 for number in range(19, 22)},
    }
    for number, owner in owners.items():
        name = f"_MIGRATION_{number}"
        assert getattr(db, name) is getattr(owner, name), name
    assert db.MIGRATIONS[17][1] is db_migrations_18_21._migration_18_encrypt_existing_persisted_names
    assert [version for version, _ in db.MIGRATIONS] == list(range(1, 22))

    # Execute the old monolith and the split code independently against fresh
    # in-memory stores. The resulting real SQLite schema must be byte-for-byte
    # identical, including tables, indexes and triggers.
    base_namespace: dict[str, object] = {"__name__": "audit_base_db"}
    exec(compile(base_source, "<base-db.py>", "exec"), base_namespace)
    old_conn = sqlite3.connect(":memory:", check_same_thread=False)
    old_conn.execute("PRAGMA foreign_keys = ON")
    base_namespace["migrate"](old_conn)  # type: ignore[operator]
    new_conn = db.connect(":memory:")
    assert old_conn.execute("PRAGMA user_version").fetchone() == (21,)
    assert new_conn.execute("PRAGMA user_version").fetchone() == (21,)
    assert _schema(old_conn) == _schema(new_conn)
    old_conn.close()
    new_conn.close()

    for path in (DB_PATH, *MOVED_PATHS):
        assert len(path.read_text(encoding="utf-8").splitlines()) < 600, path

    print("PASS: AST owners, imports, public attributes, order, fresh schema and size are equivalent")


if __name__ == "__main__":
    main()

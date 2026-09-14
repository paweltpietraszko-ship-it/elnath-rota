"""OWNER 2026-09-14: canonical scope, fail closed, .py/.ts/.tsx file sizes."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

import backend


INVALID_SCOPES = [
    "# Brief\n",
    "TASK_SCOPE:\n",
    "TASK_SCOPE:\n\n",
    "## TASK_SCOPE:\n- source.ts\n",
    " TASK_SCOPE:\n- source.ts\n",
    "TASK_SCOPE: source.ts\n",
    "TASK_SCOPE: ignored\n- source.ts\n",
    "TASK_SCOPE:\n* source.ts\n",
    "TASK_SCOPE:\n1. source.ts\n",
    "TASK_SCOPE:\nsource.ts\n",
    "TASK_SCOPE:\n-\n",
    "TASK_SCOPE:\n- `source.ts`\n",
    "TASK_SCOPE:\n- source.ts\n* other.ts\n",
]


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_canonical_scope(tmp_path, newline):
    brief = tmp_path / "brief.md"
    text = newline.join(["# Brief", "TASK_SCOPE:", "- app.py", "- source.ts", "- view.tsx", ""])
    brief.write_bytes(text.encode("utf-8"))
    assert backend.read_task_scope(brief) == ["app.py", "source.ts", "view.tsx"]


@pytest.mark.parametrize("text", INVALID_SCOPES)
def test_rejects_noncanonical_or_empty_scope(tmp_path, text):
    brief = tmp_path / "brief.md"
    brief.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        backend.read_task_scope(brief)


def test_unreadable_brief(tmp_path):
    with pytest.raises(ValueError):
        backend.read_task_scope(tmp_path / "missing.md")


@pytest.mark.parametrize("entry", ["", "../outside.ts", "/outside.ts"])
def test_existing_path_rejections(entry):
    assert backend.check_scope_paths([entry])


@pytest.mark.parametrize("suffix", [".py", ".ts", ".tsx"])
@pytest.mark.parametrize("lines", [599, 600, 601])
def test_source_file_size_boundary(tmp_path, monkeypatch, suffix, lines):
    monkeypatch.chdir(tmp_path)
    filename = "source" + suffix
    comment = "# line\n" if suffix == ".py" else "// line\n"
    Path(filename).write_text(comment * lines, encoding="utf-8")
    errors = backend.check_sizes([filename])
    if lines <= 600:
        assert errors == []
    else:
        assert errors == [f"SIZE_FILE: {filename} has 601 lines (max 600)"]


@pytest.mark.parametrize("suffix", [".py", ".ts", ".tsx"])
def test_deleted_source_retains_handling(suffix):
    assert backend.check_sizes(["absent-source" + suffix]) == []


@pytest.mark.parametrize("lines", [50, 51])
def test_python_function_limit_unchanged(tmp_path, monkeypatch, lines):
    monkeypatch.chdir(tmp_path)
    Path("source.py").write_text("def sample():\n" + "    pass\n" * (lines - 1), encoding="utf-8")
    errors = backend.check_sizes(["source.py"])
    assert errors == ([] if lines == 50 else ["SIZE_FUNC: source.py:sample has 51 lines (max 50)"])


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def cli_repo(tmp_path):
    git(tmp_path, "init")
    git(tmp_path, "config", "user.name", "Gate Fixture")
    git(tmp_path, "config", "user.email", "gate@example.invalid")
    arch = tmp_path / "arch"
    arch.mkdir()
    spec = b"Frozen fixture specification\n"
    (arch / "spec.md").write_bytes(spec)
    (arch / "FROZEN.lock").write_text("SHA256: " + hashlib.sha256(spec).hexdigest() + "\n")
    git(tmp_path, "add", "arch")
    git(tmp_path, "commit", "-m", "Fixture base")
    return tmp_path, git(tmp_path, "rev-parse", "HEAD")


def run_cli(repo, base, head, text):
    brief = repo / "brief.md"
    brief.write_text(text, encoding="utf-8")
    output = repo / "backend.txt"
    result = subprocess.run(
        [sys.executable, str(Path(backend.__file__).resolve()), str(brief), base, head, str(output)],
        cwd=repo, capture_output=True, text=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert output.exists(), result.stderr
    return result.returncode, output.read_text(encoding="utf-8")


@pytest.mark.parametrize("text", ["# Missing\n", "TASK_SCOPE:\n", "TASK_SCOPE:\n* source.ts\n"])
@pytest.mark.parametrize("changed", [False, True])
def test_cli_invalid_scope_stops_without_diff_scope_noise(cli_repo, text, changed):
    repo, base = cli_repo
    if changed:
        (repo / "source.ts").write_text("export const value = 1;\n", encoding="utf-8")
        git(repo, "add", "source.ts")
        git(repo, "commit", "-m", "Fixture source")
    code, report = run_cli(repo, base, git(repo, "rev-parse", "HEAD"), text)
    assert code == 1
    assert "STATUS: FAIL" in report
    assert "  - TASK_SCOPE:" in report
    assert "  - DIFF_SCOPE:" not in report


@pytest.mark.parametrize("suffix", [".ts", ".tsx"])
@pytest.mark.parametrize("lines", [600, 601])
@pytest.mark.parametrize("change", ["added", "modified"])
def test_cli_typescript_file_size(cli_repo, suffix, lines, change):
    repo, base = cli_repo
    filename = "source" + suffix
    source = repo / filename
    if change == "modified":
        source.write_text("// line\n" * 600, encoding="utf-8")
        git(repo, "add", filename)
        git(repo, "commit", "-m", "Fixture existing source")
        base = git(repo, "rev-parse", "HEAD")
    source.write_text("// changed\n" + "// line\n" * (lines - 1), encoding="utf-8")
    git(repo, "add", filename)
    git(repo, "commit", "-m", "Fixture size change")
    code, report = run_cli(repo, base, git(repo, "rev-parse", "HEAD"), "TASK_SCOPE:\n- " + filename + "\n")
    if lines == 601:
        assert code == 1
        assert "STATUS: FAIL" in report
        assert f"SIZE_FILE: {filename} has 601 lines (max 600)" in report
    else:
        assert code == 0
        assert "STATUS: FAIL" not in report
        assert "  - SIZE_FILE:" not in report

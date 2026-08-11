"""Shared pytest fixtures for Elnath Ward test suite."""
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent


def _run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git"] + args, cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    _run_git(["init"], tmp_path)
    _run_git(["config", "user.email", "test@test.com"], tmp_path)
    _run_git(["config", "user.name", "Test"], tmp_path)
    arch_dir = tmp_path / "arch"
    arch_dir.mkdir()
    spec_src = REPO_ROOT / "arch" / "spec.md"
    (arch_dir / "spec.md").write_bytes(spec_src.read_bytes())
    _run_git(["add", "-A"], tmp_path)
    _run_git(["commit", "-m", "initial"], tmp_path)
    return tmp_path


@pytest.fixture
def frozen_repo(tmp_repo: Path) -> Path:
    subprocess.run(
        ["python", str(REPO_ROOT / "guard.py"), "freeze", "arch/spec.md"],
        cwd=tmp_repo,
        check=True,
        capture_output=True,
    )
    return tmp_repo

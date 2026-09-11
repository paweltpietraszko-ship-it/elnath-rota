"""Shared pytest fixtures for Elnath Ward test suite."""
import itertools
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from rota.application import manual_edit

REPO_ROOT = Path(__file__).parent


@pytest.fixture(autouse=True)
def _frozen_manual_correction_now(monkeypatch):
    """ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT: apply_manual_correction's new
    historical-mutation guard compares each Assignment's start_datetime
    against the real wall clock (manual_edit._now()) -- section 2's single
    boundary. Pre-existing tests unrelated to this feature fix their
    fixture months to a specific calendar date (most commonly 2026-08),
    which has nothing to do with the guard and predates it; without this,
    they would start hitting HistoricalServiceMutationRejected purely
    because real wall-clock time marched past their fixture month, not
    because of anything the guard is meant to catch. Anchoring this one
    narrow seam to a reference point BEFORE every fixture month used
    anywhere in this suite makes every one of those Assignments read as
    "not yet started" (future), exactly their pre-Task classification --
    anchoring it to a future point would do the opposite (make every
    fixture MORE historical, not less).

    Codex audit R3-01: a single static frozen instant returned identically
    on every call let a real two-clock bug elsewhere in manual_edit.py
    (effective_from vs. the action's own recorded_at) go undetected by the
    wider suite, and would just as easily mask a future ordering bug in any
    test that performs multiple sequential corrections and expects their
    timestamps to differ. Each call now advances by one second instead of
    returning a byte-identical value, so ordering/uniqueness assumptions
    are exercised the same way they would be against the real clock.
    tests/test_historical_service_correction.py overrides this fixture
    locally (a nested monkeypatch of the same attribute) to exercise the
    actual now-vs-start_datetime boundary."""
    counter = itertools.count()
    base = datetime(2000, 1, 1)
    monkeypatch.setattr(manual_edit, "_now", lambda: base + timedelta(seconds=next(counter)))


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

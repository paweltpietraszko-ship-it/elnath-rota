"""ROTA-T004 acceptance tests (tasks/ROTA-T004/brief.md)."""
from __future__ import annotations

import sqlite3
from datetime import time
from pathlib import Path

import pytest

from rota.domain import ShiftKind, SiteProfile, StandardShift
from rota.persistence.db import connect, init_schema
from rota.persistence.site_profile_repository import (
    SiteProfileNotFound,
    get_site_profile,
    list_site_profile_ids,
    save_site_profile,
)


def _profile(profile_id: str = "OCHRONA", active: bool = True, threshold: int = 60) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id,
        display_name="Ochrona",
        active=active,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(8, 0), time(20, 0), end_next_day=False, required_primary_count=1),
            StandardShift(ShiftKind.N, time(20, 0), time(8, 0), end_next_day=True, required_primary_count=1),
        ],
        day_only_blocks_n=True,
        external_support_enabled=False,
        training_s_enabled=True,
        training_s_weekdays_only=True,
        training_s_default_readiness_threshold=2,
        rolling_7d_decision_threshold_hours=threshold,
    )


def test_round_trip_after_reconnect(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    original = _profile()
    save_site_profile(conn, original)
    conn.close()

    reopened = connect(db_path)
    reloaded = get_site_profile(reopened, original.profile_id)
    assert reloaded == original


def test_standard_shifts_preserve_order(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    profile = _profile()
    reversed_shifts = list(reversed(profile.standard_shifts))
    profile = SiteProfile(**{**profile.__dict__, "standard_shifts": reversed_shifts})
    save_site_profile(conn, profile)

    reloaded = get_site_profile(conn, profile.profile_id)
    assert reloaded.standard_shifts == reversed_shifts


def test_resave_replaces_current_state_without_version_history(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    original = _profile(threshold=60)
    save_site_profile(conn, original)

    updated = _profile(threshold=65)
    updated = SiteProfile(**{**updated.__dict__, "standard_shifts": updated.standard_shifts[:1]})
    save_site_profile(conn, updated)

    reloaded = get_site_profile(conn, original.profile_id)
    assert reloaded == updated

    row_count = conn.execute(
        "SELECT COUNT(*) FROM site_profiles WHERE profile_id = ?", (original.profile_id,)
    ).fetchone()[0]
    assert row_count == 1

    shift_count = conn.execute(
        "SELECT COUNT(*) FROM standard_shifts WHERE profile_id = ?", (original.profile_id,)
    ).fetchone()[0]
    assert shift_count == 1


def test_active_false_round_trips_normally(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    profile = _profile(active=False)
    save_site_profile(conn, profile)

    reloaded = get_site_profile(conn, profile.profile_id)
    assert reloaded.active is False


def test_missing_profile_raises_not_found(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    with pytest.raises(SiteProfileNotFound):
        get_site_profile(conn, "NO_SUCH_PROFILE")


def test_list_site_profile_ids(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    save_site_profile(conn, _profile("SITE_A"))
    save_site_profile(conn, _profile("SITE_B"))
    assert list_site_profile_ids(conn) == ["SITE_A", "SITE_B"]


class _FlakyConnection(sqlite3.Connection):
    """Raises on its Nth execute() call; sqlite3.Connection can't be
    monkeypatched at the class level (it's an immutable C type), so the
    fault is injected via a connection subclass instead (factory=)."""

    fail_on_call: int = -1
    _call_count: int = 0

    def execute(self, sql, params=()):  # type: ignore[override]
        self._call_count += 1
        if self._call_count == self.fail_on_call:
            raise sqlite3.OperationalError("simulated failure")
        return super().execute(sql, params)


def test_save_rolls_back_atomically_on_mid_transaction_failure(tmp_path: Path) -> None:
    """ACCEPTANCE #5: profile + standard_shifts write is one transaction --
    a failure partway through must leave the PRIOR persisted state intact,
    not a profile row paired with a partially-written shift list."""
    db_path = tmp_path / "rota.db"
    conn = sqlite3.connect(db_path, factory=_FlakyConnection)
    init_schema(conn)
    original = _profile(threshold=60)
    save_site_profile(conn, original)

    updated = _profile(threshold=99)
    conn._call_count = 0
    conn.fail_on_call = 3  # after site_profiles upsert + shifts delete, mid shift insert
    with pytest.raises(sqlite3.OperationalError):
        save_site_profile(conn, updated)
    conn.fail_on_call = -1

    reloaded = get_site_profile(conn, original.profile_id)
    assert reloaded == original


def test_planning_engine_has_no_persistence_coupling() -> None:
    """arch/spec.md:332-333 / ROTA-T004 brief: PlanningEngine does not open,
    know the path of, read, or write the database."""
    planning_dir = Path(__file__).resolve().parent.parent / "rota" / "planning"
    for path in planning_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "rota.persistence" not in source, f"{path} imports persistence"
        assert "import sqlite3" not in source, f"{path} imports sqlite3 directly"

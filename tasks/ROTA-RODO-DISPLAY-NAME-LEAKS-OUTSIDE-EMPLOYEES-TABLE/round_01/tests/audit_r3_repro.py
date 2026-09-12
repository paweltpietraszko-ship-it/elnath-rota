from __future__ import annotations

import sqlite3
from datetime import date, datetime

import pytest

from rota.application import plan_ops
from rota.domain import (
    AvailabilityKind,
    AvailabilityRecord,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    SiteMembership,
)
from rota.persistence import db as rota_db
from rota.persistence import pii_crypto, plan_preview_repository, site_memory
from rota.persistence.db import connect
from rota.planning.engine import plan
from tests.support.minimal_state import MONTH, SITE_ID, base_state


def _seed_persistence_context(conn) -> None:
    conn.execute(
        "INSERT INTO site_profiles "
        "(profile_id, display_name, active, day_only_blocks_n, external_support_enabled, "
        "training_s_enabled, training_s_weekdays_only, training_s_default_readiness_threshold, "
        "rolling_7d_decision_threshold_hours) "
        "VALUES ('TESTPROF', 'Profil', 1, 0, 0, 0, 0, 1, 999)"
    )
    conn.execute(
        "INSERT INTO sites (site_id, profile_id, display_name, active) "
        "VALUES (?, 'TESTPROF', 'Obiekt', 1)",
        (SITE_ID,),
    )
    conn.execute(
        "INSERT INTO coordinators (coordinator_id, display_name, active) "
        "VALUES ('C1', 'Koordynator', 1)"
    )
    conn.commit()


def test_real_plan_warning_is_encrypted_then_survives_reload(tmp_path) -> None:
    employee = Employee("EMP-1", "Anna Kowalska", date(2020, 1, 1), None, False)
    membership = SiteMembership(
        employee.employee_id,
        SITE_ID,
        MembershipKind.LOCAL,
        True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
    )
    demand = ShiftDemand(
        "N1", "test-v1", datetime(2026, 10, 6, 17), datetime(2026, 10, 7, 5), 1
    )
    day_off = AvailabilityRecord(
        "A1",
        "AV1",
        employee.employee_id,
        AvailabilityKind.DAY_SHIFT_OFF,
        date(2026, 10, 7),
        date(2026, 10, 7),
        True,
        None,
        None,
    )
    result = plan(
        base_state(
            employees=(employee,),
            memberships=(membership,),
            shift_demands=(demand,),
            availability_records=(day_off,),
            month=MONTH,
        )
    )
    assert result.status == "FEASIBLE"
    warning = next(item for item in result.warnings if "DAY_SHIFT_OFF-01 SOFT" in item)
    assert "Anna Kowalska" in warning

    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed_persistence_context(conn)
    plan_ops._persist_plan_preview(
        conn,
        site_id=SITE_ID,
        month=MONTH,
        schedule_version_id=None,
        result=result,
        operation_kind="plan",
        effective_from=MONTH,
        shift_demands=[demand],
    )
    raw = conn.execute(
        "SELECT warnings_json FROM plan_previews WHERE site_id = ? AND month = ?",
        (SITE_ID, MONTH.isoformat()),
    ).fetchone()[0]
    assert isinstance(raw, bytes)
    assert "Anna Kowalska".encode() not in raw
    conn.close()
    assert "Anna Kowalska".encode() not in db_path.read_bytes()

    reopened = connect(db_path)
    restored = plan_preview_repository.get_plan_preview(reopened, SITE_ID, MONTH)
    assert restored is not None
    assert warning in restored.warnings


def test_real_decision_guidance_is_encrypted_then_survives_reload(tmp_path) -> None:
    employee = Employee("EMP-1", "Anna Kowalska", date(2020, 1, 1), None, False)
    membership = SiteMembership(
        employee.employee_id,
        SITE_ID,
        MembershipKind.LOCAL,
        True,
        ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT,
    )
    demand = ShiftDemand(
        "D1", "test-v1", datetime(2026, 10, 6, 5), datetime(2026, 10, 6, 17), 1
    )
    unavailable = AvailabilityRecord(
        "A2",
        "AV2",
        employee.employee_id,
        AvailabilityKind.UNAVAILABLE_24H,
        date(2026, 10, 6),
        date(2026, 10, 6),
        True,
        None,
        None,
    )
    result = plan(
        base_state(
            employees=(employee,),
            memberships=(membership,),
            shift_demands=(demand,),
            availability_records=(unavailable,),
            month=MONTH,
        )
    )
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload is not None
    option_texts = [option.text for option in result.decision_payload.unblocking_options]
    assert any("Anna Kowalska" in text for text in option_texts), option_texts

    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed_persistence_context(conn)
    persisted = plan_ops._persist_decision_readback(
        conn,
        site_id=SITE_ID,
        month=MONTH,
        coordinator_id="C1",
        schedule_version_id=None,
        result=result,
    )
    assert persisted.status == "DECISION_REQUIRED"
    row = conn.execute(
        "SELECT decision_required_id, payload_json FROM decision_required_snapshots"
    ).fetchone()
    assert isinstance(row[1], bytes)
    assert "Anna Kowalska".encode() not in row[1]
    conn.close()
    assert "Anna Kowalska".encode() not in db_path.read_bytes()

    reopened = connect(db_path)
    restored = site_memory.get_current_decision_required(
        reopened, site_id=SITE_ID, month=MONTH
    )
    assert restored is not None
    assert restored.payload == result.decision_payload


def test_migration_failure_rolls_back_data_version_and_append_only_triggers(
    tmp_path, monkeypatch
) -> None:
    db_path = tmp_path / "legacy.db"
    legacy = sqlite3.connect(db_path)
    legacy.execute("BEGIN")
    for version, statements in rota_db.MIGRATIONS:
        if version > 17:
            continue
        assert not callable(statements)
        for statement in statements:
            legacy.execute(statement)
    legacy.execute("PRAGMA user_version = 17")
    legacy.execute("COMMIT")
    _seed_persistence_context(legacy)
    legacy.execute(
        "INSERT INTO plan_previews "
        "(site_id, month, schedule_version_id, candidates_json, warnings_json, "
        "optimization_complete, operation_kind, effective_from, shift_demands_json) "
        "VALUES (?, ?, NULL, '[]', ?, 1, 'plan', NULL, '[]')",
        (SITE_ID, MONTH.isoformat(), '["Anna Kowalska warning"]'),
    )
    legacy.execute(
        "INSERT INTO decision_required_snapshots "
        "(decision_required_id, site_id, month, schedule_version_id, requested_by, "
        "recorded_at, payload_json) VALUES ('DR-1', ?, ?, NULL, 'C1', ?, ?)",
        (
            SITE_ID,
            MONTH.isoformat(),
            datetime(2026, 10, 1, 8).isoformat(),
            '{"blocking_shift_demands": [], "blockers": [], '
            '"unblocking_options": [{"text": "Anna Kowalska", "target": null}], '
            '"load_blocker": null}',
        ),
    )
    legacy.commit()
    legacy.close()

    real_encrypt = pii_crypto.encrypt_text
    calls = 0

    def fail_on_second_field(key: bytes, plaintext: str, aad: bytes) -> bytes:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("forced migration interruption")
        return real_encrypt(key, plaintext, aad)

    monkeypatch.setattr(pii_crypto, "encrypt_text", fail_on_second_field)
    with pytest.raises(RuntimeError, match="forced migration interruption"):
        connect(db_path)

    checked = sqlite3.connect(db_path)
    assert checked.execute("PRAGMA user_version").fetchone()[0] == 17
    assert isinstance(checked.execute("SELECT warnings_json FROM plan_previews").fetchone()[0], str)
    assert isinstance(
        checked.execute("SELECT payload_json FROM decision_required_snapshots").fetchone()[0], str
    )
    trigger_names = {
        row[0]
        for row in checked.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' "
            "AND name LIKE 'decision_required_snapshots_no_%'"
        )
    }
    assert trigger_names == {
        "decision_required_snapshots_no_update",
        "decision_required_snapshots_no_delete",
    }


def test_successful_migration_removes_legacy_name_bytes_from_sqlite_file(tmp_path) -> None:
    db_path = tmp_path / "legacy-file.db"
    legacy = sqlite3.connect(db_path)
    legacy.execute("BEGIN")
    for version, statements in rota_db.MIGRATIONS:
        if version > 17:
            continue
        assert not callable(statements)
        for statement in statements:
            legacy.execute(statement)
    legacy.execute("PRAGMA user_version = 17")
    legacy.execute("COMMIT")
    _seed_persistence_context(legacy)
    unique_name = "UNIQUE-PLAINTEXT-NAME-RODO-1234567890"
    legacy.execute(
        "INSERT INTO plan_previews "
        "(site_id, month, schedule_version_id, candidates_json, warnings_json, "
        "optimization_complete, operation_kind, effective_from, shift_demands_json) "
        "VALUES (?, ?, NULL, '[]', ?, 1, 'plan', NULL, '[]')",
        (SITE_ID, MONTH.isoformat(), f'["{unique_name}"]'),
    )
    legacy.commit()
    legacy.close()
    assert unique_name.encode() in db_path.read_bytes()

    migrated = connect(db_path)
    migrated.close()

    assert unique_name.encode() not in db_path.read_bytes()


def test_preview_ciphertext_swap_between_months_of_same_site_fails_closed(tmp_path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_persistence_context(conn)
    october = MONTH
    november = date(2026, 11, 1)
    for month, warning in ((october, "October warning"), (november, "November warning")):
        plan_preview_repository.save_plan_preview(
            conn,
            plan_preview_repository.PlanPreview(
                site_id=SITE_ID,
                month=month,
                schedule_version_id=None,
                candidates=[],
                warnings=[warning],
                optimization_complete=True,
                operation_kind="plan",
            ),
        )

    october_blob = conn.execute(
        "SELECT warnings_json FROM plan_previews WHERE site_id = ? AND month = ?",
        (SITE_ID, october.isoformat()),
    ).fetchone()[0]
    conn.execute(
        "UPDATE plan_previews SET warnings_json = ? WHERE site_id = ? AND month = ?",
        (october_blob, SITE_ID, november.isoformat()),
    )
    conn.commit()

    with pytest.raises(ValueError, match="integrity"):
        plan_preview_repository.get_plan_preview(conn, SITE_ID, november)
    assert plan_preview_repository.get_plan_preview(conn, SITE_ID, october).warnings == [
        "October warning"
    ]

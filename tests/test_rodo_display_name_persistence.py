"""ROTA-RODO-DISPLAY-NAME-LEAKS-OUTSIDE-EMPLOYEES-TABLE (brief.md exact SHA
5683bac): plan_previews.warnings_json and decision_required_snapshots.
payload_json are encrypted at rest with the same DEK/runtime-protector
contract as Employee.display_name, record-bound AAD (site_id+month /
decision_required_id), and covered by the existing backup/recovery
primitive -- no second key, no new backup format, no solver/guidance
content change.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

import pytest

from rota.application.backup import (
    backup_database,
    create_local_recovery_kit,
    recover_plan_preview_and_decision_snapshot_from_backup,
)
from rota.persistence import db as rota_db
from rota.persistence import pii_crypto
from rota.persistence import plan_preview_repository as ppr
from rota.persistence import site_memory as sm
from rota.persistence.db import connect
from rota.planning.engine_types import DecisionRequiredPayload, UnblockingOption

MONTH = date(2026, 9, 1)


def _seed_base_entities(conn) -> None:
    conn.execute(
        "INSERT INTO site_profiles (profile_id, display_name, active, day_only_blocks_n, external_support_enabled, "
        "training_s_enabled, training_s_weekdays_only, training_s_default_readiness_threshold, "
        "rolling_7d_decision_threshold_hours) VALUES ('P1','Profile',1,0,0,0,0,1,999)"
    )
    conn.execute("INSERT INTO sites (site_id, profile_id, display_name, active) VALUES ('S1','P1','Site 1',1)")
    conn.execute("INSERT INTO sites (site_id, profile_id, display_name, active) VALUES ('S2','P1','Site 2',1)")
    conn.execute("INSERT INTO coordinators (coordinator_id, display_name, active) VALUES ('C1','Coord 1',1)")


def _decision_payload(text: str) -> DecisionRequiredPayload:
    return DecisionRequiredPayload(
        blocking_shift_demands=(), blockers=(), unblocking_options=(UnblockingOption(text),), load_blocker=None,
    )


class TestPlanPreviewWarnings:
    def test_new_warnings_are_ciphertext_at_rest_and_roundtrip(self, tmp_path) -> None:
        conn = connect(tmp_path / "rota.db")
        _seed_base_entities(conn)
        preview = ppr.PlanPreview(
            site_id="S1", month=MONTH, schedule_version_id=None,
            candidates=[], warnings=["DAY_SHIFT_OFF-01 SOFT: Jan Kowalski ma dzien wolny"],
            optimization_complete=True, operation_kind="plan",
        )
        ppr.save_plan_preview(conn, preview)

        raw = conn.execute("SELECT warnings_json FROM plan_previews WHERE site_id = ?", ("S1",)).fetchone()[0]
        assert isinstance(raw, bytes)
        assert b"Kowalski" not in raw

        loaded = ppr.get_plan_preview(conn, "S1", MONTH)
        assert loaded.warnings == ["DAY_SHIFT_OFF-01 SOFT: Jan Kowalski ma dzien wolny"]

    def test_tampering_is_rejected_not_partially_decoded(self, tmp_path) -> None:
        conn = connect(tmp_path / "rota.db")
        _seed_base_entities(conn)
        ppr.save_plan_preview(conn, ppr.PlanPreview(
            site_id="S1", month=MONTH, schedule_version_id=None,
            candidates=[], warnings=["some warning"], optimization_complete=True, operation_kind="plan",
        ))
        raw = conn.execute("SELECT warnings_json FROM plan_previews WHERE site_id = ?", ("S1",)).fetchone()[0]
        tampered = b"X" + raw[1:]
        conn.execute("UPDATE plan_previews SET warnings_json = ? WHERE site_id = ?", (tampered, "S1"))
        conn.commit()
        with pytest.raises(ValueError, match="integrity|header|version"):
            ppr.get_plan_preview(conn, "S1", MONTH)

    def test_ciphertext_swap_between_two_previews_is_rejected(self, tmp_path) -> None:
        """L4a: a full, validly-decryptable warnings_json ciphertext copied
        from one (site_id, month) preview into another of the same class
        must fail closed -- the AAD is bound to site_id+month, so the tag
        was computed over the WRONG record's identity."""
        conn = connect(tmp_path / "rota.db")
        _seed_base_entities(conn)
        ppr.save_plan_preview(conn, ppr.PlanPreview(
            site_id="S1", month=MONTH, schedule_version_id=None,
            candidates=[], warnings=["warning for S1"], optimization_complete=True, operation_kind="plan",
        ))
        ppr.save_plan_preview(conn, ppr.PlanPreview(
            site_id="S2", month=MONTH, schedule_version_id=None,
            candidates=[], warnings=["warning for S2"], optimization_complete=True, operation_kind="plan",
        ))
        raw_s1 = conn.execute("SELECT warnings_json FROM plan_previews WHERE site_id = ?", ("S1",)).fetchone()[0]

        conn.execute("UPDATE plan_previews SET warnings_json = ? WHERE site_id = ?", (raw_s1, "S2"))
        conn.commit()

        with pytest.raises(ValueError, match="integrity"):
            ppr.get_plan_preview(conn, "S2", MONTH)
        # the swap did not touch S1's own, still-correct record
        assert ppr.get_plan_preview(conn, "S1", MONTH).warnings == ["warning for S1"]


class TestDecisionRequiredPayload:
    def test_new_payload_is_ciphertext_at_rest_and_roundtrips(self, tmp_path) -> None:
        conn = connect(tmp_path / "rota.db")
        _seed_base_entities(conn)
        with conn:
            snap = sm.insert_decision_required_snapshot_no_commit(
                conn, site_id="S1", month=MONTH, schedule_version_id=None, requested_by="C1",
                recorded_at=datetime(2026, 9, 1, 8), payload=_decision_payload("Sprawdz obsade: Jan Kowalski"),
            )
        raw = conn.execute(
            "SELECT payload_json FROM decision_required_snapshots WHERE decision_required_id = ?",
            (snap.decision_required_id,),
        ).fetchone()[0]
        assert isinstance(raw, bytes)
        assert b"Kowalski" not in raw

        loaded = sm.get_decision_required_snapshot(conn, snap.decision_required_id)
        assert loaded.payload.unblocking_options[0].text == "Sprawdz obsade: Jan Kowalski"

    def test_ciphertext_swap_between_two_snapshots_is_rejected(self, tmp_path) -> None:
        """L4b: a full, validly-decryptable payload_json ciphertext copied
        from one decision_required_id into another must fail closed."""
        conn = connect(tmp_path / "rota.db")
        _seed_base_entities(conn)
        with conn:
            snap_a = sm.insert_decision_required_snapshot_no_commit(
                conn, site_id="S1", month=MONTH, schedule_version_id=None, requested_by="C1",
                recorded_at=datetime(2026, 9, 1, 8), payload=_decision_payload("payload A"),
            )
        with conn:
            snap_b = sm.insert_decision_required_snapshot_no_commit(
                conn, site_id="S1", month=MONTH, schedule_version_id=None, requested_by="C1",
                recorded_at=datetime(2026, 9, 1, 9), payload=_decision_payload("payload B"),
            )
        raw_a = conn.execute(
            "SELECT payload_json FROM decision_required_snapshots WHERE decision_required_id = ?",
            (snap_a.decision_required_id,),
        ).fetchone()[0]

        # Bypass the append-only trigger the same way the db.py migration
        # does, deliberately, to prove the crypto layer -- not the
        # trigger -- is what would reject a swapped ciphertext.
        conn.execute("DROP TRIGGER decision_required_snapshots_no_update")
        conn.execute(
            "UPDATE decision_required_snapshots SET payload_json = ? WHERE decision_required_id = ?",
            (raw_a, snap_b.decision_required_id),
        )
        conn.commit()

        with pytest.raises(ValueError, match="integrity"):
            sm.get_decision_required_snapshot(conn, snap_b.decision_required_id)
        assert sm.get_decision_required_snapshot(conn, snap_a.decision_required_id).payload.unblocking_options[0].text == "payload A"

    def test_append_only_triggers_still_enforced_for_ordinary_runtime(self, tmp_path) -> None:
        conn = connect(tmp_path / "rota.db")
        _seed_base_entities(conn)
        with conn:
            snap = sm.insert_decision_required_snapshot_no_commit(
                conn, site_id="S1", month=MONTH, schedule_version_id=None, requested_by="C1",
                recorded_at=datetime(2026, 9, 1, 8), payload=_decision_payload("payload"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE decision_required_snapshots SET requested_by = 'HACK' WHERE decision_required_id = ?",
                (snap.decision_required_id,),
            )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "DELETE FROM decision_required_snapshots WHERE decision_required_id = ?",
                (snap.decision_required_id,),
            )


def _build_legacy_db_at_version_17(db_path) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("BEGIN")
    for version, statements in rota_db.MIGRATIONS:
        if version > 17:
            continue
        for statement in statements:
            conn.execute(statement)
    conn.execute("PRAGMA user_version = 17")
    conn.execute("COMMIT")
    conn.execute(
        "INSERT INTO site_profiles (profile_id, display_name, active, day_only_blocks_n, external_support_enabled, "
        "training_s_enabled, training_s_weekdays_only, training_s_default_readiness_threshold, "
        "rolling_7d_decision_threshold_hours) VALUES ('P1','Profile',1,0,0,0,0,1,999)"
    )
    conn.execute("INSERT INTO sites (site_id, profile_id, display_name, active) VALUES ('S1','P1','Site 1',1)")
    conn.execute("INSERT INTO coordinators (coordinator_id, display_name, active) VALUES ('C1','Coord 1',1)")
    conn.execute(
        "INSERT INTO schedule_versions (version_id, site_id, month, status, created_at, created_by, parent_version_id) "
        "VALUES ('SV1','S1','2026-09-01','WORKING','2026-09-01T08:00:00','C1',NULL)"
    )
    conn.execute(
        "INSERT INTO plan_previews (site_id, month, schedule_version_id, candidates_json, warnings_json, "
        "optimization_complete, operation_kind, effective_from, shift_demands_json) "
        "VALUES ('S1','2026-09-01','SV1','[]', ?, 1, 'plan', NULL, '[]')",
        ('["DAY_SHIFT_OFF-01 SOFT: legacy Jan Kowalski"]',),
    )
    conn.execute(
        "INSERT INTO decision_required_snapshots "
        "(decision_required_id, site_id, month, schedule_version_id, requested_by, recorded_at, payload_json) "
        "VALUES ('DR-LEGACY','S1','2026-09-01',NULL,'C1','2026-09-01T08:00:00', ?)",
        ('{"blocking_shift_demands": [], "blockers": [], "unblocking_options": '
         '[{"target": null, "text": "legacy Jan Kowalski"}], "load_blocker": null}',),
    )
    conn.commit()
    conn.close()


def test_migration_encrypts_existing_plaintext_records_and_preserves_reads(tmp_path) -> None:
    """L5/L6: an existing database with genuinely plaintext warnings_json
    and payload_json (predating this feature) has both fields encrypted
    in place on first connect() at the new schema version, decrypts back
    to the exact same content, and decision_required_snapshots' append-
    only triggers survive the migration unweakened."""
    db_path = tmp_path / "legacy.db"
    _build_legacy_db_at_version_17(db_path)

    conn = connect(db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == rota_db.LATEST_SCHEMA_VERSION

    raw_warnings = conn.execute("SELECT warnings_json FROM plan_previews WHERE site_id = 'S1'").fetchone()[0]
    raw_payload = conn.execute(
        "SELECT payload_json FROM decision_required_snapshots WHERE decision_required_id = 'DR-LEGACY'"
    ).fetchone()[0]
    assert isinstance(raw_warnings, bytes) and b"Kowalski" not in raw_warnings
    assert isinstance(raw_payload, bytes) and b"Kowalski" not in raw_payload

    preview = ppr.get_plan_preview(conn, "S1", date(2026, 9, 1))
    assert preview.warnings == ["DAY_SHIFT_OFF-01 SOFT: legacy Jan Kowalski"]
    snapshot = sm.get_decision_required_snapshot(conn, "DR-LEGACY")
    assert snapshot.payload.unblocking_options[0].text == "legacy Jan Kowalski"

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE decision_required_snapshots SET requested_by = 'HACK' WHERE decision_required_id = 'DR-LEGACY'")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM decision_required_snapshots WHERE decision_required_id = 'DR-LEGACY'")


def test_migration_is_idempotent_on_reconnect(tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    _build_legacy_db_at_version_17(db_path)
    connect(db_path).close()
    # second connect: migration 18 is already applied (user_version == 18),
    # so it must not run again / must not double-encrypt already-encrypted values
    conn2 = connect(db_path)
    preview = ppr.get_plan_preview(conn2, "S1", date(2026, 9, 1))
    assert preview.warnings == ["DAY_SHIFT_OFF-01 SOFT: legacy Jan Kowalski"]


@pytest.fixture
def local_windows_only():
    if not pii_crypto._is_windows():
        pytest.skip("LOCAL_WINDOWS deployment model is Windows-only")


def test_recovery_from_backup_also_decrypts_warnings_and_decision_payload(tmp_path, local_windows_only) -> None:
    """L7: the SAME recovered DEK (no second secret, no new backup
    format) decrypts plan_previews.warnings_json and
    decision_required_snapshots.payload_json after losing the original
    installation, exactly as it already does for Employee.display_name."""
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed_base_entities(conn)
    ppr.save_plan_preview(conn, ppr.PlanPreview(
        site_id="S1", month=MONTH, schedule_version_id=None,
        candidates=[], warnings=["Jan Kowalski warning"], optimization_complete=True, operation_kind="plan",
    ))
    with conn:
        snap = sm.insert_decision_required_snapshot_no_commit(
            conn, site_id="S1", month=MONTH, schedule_version_id=None, requested_by="C1",
            recorded_at=datetime(2026, 9, 1, 8), payload=_decision_payload("Jan Kowalski decision text"),
        )
    recovery_key = create_local_recovery_kit(conn, db_path=str(db_path))
    backup_zip = tmp_path / "backup.zip"
    backup_database(conn, str(backup_zip), db_path=str(db_path))
    conn.close()

    warnings, payload_text = recover_plan_preview_and_decision_snapshot_from_backup(
        str(backup_zip), site_id="S1", month=MONTH,
        decision_required_id=snap.decision_required_id, recovery_key=recovery_key,
    )
    assert warnings == ["Jan Kowalski warning"]
    assert payload_text == "Jan Kowalski decision text"

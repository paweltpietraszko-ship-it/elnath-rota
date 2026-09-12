from __future__ import annotations

import os
import zipfile
from datetime import date

import pytest

from rota.application.backup import (
    backup_database,
    create_local_recovery_kit,
    recover_employee_names_from_backup,
)
from rota.domain import Employee
from rota.persistence import pii_crypto
from rota.persistence.db import connect
from rota.persistence.employee_repository import get_employee, save_employee


def test_new_name_is_ciphertext_at_rest_and_roundtrips(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    save_employee(conn, Employee("E1", "Jan Kowalski", date(2020, 1, 1), None, False))

    stored = conn.execute(
        "SELECT display_name FROM employees WHERE employee_id = ?", ("E1",),
    ).fetchone()[0]
    assert isinstance(stored, bytes)
    assert b"Jan Kowalski" not in stored
    assert get_employee(conn, "E1").display_name == "Jan Kowalski"


def test_legacy_plaintext_name_remains_readable(tmp_path) -> None:
    conn = connect(tmp_path / "legacy.db")
    conn.execute(
        "INSERT INTO employees (employee_id, display_name, active_from, active_to, day_only) "
        "VALUES (?, ?, ?, ?, ?)",
        ("LEGACY", "Anna Legacy", "2020-01-01", None, 0),
    )
    conn.commit()
    assert get_employee(conn, "LEGACY").display_name == "Anna Legacy"


def test_dpapi_keystore_roundtrip_on_windows() -> None:
    if not pii_crypto._is_windows():
        pytest.skip("DPAPI is Windows-only")
    key = bytes(range(pii_crypto.KEY_SIZE))
    protected = pii_crypto._dpapi_protect(key)
    assert protected != key
    assert pii_crypto._dpapi_unprotect(protected) == key


def test_tampering_with_header_is_rejected_not_downgraded_to_plaintext(tmp_path) -> None:
    """brief.md E9: changing/removing the version marker must fail closed
    with a controlled integrity error, never be silently treated as
    legacy plaintext (the exact gap R2 audit found in the first pass)."""
    conn = connect(tmp_path / "tamper.db")
    save_employee(conn, Employee("E1", "Tamper Target", date(2020, 1, 1), None, False))
    stored = conn.execute(
        "SELECT display_name FROM employees WHERE employee_id = ?", ("E1",),
    ).fetchone()[0]
    assert isinstance(stored, bytes) and stored.startswith(pii_crypto.MAGIC)

    conn.execute(
        "UPDATE employees SET display_name = ? WHERE employee_id = ?",
        (b"X" + stored[1:], "E1"),
    )
    conn.commit()
    with pytest.raises(ValueError, match="unrecognized header|not valid ciphertext"):
        get_employee(conn, "E1")


def test_truncated_ciphertext_is_rejected(tmp_path) -> None:
    conn = connect(tmp_path / "short.db")
    key = pii_crypto.resolve_key(conn)
    with pytest.raises(ValueError, match="too short"):
        pii_crypto.decrypt_name(key, b"RNAM\x02")


def test_wrong_format_version_is_rejected(tmp_path) -> None:
    conn = connect(tmp_path / "version.db")
    key = pii_crypto.resolve_key(conn)
    forged = b"RNAM\xff" + os.urandom(12) + os.urandom(16)
    with pytest.raises(ValueError, match="unsupported.*version"):
        pii_crypto.decrypt_name(key, forged)


def test_storage_class_change_cannot_downgrade_ciphertext_to_legacy_plaintext(tmp_path) -> None:
    """R5-01 (Codex round-5 audit): SQLite storage class alone (BLOB vs
    TEXT) cannot prove a value is genuine legacy plaintext -- a single
    UPDATE can put an ordinary `str` where ciphertext used to be. The
    persisted protected-ids registry (pii_crypto.mark_encrypted) is the
    tamper-evident record: once an employee_id has ever been encrypted, a
    later `str` for it is a downgrade, never legacy, no matter what the
    column's storage class says."""
    conn = connect(tmp_path / "downgrade.db")
    save_employee(conn, Employee("E1", "Jan Kowalski", date(2020, 1, 1), None, False))

    conn.execute(
        "UPDATE employees SET display_name = ? WHERE employee_id = ?",
        ("Injected Plaintext", "E1"),
    )
    conn.commit()

    with pytest.raises(ValueError, match="downgraded"):
        get_employee(conn, "E1")


def test_protected_ids_registry_has_no_deletable_sidecar_of_its_own(tmp_path) -> None:
    """R6 (Codex round-6 audit): a first version of the R5-01 fix kept the
    protected-ids registry in its own plain `<db>.pii_protected_ids`
    sidecar -- deleting only that one file, leaving the keystore (and the
    DEK it protects) untouched, silently reset the registry to "nothing
    is protected" and reopened the exact storage-class downgrade bypass.
    The registry now lives INSIDE the same DPAPI/AES-GCM-wrapped keystore
    blob as the DEK, so there is no separate file left to delete."""
    db_path = tmp_path / "no-sidecar.db"
    conn = connect(db_path)
    save_employee(conn, Employee("E1", "Jan Kowalski", date(2020, 1, 1), None, False))

    assert not (tmp_path / "no-sidecar.db.pii_protected_ids").exists()
    assert pii_crypto._keystore_path(db_path).exists()

    conn.execute(
        "UPDATE employees SET display_name = ? WHERE employee_id = ?",
        ("Injected Plaintext", "E1"),
    )
    conn.commit()
    with pytest.raises(ValueError, match="downgraded"):
        get_employee(conn, "E1")


def test_deleting_the_keystore_fails_closed_instead_of_silently_reenabling_downgrade(tmp_path) -> None:
    """The only way left to erase "this employee_id was ever encrypted"
    is to delete/corrupt the keystore itself -- which also destroys the
    DEK, so every real ciphertext row (not just the one an attacker might
    target) fails with a loud, already-expected integrity error instead
    of silently trusting a downgraded value."""
    db_path = tmp_path / "keystore-loss.db"
    conn = connect(db_path)
    save_employee(conn, Employee("E1", "Jan Kowalski", date(2020, 1, 1), None, False))
    save_employee(conn, Employee("E2", "Anna Nowak", date(2020, 1, 1), None, False))

    pii_crypto._keystore_path(db_path).unlink()
    pii_crypto._dek_cache_by_path.pop(str(db_path), None)  # force re-reading the (now-missing) keystore

    conn.execute(
        "UPDATE employees SET display_name = ? WHERE employee_id = ?",
        ("Injected Plaintext", "E1"),
    )
    conn.commit()

    # E1 (the tampered one) is a `str`, not marked in the fresh, empty
    # registry a new keystore starts with -- but E2 is still real
    # ciphertext encrypted under the OLD, now-lost DEK, and a brand new
    # DEK cannot decrypt it: the loss is loud and total, not a silent,
    # single-record downgrade.
    with pytest.raises(ValueError, match="integrity"):
        get_employee(conn, "E2")


@pytest.fixture
def local_windows_only():
    if not pii_crypto._is_windows():
        pytest.skip("LOCAL_WINDOWS deployment model is Windows-only")


class TestLocalWindowsDeployment:
    """brief.md section 2.2.A / 5.1: DPAPI runtime protector + an
    independent recovery kit that survives losing this installation."""

    def test_backup_refuses_before_any_recovery_kit_exists(self, tmp_path, local_windows_only) -> None:
        """R5-02 (Codex round-5 audit): a backup ZIP is a single artifact
        that leaves the server the moment it is downloaded -- there is no
        way to retroactively patch an already-downloaded file once a
        recovery kit is created afterward. The only architecturally sound
        fix is to refuse the backup outright until a recovery kit exists,
        never to silently hand over one that looks valid but is not
        recoverable (brief.md section 4's "at least one recoverable
        wrapped DEK representation" is not optional)."""
        db_path = tmp_path / "rota.db"
        conn = connect(db_path)
        save_employee(conn, Employee("E1", "No Kit Yet", date(2020, 1, 1), None, False))
        backup_zip = tmp_path / "backup.zip"

        with pytest.raises(pii_crypto.RecoveryKitRequired):
            backup_database(conn, str(backup_zip), db_path=str(db_path))
        assert not backup_zip.exists()

    def test_backup_after_recovery_kit_created_has_recovery_material(self, tmp_path, local_windows_only) -> None:
        db_path = tmp_path / "rota.db"
        conn = connect(db_path)
        save_employee(conn, Employee("E1", "Has Kit Now", date(2020, 1, 1), None, False))
        create_local_recovery_kit(conn, db_path=str(db_path))
        backup_zip = tmp_path / "backup.zip"
        backup_database(conn, str(backup_zip), db_path=str(db_path))

        with zipfile.ZipFile(backup_zip) as archive:
            manifest = archive.read("manifest.json").decode("utf-8")
            assert '"protector_kind": "DPAPI"' in manifest
            assert '"recovery_available": true' in manifest
            assert "wrapped_dek.bin" in archive.namelist()

    def test_recovery_survives_losing_the_original_installation(self, tmp_path, local_windows_only) -> None:
        original_dir = tmp_path / "original"
        elsewhere_dir = tmp_path / "elsewhere"
        original_dir.mkdir()
        elsewhere_dir.mkdir()
        db_path = original_dir / "rota.db"

        conn = connect(str(db_path))
        save_employee(conn, Employee("E1", "Jan Kowalski", date(2020, 1, 1), None, False))
        save_employee(conn, Employee("E2", "Anna Nowak", date(2020, 1, 1), None, False))
        recovery_key = create_local_recovery_kit(conn, db_path=str(db_path))
        backup_zip = elsewhere_dir / "backup.zip"
        backup_database(conn, str(backup_zip), db_path=str(db_path))
        conn.close()

        # simulate total loss of the original computer/DPAPI context: the
        # recovery must not need anything under original_dir any more.
        import shutil

        shutil.rmtree(original_dir)

        recovered = recover_employee_names_from_backup(str(backup_zip), recovery_key=recovery_key)
        assert recovered == {"E1": "Jan Kowalski", "E2": "Anna Nowak"}

    def test_recovery_rejects_wrong_recovery_key(self, tmp_path, local_windows_only) -> None:
        db_path = tmp_path / "rota.db"
        conn = connect(str(db_path))
        save_employee(conn, Employee("E1", "Jan Kowalski", date(2020, 1, 1), None, False))
        create_local_recovery_kit(conn, db_path=str(db_path))
        backup_zip = tmp_path / "backup.zip"
        backup_database(conn, str(backup_zip), db_path=str(db_path))

        with pytest.raises(pii_crypto.RecoveryFailed):
            recover_employee_names_from_backup(str(backup_zip), recovery_key=b"\x00" * 32)

    def test_recovery_rejects_missing_recovery_key(self, tmp_path, local_windows_only) -> None:
        db_path = tmp_path / "rota.db"
        conn = connect(str(db_path))
        save_employee(conn, Employee("E1", "Jan Kowalski", date(2020, 1, 1), None, False))
        create_local_recovery_kit(conn, db_path=str(db_path))
        backup_zip = tmp_path / "backup.zip"
        backup_database(conn, str(backup_zip), db_path=str(db_path))

        with pytest.raises(pii_crypto.RecoveryFailed):
            recover_employee_names_from_backup(str(backup_zip))


class TestCentralServiceDeployment:
    """brief.md section 2.2.B / 5.2: DEK wrapped by an externally-supplied
    KEK; recovery reuses that same deployment secret, no app-managed
    escrow. ROTA_CENTRAL_KEK is set/cleared per-test, never left behind
    for the rest of the suite."""

    @pytest.fixture(autouse=True)
    def _isolated_env(self, monkeypatch):
        monkeypatch.delenv(pii_crypto.CENTRAL_KEK_ENV_VAR, raising=False)
        yield
        monkeypatch.delenv(pii_crypto.CENTRAL_KEK_ENV_VAR, raising=False)

    def test_backup_and_recovery_roundtrip_with_correct_kek(self, tmp_path, monkeypatch) -> None:
        kek = os.urandom(32).hex()
        monkeypatch.setenv(pii_crypto.CENTRAL_KEK_ENV_VAR, kek)
        db_path = tmp_path / "rota.db"
        conn = connect(str(db_path))
        save_employee(conn, Employee("E1", "Piotr Wisniewski", date(2020, 1, 1), None, False))
        backup_zip = tmp_path / "backup.zip"
        backup_database(conn, str(backup_zip), db_path=str(db_path))
        conn.close()

        with zipfile.ZipFile(backup_zip) as archive:
            manifest = archive.read("manifest.json").decode("utf-8")
            assert '"protector_kind": "CENTRAL"' in manifest
            assert '"recovery_available": true' in manifest

        recovered = recover_employee_names_from_backup(str(backup_zip))
        assert recovered == {"E1": "Piotr Wisniewski"}

    def test_wrong_kek_on_reopen_fails_closed_without_generating_a_new_dek(self, tmp_path, monkeypatch) -> None:
        db_path = tmp_path / "rota.db"
        monkeypatch.setenv(pii_crypto.CENTRAL_KEK_ENV_VAR, os.urandom(32).hex())
        conn = connect(str(db_path))
        save_employee(conn, Employee("E1", "Piotr Wisniewski", date(2020, 1, 1), None, False))
        conn.close()

        # resolve_key's process-lifetime cache is keyed by real path (see
        # pii_crypto's module docstring for why that must be safe, not
        # id(conn)-based) -- it is correctly sticky for the life of ONE
        # process, which a real restart never is. Popping this one test's
        # cache entry is how a single pytest process honestly simulates
        # the fresh-process reopen this test is actually about.
        pii_crypto._dek_cache_by_path.pop(str(db_path), None)
        monkeypatch.setenv(pii_crypto.CENTRAL_KEK_ENV_VAR, os.urandom(32).hex())
        conn2 = connect(str(db_path))
        with pytest.raises(pii_crypto.RecoveryFailed):
            get_employee(conn2, "E1")

    def test_recovery_rejects_wrong_kek(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setenv(pii_crypto.CENTRAL_KEK_ENV_VAR, os.urandom(32).hex())
        db_path = tmp_path / "rota.db"
        conn = connect(str(db_path))
        save_employee(conn, Employee("E1", "Piotr Wisniewski", date(2020, 1, 1), None, False))
        backup_zip = tmp_path / "backup.zip"
        backup_database(conn, str(backup_zip), db_path=str(db_path))
        conn.close()

        monkeypatch.setenv(pii_crypto.CENTRAL_KEK_ENV_VAR, os.urandom(32).hex())
        with pytest.raises(pii_crypto.RecoveryFailed):
            recover_employee_names_from_backup(str(backup_zip))


def test_non_windows_without_central_kek_has_no_automatic_fallback(tmp_path, monkeypatch) -> None:
    """brief.md E4: no silent raw-key-file fallback when neither DPAPI nor
    an explicit CENTRAL_SERVICE KEK is available."""
    monkeypatch.delenv(pii_crypto.CENTRAL_KEK_ENV_VAR, raising=False)
    monkeypatch.setattr(pii_crypto, "_is_windows", lambda: False)
    db_path = tmp_path / "rota.db"
    conn = connect(str(db_path))
    with pytest.raises(pii_crypto.KeyProtectionUnavailable):
        save_employee(conn, Employee("E1", "Should Not Save", date(2020, 1, 1), None, False))
    assert not pii_crypto.recovery_sidecar_path(db_path).exists()
    assert not pii_crypto._keystore_path(db_path).exists()

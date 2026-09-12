from __future__ import annotations

from datetime import date

import pytest

from rota.application.backup import backup_database
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


def test_tampering_with_magic_header_is_rejected(tmp_path) -> None:
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
    with pytest.raises(ValueError, match="integrity"):
        get_employee(conn, "E1")


def test_sqlite_backup_is_a_readable_local_store_without_sidecar_key(tmp_path) -> None:
    source_path = tmp_path / "source.db"
    backup_path = tmp_path / "downloaded-backup.db"
    source = connect(source_path)
    save_employee(source, Employee("E1", "Backup Person", date(2020, 1, 1), None, False))
    backup_database(source, str(backup_path))

    # /workspace/backup downloads only this .db file; it does not deliver the
    # source database's DPAPI-protected .pii_keystore sidecar.
    assert backup_path.exists()
    assert not backup_path.with_name(backup_path.name + pii_crypto.KEYSTORE_SUFFIX).exists()
    reopened = connect(backup_path)
    assert get_employee(reopened, "E1").display_name == "Backup Person"

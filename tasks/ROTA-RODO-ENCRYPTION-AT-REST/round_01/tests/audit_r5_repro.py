from __future__ import annotations

from datetime import date

import pytest

from rota.application.backup import (
    backup_database,
    create_local_recovery_kit,
    recover_employee_names_from_backup,
)
from rota.domain import Employee
from rota.persistence.db import connect
from rota.persistence.employee_repository import get_employee, save_employee


def test_storage_class_change_cannot_downgrade_ciphertext_to_legacy_plaintext(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    save_employee(conn, Employee("E1", "Jan Kowalski", date(2020, 1, 1), None, False))

    stored = conn.execute("SELECT display_name FROM employees WHERE employee_id = 'E1'").fetchone()[0]
    assert isinstance(stored, bytes)

    # Simulate an at-rest tamper/downgrade that changes SQLite storage class,
    # not merely one byte inside the existing BLOB.
    conn.execute("UPDATE employees SET display_name = ? WHERE employee_id = 'E1'", ("Injected Plaintext",))
    conn.commit()

    with pytest.raises(ValueError, match="integrity|legacy|ciphertext"):
        get_employee(conn, "E1")


def test_first_downloaded_backup_remains_recoverable_when_key_is_downloaded_after_it(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    save_employee(conn, Employee("E1", "Anna Nowak", date(2020, 1, 1), None, False))

    # This is the order presented by the production Workspace UI: backup
    # first, recovery-key button second. A fresh installation has no recovery
    # sidecar yet when the first ZIP is created.
    backup_zip = tmp_path / "first-backup.zip"
    backup_database(conn, str(backup_zip), db_path=str(db_path))
    recovery_key = create_local_recovery_kit(conn, db_path=str(db_path))

    assert recover_employee_names_from_backup(
        str(backup_zip), recovery_key=recovery_key
    ) == {"E1": "Anna Nowak"}

from __future__ import annotations

from datetime import date

import pytest

from rota.domain import Employee
from rota.persistence.db import connect
from rota.persistence.employee_repository import get_employee, save_employee


def test_missing_protected_ids_sidecar_cannot_reenable_plaintext_downgrade(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    save_employee(conn, Employee("E1", "Jan Kowalski", date(2020, 1, 1), None, False))

    registry = tmp_path / "rota.db.pii_protected_ids"
    assert registry.exists()
    registry.unlink()

    conn.execute(
        "UPDATE employees SET display_name = ? WHERE employee_id = ?",
        ("Injected Plaintext", "E1"),
    )
    conn.commit()

    with pytest.raises(ValueError, match="integrity|downgraded|legacy|ciphertext"):
        get_employee(conn, "E1")

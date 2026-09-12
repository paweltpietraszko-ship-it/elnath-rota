from __future__ import annotations

from datetime import date

import pytest

from rota.domain import Employee
from rota.persistence import pii_crypto
from rota.persistence.db import connect
from rota.persistence.employee_repository import get_employee, save_employee


def test_keystore_loss_cannot_reenable_downgraded_record_as_legacy_plaintext(tmp_path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    save_employee(conn, Employee("E1", "Jan Kowalski", date(2020, 1, 1), None, False))

    pii_crypto._keystore_path(db_path).unlink()
    pii_crypto._dek_cache_by_path.pop(str(db_path), None)

    conn.execute(
        "UPDATE employees SET display_name = ? WHERE employee_id = ?",
        ("Injected Plaintext", "E1"),
    )
    conn.commit()

    with pytest.raises(ValueError, match="integrity|downgraded|legacy|ciphertext|key"):
        get_employee(conn, "E1")

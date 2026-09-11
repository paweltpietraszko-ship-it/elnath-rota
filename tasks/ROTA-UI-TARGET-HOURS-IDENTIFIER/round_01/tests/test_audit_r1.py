from __future__ import annotations

from datetime import date

from rota.application.assembler import assemble_planning_state
from rota.persistence.db import connect
from tests.support.t009_fixtures import seed_real_object


def test_missing_target_warning_is_plain_polish_without_changing_fallback(tmp_path) -> None:
    month = date(2026, 8, 1)
    conn = connect(tmp_path / "rota.db")
    seeded = seed_real_object(conn, case_id="ui-target-hours-audit", month=month, seed=904)

    state, warnings = assemble_planning_state(conn, site_id=seeded.site.site_id, month=month)
    relevant = [warning for warning in warnings if "użyto awaryjnego, równego podziału godzin" in warning]

    assert state.work_balances == ()
    assert relevant
    assert all("target_hours" not in warning for warning in relevant)
    assert all("Brak wpisanego miesięcznego limitu godzin" in warning for warning in relevant)


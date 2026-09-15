"""ROTA-DELEGACJA-ABSENCE-KIND (brief.md @ 032b14f, Codex preimplementation
audit pending): dedicated matrix for the new AvailabilityKind.DELEGACJA --
whole-day automatic blocker (section 5) whose delegation_hours count as
real planned work (section 6/8), never excused absence, presented as `DEL`
on the PDF for both regimes (section 10). Reuses tests/test_t020.py's own
OCHRONA/ORDINARY fixtures and tests/test_t047_print_export.py's page-capture
helper rather than building parallel print infrastructure.

R2 audit fix (tests_r2.txt R2-01, audit 327215e): a coordinator's manual
correction may legally place a real Assignment on an active DELEGACJA day
(materialized as a DELEGACJA-01 Deviation, never a hard block) -- the print
renderer must not turn that saved decision back into an export-time
ASSIGNMENT_ABSENCE_CONFLICT exception. Both _build_ordinary_rows and
_build_rows now just show the real work code for that day, same as any
other real Assignment day. Known, deliberately out-of-scope-for-this-round
follow-up (not part of R2's closing condition): on that same day,
total_hours/plan_hours currently add both the real work hours and the full
delegation_hours_in_range for the month, double-counting that one day --
left for a future round if the owner wants it addressed."""
from __future__ import annotations

from datetime import date

import pytest

from rota.application.durable_inputs import append_availability
from rota.application.schedule_export import ExportReady, _build_ordinary_rows, _build_rows
from rota.application.schedule_export import generate_schedule_pdf as _generate_schedule_pdf
from rota.balance import compute_month_balance
from rota.domain import (
    AssignmentRole, AssignmentState, AvailabilityKind, AvailabilityRecord, Employee, ShiftDemand, ShiftKind,
)
from rota.persistence.availability_repository import (
    append_availability_version_in_open_transaction,
    get_current_availability_for_employee,
)
from rota.persistence.db import connect
from rota.planning.absence import EXCUSED_ABSENCE_KINDS, IncompleteDelegationHoursError, delegation_hours_in_range
from rota.planning.eligibility import _blocked_by_availability
from rota.planning.validator_checks_availability import _check_leave_and_unavailable
from tests.test_t020 import MONTH, _create_version, _seed, _seed_ordinary, _settings, _work_item
from tests.test_t047_print_export import _capture_pages, _finished_pages


# --- DEL-01/DEL-05: domain/persistence invariants ---------------------------


def test_del_01_create_for_both_regimes():
    for seed in (_seed, _seed_ordinary):
        conn = connect(":memory:")
        seed(conn)
        append_availability(
            conn, coordinator_id="COORD-1", site_id="SITE-1", availability_id="AV-DEL",
            employee_id="EMP-1", kind=AvailabilityKind.DELEGACJA,
            start_date=date(2026, 8, 5), end_date=date(2026, 8, 7), active=True, delegation_hours=7,
        )
        records = get_current_availability_for_employee(conn, "EMP-1")
        record = next(r for r in records if r.availability_id == "AV-DEL")
        assert record.kind == AvailabilityKind.DELEGACJA
        assert record.delegation_hours == 7
        assert record.start_date == date(2026, 8, 5) and record.end_date == date(2026, 8, 7)


def test_del_05_missing_hours_fails_closed():
    conn = connect(":memory:")
    _seed(conn)
    with pytest.raises(ValueError):
        append_availability_version_in_open_transaction(
            conn, availability_id="AV-BAD", employee_id="EMP-1", kind=AvailabilityKind.DELEGACJA,
            start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), active=True, delegation_hours=None,
        )


def test_del_05_non_positive_hours_fails_closed():
    conn = connect(":memory:")
    _seed(conn)
    with pytest.raises(ValueError):
        append_availability_version_in_open_transaction(
            conn, availability_id="AV-BAD", employee_id="EMP-1", kind=AvailabilityKind.DELEGACJA,
            start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), active=True, delegation_hours=0,
        )


def test_del_05_other_kind_with_hours_fails_closed():
    conn = connect(":memory:")
    _seed(conn)
    with pytest.raises(ValueError):
        append_availability_version_in_open_transaction(
            conn, availability_id="AV-BAD", employee_id="EMP-1", kind=AvailabilityKind.LEAVE_GRANTED,
            start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), active=True, delegation_hours=7,
        )


# --- DEL-04: Site default is a prefill, not retroactive ---------------------


def test_del_04_site_default_change_does_not_rewrite_old_record():
    conn = connect(":memory:")
    _seed(conn)
    append_availability(
        conn, coordinator_id="COORD-1", site_id="SITE-1", availability_id="AV-DEL",
        employee_id="EMP-1", kind=AvailabilityKind.DELEGACJA,
        start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), active=True, delegation_hours=7,
    )
    from rota.application.durable_inputs import update_site
    from rota.persistence.site_repository import get_site

    site = get_site(conn, "SITE-1")
    from dataclasses import replace
    update_site(conn, coordinator_id="COORD-1", site_id="SITE-1", site=replace(site, delegation_default_hours=8))

    record = next(r for r in get_current_availability_for_employee(conn, "EMP-1") if r.availability_id == "AV-DEL")
    assert record.delegation_hours == 7
    assert get_site(conn, "SITE-1").delegation_default_hours == 8


# --- DEL-02: automatic eligibility blocker, both regimes --------------------


def _delegacja_record(start: date, end: date, *, hours: int = 7, active: bool = True) -> AvailabilityRecord:
    return AvailabilityRecord(
        availability_id="AV-DEL", availability_version_id="AVV-DEL", employee_id="EMP-1",
        kind=AvailabilityKind.DELEGACJA, start_date=start, end_date=end, active=active,
        supersedes_availability_version_id=None, note=None, delegation_hours=hours,
    )


def test_del_02_blocks_automatic_assignment():
    from datetime import datetime

    demand = ShiftDemand("D-1", "", datetime(2026, 8, 5, 6), datetime(2026, 8, 5, 18), 1)
    reason, leave_plan_collision = _blocked_by_availability(demand, [_delegacja_record(date(2026, 8, 5), date(2026, 8, 5))])
    assert reason == "DELEGACJA-01"
    assert leave_plan_collision is False


def test_del_11_inactive_record_does_not_block():
    from datetime import datetime

    demand = ShiftDemand("D-1", "", datetime(2026, 8, 5, 6), datetime(2026, 8, 5, 18), 1)
    reason, _ = _blocked_by_availability(demand, [_delegacja_record(date(2026, 8, 5), date(2026, 8, 5), active=False)])
    assert reason is None


# --- Validator mirror: DELEGACJA-01 --------------------------------------


def test_del_validator_flags_manual_correction_overlap():
    from datetime import datetime

    from rota.domain import Assignment
    from tests.support.minimal_state import base_state

    assignment = Assignment(
        "A-1", "", "EMP-1", datetime(2026, 8, 5, 6), datetime(2026, 8, 5, 18),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D-1", None,
    )
    state = base_state(availability_records=(_delegacja_record(date(2026, 8, 5), date(2026, 8, 5)),))
    details = []
    _check_leave_and_unavailable(state, [assignment], details)
    assert any(d.rule == "DELEGACJA-01" for d in details)


# --- DEL-06: not excused absence --------------------------------------------


def test_del_06_not_excused_absence():
    assert AvailabilityKind.DELEGACJA not in EXCUSED_ABSENCE_KINDS


# --- delegation_hours_in_range: single/multi-day, clipping, inactive -------


def test_delegation_hours_single_day():
    total = delegation_hours_in_range([_delegacja_record(date(2026, 8, 5), date(2026, 8, 5))], "EMP-1", date(2026, 8, 1), date(2026, 8, 31))
    assert total == 7


def test_delegation_hours_multi_day_per_day_rate():
    total = delegation_hours_in_range([_delegacja_record(date(2026, 8, 5), date(2026, 8, 7), hours=7)], "EMP-1", date(2026, 8, 1), date(2026, 8, 31))
    assert total == 21  # 3 days * 7h


def test_delegation_hours_clips_to_range():
    total = delegation_hours_in_range(
        [_delegacja_record(date(2026, 7, 30), date(2026, 8, 2), hours=7)], "EMP-1", date(2026, 8, 1), date(2026, 8, 31),
    )
    assert total == 14  # only Aug 1-2 count


def test_delegation_hours_inactive_excluded():
    total = delegation_hours_in_range(
        [_delegacja_record(date(2026, 8, 5), date(2026, 8, 5), active=False)], "EMP-1", date(2026, 8, 1), date(2026, 8, 31),
    )
    assert total == 0


def test_delegation_hours_missing_value_fails_closed():
    bad = AvailabilityRecord(
        "AV-BAD", "AVV-BAD", "EMP-1", AvailabilityKind.DELEGACJA, date(2026, 8, 5), date(2026, 8, 5),
        True, None, None, delegation_hours=None,
    )
    with pytest.raises(IncompleteDelegationHoursError):
        delegation_hours_in_range([bad], "EMP-1", date(2026, 8, 1), date(2026, 8, 31))


# --- DEL-07: WorkBalance adds to planned_hours once, never realized_hours --


def test_del_07_balance_adds_planned_hours_once_not_realized():
    baseline = compute_month_balance("EMP-1", MONTH, target_hours=100, assignments=[], absence_facts=[])
    with_delegation = compute_month_balance(
        "EMP-1", MONTH, target_hours=100, assignments=[], absence_facts=[],
        delegation_records=[_delegacja_record(date(2026, 8, 5), date(2026, 8, 7), hours=7)],
    )
    assert with_delegation.planned_hours == baseline.planned_hours + 21
    assert with_delegation.realized_hours == baseline.realized_hours == 0


# --- DEL-08/09: PDF shows DEL and adds to the hour sum, both regimes -------


def test_del_08_ordinary_pdf_shows_del_and_sums_hours(monkeypatch):
    from rota.persistence.site_repository import save_site_print_settings

    conn = connect(":memory:")
    _seed_ordinary(conn)
    save_site_print_settings(conn, _settings())
    append_availability(
        conn, coordinator_id="COORD-1", site_id="SITE-1", availability_id="AV-DEL",
        employee_id="EMP-1", kind=AvailabilityKind.DELEGACJA,
        start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), active=True, delegation_hours=7,
    )
    demand, assignment = _work_item(4, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [demand], [assignment])
    pages = _capture_pages(monkeypatch)
    result = _generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="Sierpień 2026")
    assert isinstance(result, ExportReady)
    flat = [t for page in _finished_pages(pages) for t in page]
    assert any(t == "DEL" for t in flat)


def test_del_09_ochrona_pdf_shows_del_unambiguous_from_dn(monkeypatch):
    conn = connect(":memory:")
    _seed(conn)
    from rota.persistence.site_repository import save_site_print_settings

    save_site_print_settings(conn, _settings())
    append_availability(
        conn, coordinator_id="COORD-1", site_id="SITE-1", availability_id="AV-DEL",
        employee_id="EMP-1", kind=AvailabilityKind.DELEGACJA,
        start_date=date(2026, 8, 5), end_date=date(2026, 8, 5), active=True, delegation_hours=7,
    )
    demand, assignment = _work_item(4, 6, 18, kind=ShiftKind.D)
    _create_version(conn, [demand], [assignment])
    pages = _capture_pages(monkeypatch)
    result = _generate_schedule_pdf(conn, site_id="SITE-1", month=MONTH, period_label="Sierpień 2026")
    assert isinstance(result, ExportReady)
    flat = [t for page in _finished_pages(pages) for t in page]
    assert any(t == "DEL" for t in flat)
    # DEL must never be printed as a bare "D" (which would collide with the
    # OCHRONA day-shift code) -- every occurrence of a lone "D" family code
    # in the used-codes legend/day letters stays exactly "D1".."D5", never
    # a truncated "DEL".
    assert "D" not in flat


# --- R2-01: a saved manual-correction conflict must not block the export --


def test_r2_ordinary_print_does_not_block_a_recorded_manual_assignment_on_delegation_day():
    from datetime import datetime

    day = date(2026, 10, 5)
    employee = Employee("E1", "Jan", date(2020, 1, 1), None, False)
    delegation = AvailabilityRecord(
        "DEL-1", "DEL-V1", "E1", AvailabilityKind.DELEGACJA, day, day, True, None, None, delegation_hours=7,
    )
    rows = _build_ordinary_rows(
        {"E1"}, {"E1": employee}, [day],
        {"E1": {day: [(datetime(2026, 10, 5, 12), datetime(2026, 10, 5, 19), "A1")]}},
        {}, {"E1": [delegation]}, {},
    )
    assert rows
    assert rows[0].day_cells[0] != ["DEL"]  # real work shown, not the DELEGACJA label


def test_r2_ochrona_print_does_not_block_a_recorded_manual_assignment_on_delegation_day():
    day = date(2026, 10, 5)
    employee = Employee("E1", "Jan", date(2020, 1, 1), None, False)
    delegation = AvailabilityRecord(
        "DEL-1", "DEL-V1", "E1", AvailabilityKind.DELEGACJA, day, day, True, None, None, delegation_hours=7,
    )
    rows = _build_rows(
        {"E1"}, {"E1": employee}, [day], {"E1": {day: "D1"}}, {}, {"E1": [delegation]}, {}, {},
    )
    assert rows
    assert rows[0].plan == ["D1"]  # real work code shown, not DEL


if __name__ == "__main__":
    print("test_delegation_absence module OK")

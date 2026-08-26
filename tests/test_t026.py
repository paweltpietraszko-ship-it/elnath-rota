"""ROTA-T026 closure matrix (tasks/ROTA-T026/brief.md section 7): the
engine trust-boundary repair (T26-01..05) and the canonical Site-aware
absence projection (T26-10..19). Reuses tests/test_t018.py's helpers
(_sick, _local_membership, _full_month_calendar) and tests/test_t023.py's
DB fixtures (_setup, SITE, COORDINATOR, MONTH) rather than duplicating
them -- no existing T018/T023/T020 test is moved, removed or duplicated
into this file."""
from __future__ import annotations

import inspect
from datetime import date, datetime

import pytest

import rota.application.schedule_export as schedule_export_module
import rota.planning.absence as absence_module
import rota.planning.engine as engine_module
from rota.application import plan_ops
from rota.domain import AvailabilityKind, Employee, ShiftDemand, WorkBalance
from rota.persistence.availability_repository import append_availability_version
from rota.persistence.work_balance_repository import save_work_balance_target
from rota.planning.absence import (
    DailyAbsenceFact,
    DetailedAbsencePeriodFact,
    DetailedDailyAbsenceFact,
    IncompleteAbsenceReferenceError,
    canonical_daily_hours,
    canonical_site_absence_days,
)
from rota.planning.engine import plan
from rota.planning.shift_catalog import UnclassifiedShiftError
from rota.planning.site_rules import UnsupportedOrMalformedSiteRule
from rota.planning.solver import _effective_targets
from tests.support.minimal_state import base_state
from tests.test_t018 import _full_month_calendar, _local_membership, _sick
from tests.test_t023 import COORDINATOR, MONTH, SITE, _seed_full_month_calendar, _setup

# --- T26-01..05: engine trust boundary --------------------------------------


def test_t26_01_direct_plan_not_calendar_gated_with_canonical_work_balance() -> None:
    demand = ShiftDemand("2026-10-06-D", "test-v1", datetime(2026, 10, 6, 5, 0), datetime(2026, 10, 6, 17, 0), 1)
    employee_a, employee_b = Employee("A", "A", date(2026, 9, 1), None, False), Employee("B", "B", date(2026, 9, 1), None, False)
    sick = _sick("A", date(2026, 10, 1), date(2026, 10, 5))
    wb = WorkBalance("A", date(2026, 10, 1), 156, 0, 0, 0, 0, 0, absence_hours=40)
    state = base_state(
        employees=(employee_a, employee_b), memberships=(_local_membership("A"), _local_membership("B")),
        shift_demands=(demand,), availability_records=(sick,), work_balances=(wb,),
    )
    result = plan(state)
    assert result.status != "TECHNICAL_ERROR"


def test_t26_02_calendar_days_cannot_change_target_arithmetic() -> None:
    wb = WorkBalance("A", date(2026, 10, 1), 156, 0, 0, 0, 0, 0, absence_hours=40)
    state_no_calendar = base_state(work_balances=(wb,), calendar_days=())
    state_full_calendar = base_state(work_balances=(wb,), calendar_days=_full_month_calendar(date(2026, 10, 1)))
    assert _effective_targets(state_no_calendar) == _effective_targets(state_full_calendar) == {"A": 116}


def test_t26_03_hard_availability_unaffected_by_removed_calendar_gate() -> None:
    demand = ShiftDemand("2026-10-06-D", "test-v1", datetime(2026, 10, 6, 5, 0), datetime(2026, 10, 6, 17, 0), 1)
    employee_a = Employee("A", "A", date(2026, 9, 1), None, False)
    sick = _sick("A", date(2026, 10, 1), date(2026, 10, 12))
    state = base_state(employees=(employee_a,), memberships=(_local_membership("A"),), shift_demands=(demand,), availability_records=(sick,))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"  # sole Employee is HARD unavailable -- no eligible Employee, never silently assigned


def test_t26_04_plan_month_still_fails_closed_on_incomplete_reference(tmp_path) -> None:
    conn = _setup(tmp_path)
    _seed_full_month_calendar(conn, MONTH, MONTH)
    save_work_balance_target(conn, employee_id="A", month=MONTH, target_hours=100)
    append_availability_version(
        conn, availability_id="AV-LEGACY", employee_id="A", kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2027, 3, 6), end_date=date(2027, 3, 6), active=True,
    )
    with pytest.raises(IncompleteAbsenceReferenceError):
        plan_ops.plan_month(conn, site_id=SITE, month=MONTH, coordinator_id=COORDINATOR, effective_from=MONTH)


def test_t26_05_unrelated_technical_error_mappings_unchanged(monkeypatch) -> None:
    monkeypatch.setattr(engine_module, "_plan", lambda state, *a, **kw: (_ for _ in ()).throw(UnclassifiedShiftError("bad shift")))
    assert plan(base_state()).status == "TECHNICAL_ERROR"
    monkeypatch.setattr(engine_module, "_plan", lambda state, *a, **kw: (_ for _ in ()).throw(UnsupportedOrMalformedSiteRule("RV-1", "bad rule")))
    assert plan(base_state()).status == "TECHNICAL_ERROR"


# --- T26-10..19: canonical Site-aware absence projection --------------------


def _period(site_id: str, start: datetime, end: datetime, shift_kind=None) -> DetailedAbsencePeriodFact:
    return DetailedAbsencePeriodFact("A-1", "SV-1", site_id, "D-1", None, start, end, shift_kind, "H12", None, None, None)


def test_t26_10_range_clipping_before_precedence_and_status() -> None:
    in_range = DetailedDailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.SICK_LEAVE, "POST_PLAN_REFERENCE", "BOUND", 12, ())
    out_of_range_missing = DetailedDailyAbsenceFact(date(2027, 3, 1), AvailabilityKind.SICK_LEAVE, "POST_PLAN_REFERENCE", "MISSING", None, ())
    days = canonical_site_absence_days([in_range, out_of_range_missing], range_start=date(2027, 3, 5), range_end=date(2027, 3, 10), site_id="SITE-1")
    assert [d.the_date for d in days] == [date(2027, 3, 8)]


def test_t26_11_same_date_sick_leave_one_sick_winner_shared() -> None:
    leave, sick = DailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.LEAVE_GRANTED, "PRE_PLAN_LEAVE", "BOUND", 8), DailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.SICK_LEAVE, "POST_PLAN_REFERENCE", "BOUND", 12)
    assert canonical_daily_hours([leave, sick]) == {date(2027, 3, 8): 12}
    detailed_leave = DetailedDailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.LEAVE_GRANTED, "PRE_PLAN_LEAVE", "BOUND", 8, ())
    detailed_sick = DetailedDailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.SICK_LEAVE, "POST_PLAN_REFERENCE", "BOUND", 12, ())
    days = canonical_site_absence_days([detailed_leave, detailed_sick], range_start=date(2027, 3, 1), range_end=date(2027, 3, 31), site_id="SITE-1")
    assert len(days) == 1 and days[0].kind == AvailabilityKind.SICK_LEAVE and days[0].canonical_hours == 12


def test_t26_12_single_site_post_plan_site_hours_equals_canonical() -> None:
    period = _period("SITE-1", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), "D")
    fact = DetailedDailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.SICK_LEAVE, "POST_PLAN_REFERENCE", "BOUND", 12, (period,))
    days = canonical_site_absence_days([fact], range_start=date(2027, 3, 1), range_end=date(2027, 3, 31), site_id="SITE-1")
    assert days[0].site_hours == days[0].canonical_hours == 12
    assert days[0].site_periods[0].shift_kind == "D"


def test_t26_13_multi_site_post_plan_exposes_only_requested_site() -> None:
    period_a, period_b = _period("SITE-A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), "D"), _period("SITE-B", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), "D")
    fact = DetailedDailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.SICK_LEAVE, "POST_PLAN_REFERENCE", "BOUND", 24, (period_a, period_b))
    days = canonical_site_absence_days([fact], range_start=date(2027, 3, 1), range_end=date(2027, 3, 31), site_id="SITE-A")
    assert days[0].canonical_hours == 24
    assert days[0].site_hours == 12
    assert len(days[0].site_periods) == 1 and days[0].site_periods[0].site_id == "SITE-A"


def test_t26_14_accepted_rest_yields_zero_canonical_and_site() -> None:
    fact = DetailedDailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.SICK_LEAVE, "POST_PLAN_REFERENCE", "BOUND", 0, ())
    days = canonical_site_absence_days([fact], range_start=date(2027, 3, 1), range_end=date(2027, 3, 31), site_id="SITE-1")
    assert days[0].canonical_hours == 0
    assert days[0].site_hours == 0


def test_t26_15_24h_and_dn_provenance_survives_projection() -> None:
    p1 = _period("SITE-1", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), "D")
    p2 = _period("SITE-1", datetime(2027, 3, 8, 17, 0), datetime(2027, 3, 9, 5, 0), "N")
    fact = DetailedDailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.SICK_LEAVE, "POST_PLAN_REFERENCE", "BOUND", 24, (p1, p2))
    days = canonical_site_absence_days([fact], range_start=date(2027, 3, 1), range_end=date(2027, 3, 31), site_id="SITE-1")
    assert days[0].site_hours == 24
    assert {p.shift_kind for p in days[0].site_periods} == {"D", "N"}


def test_t26_16_pre_plan_leave_has_no_site_attribution() -> None:
    fact = DetailedDailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.LEAVE_GRANTED, "PRE_PLAN_LEAVE", "BOUND", 8, ())
    days = canonical_site_absence_days([fact], range_start=date(2027, 3, 1), range_end=date(2027, 3, 31), site_id="SITE-1")
    assert days[0].canonical_hours == 8
    assert days[0].site_hours is None
    assert days[0].site_periods == ()


def test_t26_17_missing_status_raises_canonical_error() -> None:
    fact = DetailedDailyAbsenceFact(date(2027, 3, 8), AvailabilityKind.SICK_LEAVE, "POST_PLAN_REFERENCE", "MISSING", None, ())
    with pytest.raises(IncompleteAbsenceReferenceError):
        canonical_site_absence_days([fact], range_start=date(2027, 3, 1), range_end=date(2027, 3, 31), site_id="SITE-1")


def test_t26_18_schedule_export_has_no_local_precedence_or_duration_sum() -> None:
    source = inspect.getsource(schedule_export_module)
    assert "canonical_site_absence_days" in source
    assert "_winning_days" not in source
    assert not hasattr(schedule_export_module, "_winning_days")


def test_t26_19_absence_module_imports_no_persistence() -> None:
    assert "rota.persistence" not in inspect.getsource(absence_module)

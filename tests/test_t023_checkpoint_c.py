"""ROTA-T023 Checkpoint C test matrix (brief.md section 17 subset, owner-
authorized narrow TASK_SCOPE amendment 2026-08-22): T23-35 (deferred from
Checkpoint B) and T23-40..47 (T020 presentation).

Reuses tests/test_t023.py's Checkpoint A fixtures (SITE/COORDINATOR/MONTH,
_setup, _setup_two_sites, _primary, _accept_one, _accept_two, _accept_version,
_leave) and tests/test_t020.py's print-settings builder (_settings) rather
than duplicating them -- no Checkpoint A/B test is moved, removed or
duplicated into this file."""
from __future__ import annotations

from datetime import date, datetime

import pytest

from rota.application import schedule_export as SE
from rota.domain import Assignment, AssignmentRole, AssignmentState, AvailabilityKind, MembershipKind, ShiftCatalogKind, ShiftDemand, ShiftKind
from rota.persistence import schedule_lifecycle as lifecycle
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.persistence.site_repository import save_site_print_settings
from rota.persistence.work_balance_repository import absence_facts_for_employee
from rota.planning.absence import canonical_hours_in_range
from tests.test_t020 import _settings
from tests.test_t023 import MONTH, SITE, _accept_one, _accept_two, _accept_version, _leave, _setup, _setup_two_sites


def test_t23_35_t020_totals_equal_canonical_projection(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0))
    lifecycle.replace_working_snapshot(conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[])
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    save_site_print_settings(conn, _settings())
    model = SE._assemble_export_model(conn, site_id=SITE, month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "A")
    facts = absence_facts_for_employee(conn, "A", model.days[0], model.days[-1])
    assert row.l4_hours == canonical_hours_in_range(facts, model.days[0], model.days[-1])


def test_t23_40_post_plan_12h_anchored_plan_equal_uc_wyk(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0))
    _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    lifecycle.replace_working_snapshot(conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[])
    save_site_print_settings(conn, _settings())
    model = SE._assemble_export_model(conn, site_id=SITE, month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "A")
    idx = model.days.index(date(2027, 3, 8))
    assert row.plan[idx] == "D1"
    assert row.wyk[idx] == "U1"


def test_t23_41_post_plan_legal_24h_prints_once(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_two(conn, ("D24-1", "A24-1", "A", datetime(2027, 3, 5, 5, 0), datetime(2027, 3, 5, 17, 0)), ("D24-2", "A24-2", "A", datetime(2027, 3, 5, 17, 0), datetime(2027, 3, 6, 5, 0)), work_period_id="WP-1")
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 5), end_date=date(2027, 3, 5))
    lifecycle.replace_working_snapshot(conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[])
    save_site_print_settings(conn, _settings(base_regime="24h", reserve_hours={"C3": 24, "C4": None, "C5": None, "U3": None, "U4": None, "U5": None}))
    model = SE._assemble_export_model(conn, site_id=SITE, month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "A")
    idx = model.days.index(date(2027, 3, 5))
    assert row.wyk[idx] == "C3"
    assert row.wyk.count("C3") == 1  # prints once, not split across the two underlying 12h components


def test_t23_42_post_plan_accepted_rest_no_synthetic_uc(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_version(conn, version_id="SV-1", pairs=[], effective_from=MONTH, accepted_at=datetime(2020, 3, 1, 8, 0))
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    save_site_print_settings(conn, _settings())
    model = SE._assemble_export_model(conn, site_id=SITE, month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "A")
    idx = model.days.index(date(2027, 3, 8))
    assert row.plan[idx] == SE.BLANK
    assert row.wyk[idx] == SE.BLANK


def test_t23_43_post_plan_no_coin_change_relocation(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_two(conn, ("D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0)), ("N-9", "A-9", "A", datetime(2027, 3, 9, 17, 0), datetime(2027, 3, 10, 9, 0)))
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 9))
    lifecycle.replace_working_snapshot(conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[])
    save_site_print_settings(conn, _settings())
    model = SE._assemble_export_model(conn, site_id=SITE, month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "A")
    i8, i9 = model.days.index(date(2027, 3, 8)), model.days.index(date(2027, 3, 9))
    assert row.wyk[i8] == "C1"  # 12h exact, own date
    assert row.wyk[i9] == "C2"  # 16h exact, own date -- never merged/relocated onto one symbol day


def test_t23_44_post_plan_unrepresentable_hours_fails_closed(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 10, 0))  # 5h, no matching legend code
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    lifecycle.replace_working_snapshot(conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[])
    save_site_print_settings(conn, _settings())
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id=SITE, month=MONTH, period_label="x")
    assert exc.value.code == "ABSENCE_DECOMPOSITION_REQUIRED"


def test_t23_45_sick_over_leave_prints_c_only(tmp_path) -> None:
    conn = _setup(tmp_path)
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0))
    _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-A-L")
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), availability_id="AV-A-S")
    lifecycle.replace_working_snapshot(conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[])
    save_site_print_settings(conn, _settings())
    model = SE._assemble_export_model(conn, site_id=SITE, month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "A")
    idx = model.days.index(date(2027, 3, 8))
    assert row.wyk[idx] == "C1"  # SICK wins, one C, no conflict error


def test_t23_46a_post_plan_multi_local_membership_not_ambiguous(tmp_path) -> None:
    conn = _setup_two_sites(tmp_path)  # both SITE-A and SITE-B enabled LOCAL -- both are required sites
    _accept_one(conn, "D-8", "A-8", "A", datetime(2027, 3, 8, 5, 0), datetime(2027, 3, 8, 17, 0), site_id="SITE-A")
    _accept_version(conn, version_id="SV-B", pairs=[], effective_from=MONTH, accepted_at=datetime(2020, 3, 1, 8, 0), site_id="SITE-B")
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), site_id="SITE-A")
    lifecycle.replace_working_snapshot(conn, version_id="SV-1", applied_rule_version_ids=[], shift_demands=[], assignments=[], deviations=[])
    save_site_print_settings(conn, _settings(site_id="SITE-A"))
    model = SE._assemble_export_model(conn, site_id="SITE-A", month=MONTH, period_label="x")
    row = next(r for r in model.rows if r.employee_id == "A")
    idx = model.days.index(date(2027, 3, 8))
    assert row.wyk[idx] == "C1"  # multi-LOCAL alone never makes POST_PLAN ambiguous


def test_t23_46b_pre_plan_multi_local_membership_ambiguous(tmp_path) -> None:
    conn = _setup_two_sites(tmp_path, membership_kind_b=MembershipKind.LOCAL)
    _accept_version(conn, version_id="SV-A", pairs=[], effective_from=MONTH, accepted_at=datetime(2020, 3, 1, 8, 0), site_id="SITE-A", record_action=False)  # a current version for export to reconstruct, but never accepted (no SCHEDULE_CANDIDATE_SELECTED) -- PRE_PLAN still applies
    _leave(conn, employee_id="A", kind=AvailabilityKind.LEAVE_GRANTED, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8), site_id="SITE-A", seed_calendar=True)
    save_site_print_settings(conn, _settings(site_id="SITE-A"))
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id="SITE-A", month=MONTH, period_label="x")
    assert exc.value.code == "ABSENCE_SITE_AMBIGUOUS"  # PRE_PLAN keeps the existing fail-closed attribution


def test_t23_47_defensive_conflict_leaves_work_untouched(tmp_path) -> None:
    conn = _setup(tmp_path)
    # A real, printable work item (shift_kind/catalog_kind set, matching _settings()'s D1 06:00-18:00 interval) so the map_work_code step succeeds and the conflict is caught downstream, at the absence layer.
    demand = ShiftDemand("D-8", "SV-1", datetime(2027, 3, 8, 6, 0), datetime(2027, 3, 8, 18, 0), 1, shift_kind=ShiftKind.D, catalog_kind=ShiftCatalogKind.H12)
    assignment = Assignment("A-8", "SV-1", "A", datetime(2027, 3, 8, 6, 0), datetime(2027, 3, 8, 18, 0), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D-8", None)
    _accept_version(conn, version_id="SV-1", pairs=[(demand, assignment)], effective_from=MONTH, accepted_at=datetime(2020, 3, 1, 8, 0))
    _leave(conn, employee_id="A", kind=AvailabilityKind.SICK_LEAVE, start_date=date(2027, 3, 8), end_date=date(2027, 3, 8))
    save_site_print_settings(conn, _settings())
    before = get_schedule_snapshot(conn, "SV-1").assignments
    with pytest.raises(SE.ExportProblemError) as exc:
        SE._assemble_export_model(conn, site_id=SITE, month=MONTH, period_label="x")
    assert exc.value.code == "ASSIGNMENT_ABSENCE_CONFLICT"
    after = get_schedule_snapshot(conn, "SV-1").assignments
    assert before == after  # export never mutates the underlying schedule

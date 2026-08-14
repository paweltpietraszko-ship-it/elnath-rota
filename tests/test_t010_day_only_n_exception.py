"""ROTA-T010-B tests (tasks/ROTA-T010/part_b_availability.md,
arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md): the narrow
EMPLOYEE_DAY_ONLY_N_EXCEPTION exception to DAY_ONLY-01, and the read-only
availability matrix projection."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from rota.application.availability_matrix import employee_availability_matrix
from rota.domain import (
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    Employee,
    MembershipKind,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
)
from rota.persistence.availability_repository import append_availability_version
from rota.persistence.db import connect
from rota.persistence.decision_ledger import record_decision
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_rule_assembly import assemble_monthly_site_rules
from rota.persistence.site_repository import save_site
from rota.planning.eligibility import check_eligibility
from rota.planning.site_rules import (
    EMPLOYEE_DAY_ONLY_N_EXCEPTION,
    EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
    hard_rules_applicable_on,
)
from rota.planning.validator import validate
from rota.site_memory_types import NewRuleContent
from tests.support.minimal_state import PROFILE_ID, SITE_ID, ReadinessSource, ReadinessState, base_profile, base_state

EMP = "A-DAYONLY"


def _employee(day_only: bool = True) -> Employee:
    return Employee(EMP, "A", date(2026, 9, 1), None, day_only)


def _membership() -> SiteMembership:
    return SiteMembership(EMP, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _n_demand(day: int) -> ShiftDemand:
    return ShiftDemand(f"N-{day}", "test-v1", datetime(2026, 10, day, 17, 0), datetime(2026, 10, day + 1, 5, 0), 1)


def _record(conn, *, rule_id: str, rule_kind: str, parameters: dict, effective_from: date, effective_to) -> None:
    record_decision(
        conn, site_id=SITE_ID, rule_id=rule_id, statement="test", coordinator_id="COORD-1",
        recorded_at=datetime(2026, 9, 1, 9, 0), effective_from=effective_from, rel=None,
        rule_content=NewRuleContent(
            category=RuleCategory.CONFIRMED_EXCEPTION if rule_kind == EMPLOYEE_DAY_ONLY_N_EXCEPTION else RuleCategory.LOCAL_RULE,
            rule_kind=rule_kind, structured_parameters=parameters, enforcement=RuleEnforcement.HARD,
            resolution_status=RuleResolution.RESOLVED, effective_to=effective_to,
            description=None, source=None, reason=None,
        ),
    )


def _record_exception(conn, *, effective_from: date, effective_to) -> None:
    _record(
        conn, rule_id="R-DAYONLY-EXC", rule_kind=EMPLOYEE_DAY_ONLY_N_EXCEPTION,
        parameters={"employee_id": EMP}, effective_from=effective_from, effective_to=effective_to,
    )


def _resolved_and_applicability(conn, month: date):
    resolved, _, applicability = assemble_monthly_site_rules(conn, SITE_ID, month)
    return resolved, applicability


def _eligible_for_n(conn, day: int, month: date, availability_records=()) -> bool:
    resolved, applicability = _resolved_and_applicability(conn, month)
    applicable = hard_rules_applicable_on(resolved, applicability, date(2026, 10, day))
    demand = _n_demand(day)
    result = check_eligibility(
        _employee(), _membership(), demand, ShiftKind.N, base_profile(),
        list(availability_records), [], SITE_ID, applicable,
    )
    return result.eligible


def _validator_blocks_n(conn, day: int, month: date) -> bool:
    resolved, applicability = _resolved_and_applicability(conn, month)
    demand = _n_demand(day)
    state = base_state(
        employees=(_employee(),), memberships=(_membership(),), shift_demands=(demand,),
        site_rules=resolved, site_rule_applicability=applicability, month=month,
    )
    assignment = _make_assignment(day)
    report = validate(state, [assignment])
    return any(v.rule == "DAY_ONLY-01" for v in report.violation_details)


def _make_assignment(day: int):
    from rota.domain import Assignment
    return Assignment(
        assignment_id=f"AS-{day}", schedule_version_id="test-v1", employee_id=EMP,
        start_datetime=datetime(2026, 10, day, 17, 0), end_datetime=datetime(2026, 10, day + 1, 5, 0),
        role=AssignmentRole.PRIMARY, state=AssignmentState.PLANNED, frozen=False,
        covers_demand_id=f"N-{day}", mentor_primary_assignment_id=None,
    )


def _seed_context(conn) -> None:
    save_site_profile(conn, base_profile())
    save_site(conn, Site(SITE_ID, PROFILE_ID, "Test Site", True))
    save_employee(conn, _employee())
    save_site_membership(conn, _membership())


def test_day_before_exception_still_blocked(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    _record_exception(conn, effective_from=date(2026, 10, 10), effective_to=date(2026, 10, 15))
    assert not _eligible_for_n(conn, 9, date(2026, 10, 1))
    assert _validator_blocks_n(conn, 9, date(2026, 10, 1))


def test_both_boundaries_and_middle_allowed(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    _record_exception(conn, effective_from=date(2026, 10, 10), effective_to=date(2026, 10, 15))
    for day in (10, 12, 15):
        assert _eligible_for_n(conn, day, date(2026, 10, 1)), day
        assert not _validator_blocks_n(conn, day, date(2026, 10, 1)), day


def test_day_after_exception_blocked_again(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    _record_exception(conn, effective_from=date(2026, 10, 10), effective_to=date(2026, 10, 15))
    assert not _eligible_for_n(conn, 16, date(2026, 10, 1))
    assert _validator_blocks_n(conn, 16, date(2026, 10, 1))


def test_exception_does_not_lift_other_hard_n_ban(tmp_path: Path) -> None:
    """Exception only exempts DAY_ONLY-01; a separate HARD ban still blocks N (AND)."""
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    _record_exception(conn, effective_from=date(2026, 10, 10), effective_to=date(2026, 10, 15))
    _record(
        conn, rule_id="R-OTHER-N-BAN", rule_kind=EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS,
        parameters={"employee_id": EMP, "weekdays": list(range(1, 8)), "forbidden_shift_kinds": ["N"]},
        effective_from=date(2026, 10, 1), effective_to=None,
    )
    assert not _eligible_for_n(conn, 12, date(2026, 10, 1))


def test_exception_does_not_lift_sick_leave(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    _record_exception(conn, effective_from=date(2026, 10, 10), effective_to=date(2026, 10, 15))
    record = append_availability_version(
        conn, availability_id="AV-1", employee_id=EMP, kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2026, 10, 12), end_date=date(2026, 10, 12), active=True,
    )
    assert not _eligible_for_n(conn, 12, date(2026, 10, 1), availability_records=[record])


def test_disabled_membership_still_blocks_despite_exception(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    _record_exception(conn, effective_from=date(2026, 10, 10), effective_to=date(2026, 10, 15))
    resolved, applicability = _resolved_and_applicability(conn, date(2026, 10, 1))
    applicable = hard_rules_applicable_on(resolved, applicability, date(2026, 10, 12))
    disabled_membership = SiteMembership(EMP, SITE_ID, MembershipKind.LOCAL, False, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)
    result = check_eligibility(
        _employee(), disabled_membership, _n_demand(12), ShiftKind.N, base_profile(), [], [], SITE_ID, applicable,
    )
    assert not result.eligible
    assert result.blocked_reason == "MEMBERSHIP_DISABLED"


def test_availability_matrix_composes_read_only(tmp_path: Path) -> None:
    conn = connect(tmp_path / "rota.db")
    _seed_context(conn)
    _record_exception(conn, effective_from=date(2026, 10, 10), effective_to=date(2026, 10, 15))
    record = append_availability_version(
        conn, availability_id="AV-2", employee_id=EMP, kind=AvailabilityKind.LEAVE_GRANTED,
        start_date=date(2026, 10, 20), end_date=date(2026, 10, 22), active=True,
    )
    matrix = employee_availability_matrix(conn, site_id=SITE_ID, employee_id=EMP, month=date(2026, 10, 1))
    assert matrix.employee.employee_id == EMP
    assert record in matrix.availability_records
    assert any(r.rule_kind == EMPLOYEE_DAY_ONLY_N_EXCEPTION for r in matrix.weekday_and_exception_rules)


def test_restart_reproduces_identical_exception_projection(tmp_path: Path) -> None:
    db_path = tmp_path / "rota.db"
    conn = connect(db_path)
    _seed_context(conn)
    _record_exception(conn, effective_from=date(2026, 10, 10), effective_to=date(2026, 10, 15))
    before = _eligible_for_n(conn, 12, date(2026, 10, 1))
    conn.close()

    reopened = connect(db_path)
    after = _eligible_for_n(reopened, 12, date(2026, 10, 1))
    assert before == after is True

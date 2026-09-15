"""ROTA-THIRD-CONSECUTIVE-SHIFT-ORDINARY-SCOPE (brief.md, Codex
preimplementation PASS 5c91225): THIRD-CONSECUTIVE-SHIFT-01 (ROTA-T058) is
now OCHRONA-only -- OWNER_RULING 2026-09-15, for ORDINARY the only HARD
limits on work rhythm remain the labor-code rules (REST-01/WEEKLY-REST-01).
T058's own OCHRONA-side contract is unchanged and stays covered by
tests/test_t058.py (T58-11/T58-13 there were switched to an explicit
OCHRONA Site so they keep exercising it after this file's regime split).

TCSO-03/08 (solver+plan, no block) and TCSO-05 (manual correction, no
Deviation) are exercised here for ORDINARY. TCSO-04 (isolation from
REST-01/WEEKLY-REST-01/LOAD-01) is not a new fixture: this change touches
only the two THIRD-CONSECUTIVE-SHIFT-01 enforcement points (constraints.py
solver call site + validator_checks_patterns.py), never REST/WEEKLY-REST/
LOAD code, so their own existing test matrices are the isolation proof."""
from __future__ import annotations

from datetime import date, datetime, time

from rota.application import manual_edit
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftDemand,
    ShiftKind,
    Site,
    SiteMembership,
    SitePlanningRegime,
    SiteProfile,
    StandardShift,
    WorkBalance,
)
from rota.persistence import schedule_lifecycle
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.db import connect
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.schedule_repository import get_schedule_snapshot
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site
from rota.planning.engine import plan
from rota.planning.solver import solve
from rota.planning.validator import validate
from tests.support.minimal_state import MONTH, base_state
from tests.test_t032_soft_ranking import _d_demand, _membership


def test_tcso_03_ordinary_three_consecutive_days_feasible():
    """Same shape as test_t058.py's T58-11 (one employee, three mandatory D
    demands, no alternative) but ORDINARY (base_state's own default regime,
    unchanged here) -- T058 no longer blocks it: the solver assigns all
    three, plan() reaches FEASIBLE, and the independent validator raises no
    THIRD-CONSECUTIVE-SHIFT-01 finding (TCSO-03/TCSO-08)."""
    employee = Employee("A", "A", date(2020, 1, 1), None, False)
    demands = (_d_demand(1), _d_demand(2), _d_demand(3))
    work_balances = (WorkBalance("A", MONTH, 36, 0, 0, 0, 0, 0),)
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), shift_demands=demands, work_balances=work_balances,
    )
    outcome = solve(state, enforce_load_cap=False)
    assert outcome.assignments is not None
    assert outcome.status_name in ("OPTIMAL", "FEASIBLE")
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.status != "THIRD_CONSECUTIVE_SHIFT_BLOCKED"
    report = validate(state, result.candidates[0])
    assert not any(v.rule == "THIRD-CONSECUTIVE-SHIFT-01" for v in report.violation_details)


def _tcso05_ordinary_fixture(conn, *, site_id: str, profile_id: str, coord_id: str, month: date) -> None:
    """Deterministic ORDINARY bootstrap via the same raw persistence
    primitives tests/support/t009_fixtures.py uses -- never durable_inputs
    (its update_membership enforces CONFIGURABLE-ROLES' position-role
    requirement, irrelevant to this HARD-scope test) and never
    benchmarks/ (Codex audit R2, tests_r2.txt R2-01: the frozen benchmark
    scenario generator is not an allowed audit dependency, and its
    seed-dependent roster shape let this test finish via an empty
    `return` without ever exercising the manual correction)."""
    save_site_profile(conn, SiteProfile(
        profile_id, profile_id, True, [StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        False, False, False, False, 1, 999,
    ))
    save_site(conn, Site(site_id, profile_id, site_id, True, planning_regime=SitePlanningRegime.ORDINARY))
    save_coordinator(conn, Coordinator(coord_id, "Coord", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation(coord_id, site_id, True))
    save_employee(conn, Employee("E1", "E1", date(2020, 1, 1), None, False))
    save_site_membership(conn, SiteMembership(
        "E1", site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
    ))
    for day in range(1, 32):
        save_calendar_day(conn, CalendarDay(date(month.year, month.month, day), False))


def test_tcso_05_ordinary_manual_correction_never_materializes_the_deviation():
    """Two already-fixed consecutive PRIMARY days for E1 (day 1, day 2) plus
    an open third-day demand (day 3) -- forcing E1 onto day 3 via a manual
    correction must not materialize a THIRD-CONSECUTIVE-SHIFT-01 Deviation
    for this ORDINARY Site, unlike test_t058.py's T58-13 (explicitly
    switched to OCHRONA, where the same shape does materialize it)."""
    site_id, profile_id, coord_id, month = "TCSO-SITE", "TCSO-PROF", "TCSO-COORD", date(2026, 8, 1)
    conn = connect(":memory:")
    _tcso05_ordinary_fixture(conn, site_id=site_id, profile_id=profile_id, coord_id=coord_id, month=month)

    def _demand(day: int) -> ShiftDemand:
        return ShiftDemand(
            f"D-{day}", "V0", datetime(month.year, month.month, day, 6), datetime(month.year, month.month, day, 18), 1,
        )

    def _assignment(day: int) -> Assignment:
        return Assignment(
            f"A-{day}", "V0", "E1", datetime(month.year, month.month, day, 6), datetime(month.year, month.month, day, 18),
            AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, f"D-{day}", None,
        )

    schedule_lifecycle.create_schedule_version(
        conn, version_id="V0", site_id=site_id, month=month, parent_version_id=None,
        created_at=datetime(month.year, month.month, 1, 12), created_by=coord_id, applied_rule_version_ids=[],
        shift_demands=[_demand(1), _demand(2), _demand(3)], assignments=[_assignment(1), _assignment(2)],
        deviations=[], effective_from=month,
    )
    forced = Assignment(
        "A-3-forced", "", "E1", datetime(month.year, month.month, 3, 6), datetime(month.year, month.month, 3, 18),
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D-3", None,
    )
    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=month, coordinator_id=coord_id,
        effective_from=date(month.year, month.month, 2), upsert_assignments=[forced],
    )
    v2_snapshot = get_schedule_snapshot(conn, v2.version_id)
    assert any(a.assignment_id == "A-3-forced" and a.employee_id == "E1" for a in v2_snapshot.assignments)
    assert not any(d.source_reference == "THIRD-CONSECUTIVE-SHIFT-01" for d in v2_snapshot.deviations)


if __name__ == "__main__":
    print("test_third_consecutive_shift_regime_scope module OK")

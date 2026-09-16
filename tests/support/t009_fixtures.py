"""Shared builders for ROTA-T009 application-layer tests. Reuses the
already-audited real-object scenario builder for a realistic, non-trivial
roster/profile instead of a bespoke minimal fixture.

ROTA-CLEANUP-FROZEN-BENCHMARKS (owner-directed, 2026-09-15): this scenario
builder used to live under benchmarks/, entangled with the frozen/broken
benchmark evaluator (real_object.py/real_object_checker.py) even though it
has nothing to do with scoring a benchmark -- it is reused test-fixture
infrastructure. Moved to tests/support/ alongside its own consumer; the
actual dead evaluator chain was deleted, not moved."""
from __future__ import annotations

from datetime import date

from tests.support.real_object_production import build_planning_state
from tests.support.real_object_scenarios import _calendar_case
from rota.domain import Coordinator, CoordinatorSiteAssociation, MembershipKind
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site
from rota.persistence.work_balance_repository import write_work_balance_target_in_open_transaction


def seed_real_object(conn, *, case_id: str, month: date, seed: int, coordinator_id: str = "COORD-1", target_hours: int | None = None):
    """Seeds Site/Profile/Coordinator/CoordinatorSiteAssociation/Employees/
    Memberships/CalendarDay from a real-object scenario, returns the
    production PlanningState used to seed it (for demand/employee lookups
    in tests).

    ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE: target_hours defaults to
    None (no work_balance_targets written at all) -- unchanged behavior,
    load-bearing for tests/test_t009_open_and_assembler.py's own
    missing-target-hours-warning assertions, which need a genuinely bare
    seed. Callers whose tests reach plan_month/replan/precheck pass a
    real value; this writes it for every LOCAL membership so the new
    require_complete_target_hours gate does not block them."""
    scenario = _calendar_case(case_id, month, seed)
    pstate = build_planning_state(scenario)
    save_site_profile(conn, pstate.profile)
    save_site(conn, pstate.site)
    save_coordinator(conn, Coordinator(coordinator_id, "Coord", True))
    save_coordinator_site_association(conn, CoordinatorSiteAssociation(coordinator_id, pstate.site.site_id, True))
    for employee in pstate.employees:
        save_employee(conn, employee)
    for membership in pstate.memberships:
        save_site_membership(conn, membership)
    for day in pstate.calendar_days:
        save_calendar_day(conn, day)
    if target_hours is not None:
        with conn:
            for membership in pstate.memberships:
                if membership.enabled and membership.membership_kind == MembershipKind.LOCAL:
                    write_work_balance_target_in_open_transaction(
                        conn, employee_id=membership.employee_id, month=month, target_hours=target_hours,
                    )
    return pstate

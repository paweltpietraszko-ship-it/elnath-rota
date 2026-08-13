"""Shared builders for ROTA-T009 application-layer tests. Reuses the
already-audited real-object benchmark scenario builder for a realistic,
non-trivial roster/profile instead of a bespoke minimal fixture."""
from __future__ import annotations

from datetime import date

from benchmarks.real_object_production import build_planning_state
from benchmarks.real_object_scenarios import _calendar_case
from rota.domain import Coordinator, CoordinatorSiteAssociation
from rota.persistence.calendar_repository import save_calendar_day
from rota.persistence.coordinator_repository import save_coordinator, save_coordinator_site_association
from rota.persistence.employee_repository import save_employee, save_site_membership
from rota.persistence.site_profile_repository import save_site_profile
from rota.persistence.site_repository import save_site


def seed_real_object(conn, *, case_id: str, month: date, seed: int, coordinator_id: str = "COORD-1"):
    """Seeds Site/Profile/Coordinator/CoordinatorSiteAssociation/Employees/
    Memberships/CalendarDay from a real-object scenario, returns the
    production PlanningState used to seed it (for demand/employee lookups
    in tests)."""
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
    return pstate

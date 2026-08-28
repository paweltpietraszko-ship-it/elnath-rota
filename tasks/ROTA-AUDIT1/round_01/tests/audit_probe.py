"""Independent AUDIT-1 evidence probe.

This is an audit artifact, not a pytest test and not product code.  It builds
fresh isolated SQLite stores exclusively through production bootstrap/durable
input operations, then calls the same planner/validator/lifecycle entry points
used by the API.  It prints JSON facts; it contains no expected-result asserts
that could silently turn this audit into a new product contract.
"""
from __future__ import annotations

import calendar
import json
import sys
import tempfile
from dataclasses import asdict, replace
from datetime import date, datetime, time, timedelta
from pathlib import Path

# Direct execution sets sys.path to this artifact directory, not repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from fastapi.testclient import TestClient
from ortools.sat.python import cp_model

from api.config import DEV_COORDINATOR_ID
from api.deps import get_conn
from api.main import app
from rota.application import bootstrap, durable_inputs, lifecycle_ops, manual_edit, open_month, plan_ops, store
from rota.application.assembler import assemble_planning_state, generate_profile_demands
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    CalendarDay,
    Coordinator,
    CoordinatorSiteAssociation,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    ShiftCatalogKind,
    ShiftKind,
    Site,
    SiteMembership,
    SitePlanningRegime,
    SiteProfile,
    StandardShift,
)
from rota.persistence.db import connect
from rota.persistence.schedule_repository import get_current_version_id, get_schedule_snapshot, get_schedule_version_header
from rota.persistence.site_profile_repository import get_site_profile
from rota.planning.fairness import add_dn_rhythm_reward
from rota.planning.validator import validate

MONTH = date(2026, 9, 1)
COORD = "COORD-AUDIT1"


def emit(scenario: str, **facts) -> None:
    print(json.dumps({"scenario": scenario, **facts}, ensure_ascii=False, sort_keys=True, default=str))


def profile_dn(profile_id: str, *, threshold: int = 60, day_only_blocks_n: bool = False) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id,
        display_name=profile_id,
        active=True,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(6), time(18), False, 1, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=11),
            StandardShift(ShiftKind.N, time(18), time(6), True, 1, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=11),
        ],
        day_only_blocks_n=day_only_blocks_n,
        external_support_enabled=False,
        training_s_enabled=False,
        training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1,
        rolling_7d_decision_threshold_hours=threshold,
    )


def profile_h24(profile_id: str) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id,
        display_name=profile_id,
        active=True,
        standard_shifts=[
            StandardShift(
                ShiftKind.D,
                time(6),
                time(6),
                True,
                1,
                catalog_kind=ShiftCatalogKind.H24,
                required_rest_hours=24,
            )
        ],
        day_only_blocks_n=False,
        external_support_enabled=False,
        training_s_enabled=False,
        training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1,
        rolling_7d_decision_threshold_hours=60,
    )


def profile_empty(profile_id: str) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id,
        display_name=profile_id,
        active=True,
        standard_shifts=[],
        day_only_blocks_n=False,
        external_support_enabled=False,
        training_s_enabled=False,
        training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1,
        rolling_7d_decision_threshold_hours=60,
    )


def bootstrap_site(
    conn,
    *,
    tag: str,
    profile: SiteProfile,
    employee_count: int,
    target_ids: set[int] | None = None,
    day_only_ids: set[int] | None = None,
    month: date = MONTH,
    regime: SitePlanningRegime = SitePlanningRegime.OCHRONA,
) -> tuple[str, tuple[str, ...]]:
    site_id = f"SITE-{tag}"
    target_ids = set(range(employee_count)) if target_ids is None else target_ids
    day_only_ids = set() if day_only_ids is None else day_only_ids
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn,
        coordinator_id=COORD,
        site_id=site_id,
        coordinator=Coordinator(COORD, "Audytor", True),
        site_profile=profile,
    )
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn,
        coordinator_id=COORD,
        site_id=site_id,
        site=Site(site_id, profile.profile_id, tag, True, planning_regime=regime),
        association=CoordinatorSiteAssociation(COORD, site_id, True),
    )
    employees = tuple(f"EMP-{tag}-{i + 1}" for i in range(employee_count))
    for i, employee_id in enumerate(employees):
        durable_inputs.update_employee(
            conn,
            coordinator_id=COORD,
            site_id=site_id,
            employee=Employee(employee_id, employee_id, date(2020, 1, 1), None, i in day_only_ids),
        )
        durable_inputs.update_membership(
            conn,
            coordinator_id=COORD,
            site_id=site_id,
            membership=SiteMembership(
                employee_id,
                site_id,
                MembershipKind.LOCAL,
                True,
                ReadinessState.READY_FOR_PRIMARY,
                ReadinessSource.DEFAULT,
                can_work_24h=True,
            ),
        )
        if i in target_ids:
            durable_inputs.set_target_hours(
                conn,
                coordinator_id=COORD,
                site_id=site_id,
                employee_id=employee_id,
                month=month,
                target_hours=176,
            )
    for d in range(1, calendar.monthrange(month.year, month.month)[1] + 1):
        durable_inputs.set_calendar_day(
            conn,
            coordinator_id=COORD,
            site_id=site_id,
            day=CalendarDay(date(month.year, month.month, d), False),
        )
    return site_id, employees


def hours(candidate) -> dict[str, int]:
    out: dict[str, int] = {}
    for assignment in candidate:
        if assignment.role != AssignmentRole.PRIMARY or assignment.state == AssignmentState.CANCELLED:
            continue
        value = int((assignment.end_datetime - assignment.start_datetime).total_seconds() // 3600)
        out[assignment.employee_id] = out.get(assignment.employee_id, 0) + value
    return dict(sorted(out.items()))


def planning_facts(conn, site_id: str, result) -> dict:
    state, warnings = assemble_planning_state(conn, site_id=site_id, month=MONTH)
    candidate = list(result.candidates[0]) if result.candidates else []
    report = validate(state, candidate) if candidate else None
    return {
        "status": result.status,
        "candidate_count": len(result.candidates),
        "decision_blockers": [asdict(blocker) for blocker in (result.decision_payload.blockers if result.decision_payload else [])],
        "unblocking_options": list(result.decision_payload.unblocking_options) if result.decision_payload else [],
        "error": result.error_message,
        "assembler_warnings": list(warnings),
        "hard_pass": report.hard_pass if report else None,
        "violations": list(report.violations) if report else [],
        "hours": hours(candidate),
        "all_candidate_hours": [hours(list(item)) for item in result.candidates],
    }


def scenario_b01() -> None:
    conn = connect(":memory:")
    site, employees = bootstrap_site(conn, tag="B01", profile=profile_dn("PROF-B01"), employee_count=5)
    result = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    emit("B-01 five LOCAL D/N", roster=list(employees), **planning_facts(conn, site, result))


def scenario_b02() -> None:
    conn = connect(":memory:")
    site, employees = bootstrap_site(
        conn,
        tag="B02",
        profile=profile_dn("PROF-B02", day_only_blocks_n=True),
        employee_count=5,
        day_only_ids={0},
    )
    result = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    n_for_day_only = []
    if result.candidates:
        state, _ = assemble_planning_state(conn, site_id=site, month=MONTH)
        by_id = {d.demand_id: d for d in state.shift_demands}
        n_for_day_only = [
            a.covers_demand_id
            for a in result.candidates[0]
            if a.employee_id == employees[0]
            and a.covers_demand_id
            and by_id[a.covers_demand_id].shift_kind == ShiftKind.N
        ]
    emit("B-02 DAY_ONLY", day_only_employee=employees[0], night_assignments=n_for_day_only, **planning_facts(conn, site, result))


def scenario_b05() -> None:
    conn = connect(":memory:")
    # A real shortage: the normal five-person object is missing two people.
    # The probe never reacts by silently enlarging this declared roster.
    site, employees = bootstrap_site(conn, tag="B05", profile=profile_dn("PROF-B05"), employee_count=2)
    result = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    emit("B-05 shortage", roster=list(employees), **planning_facts(conn, site, result))


def scenario_b06() -> None:
    conn = connect(":memory:")
    site, employees = bootstrap_site(conn, tag="B06", profile=profile_dn("PROF-B06", threshold=24), employee_count=5)
    result = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    emit("B-06 rolling load", roster=list(employees), threshold=24, **planning_facts(conn, site, result))


def scenario_b11_c01() -> None:
    conn = connect(":memory:")
    site, employees = bootstrap_site(conn, tag="B11", profile=profile_h24("PROF-B11"), employee_count=5)
    result = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    state, _ = assemble_planning_state(conn, site_id=site, month=MONTH)
    templates = sorted({d.work_period_template_id for d in state.shift_demands})
    employee_by_template = {template: employees[index % len(employees)] for index, template in enumerate(templates)}
    witness = [
        Assignment(
            f"W-{index}",
            state.schedule_version_id,
            employee_by_template[demand.work_period_template_id],
            demand.start_datetime,
            demand.end_datetime,
            AssignmentRole.PRIMARY,
            AssignmentState.PLANNED,
            False,
            demand.demand_id,
            None,
            work_period_id=f"{site}:{demand.work_period_template_id}",
            required_rest_after_hours=24,
        )
        for index, demand in enumerate(state.shift_demands)
    ]
    witness_report = validate(state, witness)
    emit(
        "B-11/C-01 H24 production vertical",
        roster=list(employees),
        round_robin_witness_hard_pass=witness_report.hard_pass,
        round_robin_witness_violations=list(witness_report.violations),
        round_robin_witness_hours=hours(witness),
        **planning_facts(conn, site, result),
    )

    model = cp_model.CpModel()
    x = model.new_bool_var("h24")
    model.add(x == 1)
    day_terms = {
        "EMP": {
            date(2026, 9, 1): (1, 0, 1, None),
            date(2026, 9, 2): (0, 1, 1, "N"),
            date(2026, 9, 3): (0, 0, x + x, None),
            date(2026, 9, 4): (0, 0, 0, None),
        }
    }
    penalties: list = []
    add_dn_rhythm_reward(model, MONTH, day_terms, penalties)
    if penalties:
        model.minimize(sum(penalties))
    solver = cp_model.CpSolver()
    status = solver.solve(model)
    emit(
        "C-01 minimal fairness root-cause probe",
        cp_status=solver.status_name(status),
        forced_h24_x=1,
        occupancy_expression="2*x",
        penalty_terms=len(penalties),
    )


def scenario_c02() -> None:
    conn = connect(":memory:")
    site, employees = bootstrap_site(conn, tag="C02", profile=profile_dn("PROF-C02"), employee_count=5)
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn,
        coordinator_id=DEV_COORDINATOR_ID,
        site_id=site,
        coordinator=Coordinator(DEV_COORDINATOR_ID, "API coordinator", True),
    )
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn,
        coordinator_id=DEV_COORDINATOR_ID,
        site_id=site,
        association=CoordinatorSiteAssociation(DEV_COORDINATOR_ID, site, True),
    )
    app.dependency_overrides[get_conn] = lambda: (yield conn)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            f"/api/workspace/employees/{employees[0]}/availability",
            json={
                "site_id": site,
                "availability_id": "AV-C02-SICK",
                "kind": "SICK_LEAVE",
                "start_date": "2026-09-12",
                "end_date": "2026-09-14",
            },
        )
        plan_response = client.post(
            f"/api/workspace/sites/{site}/schedule/{MONTH.isoformat()}/plan",
            json={"effective_from": MONTH.isoformat(), "search_attempt": 0},
        )
        emit(
            "C-02 SICK_LEAVE before first PLAN",
            availability_http=response.status_code,
            plan_http=plan_response.status_code,
            response_body=plan_response.text,
        )
    finally:
        app.dependency_overrides.pop(get_conn, None)


def scenario_c03() -> None:
    conn = connect(":memory:")
    overlapping = SiteProfile(
        profile_id="PROF-C03",
        display_name="PROF-C03",
        active=True,
        standard_shifts=[
            StandardShift(ShiftKind.N, time(18), time(6), True, 1, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=11, active_weekdays=(2,)),
            StandardShift(ShiftKind.N, time(22), time(10), True, 1, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=11, active_weekdays=(2,)),
        ],
        day_only_blocks_n=False,
        external_support_enabled=False,
        training_s_enabled=False,
        training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1,
        rolling_7d_decision_threshold_hours=60,
    )
    site, employees = bootstrap_site(conn, tag="C03", profile=overlapping, employee_count=10)
    state, _ = assemble_planning_state(conn, site_id=site, month=MONTH)
    assignments = []
    for index, demand in enumerate(state.shift_demands):
        assignments.append(
            Assignment(
                f"A-{index}",
                "AUDIT-WITNESS",
                employees[index],
                demand.start_datetime,
                demand.end_datetime,
                AssignmentRole.PRIMARY,
                AssignmentState.PLANNED,
                False,
                demand.demand_id,
                None,
                required_rest_after_hours=demand.required_rest_hours,
            )
        )
    report = validate(state, assignments)
    emit(
        "C-03 legal overlapping demand witness",
        demand_count=len(state.shift_demands),
        assignment_count=len(assignments),
        unique_employee_per_demand=len({a.employee_id for a in assignments}) == len(assignments),
        every_assignment_matches_own_demand=all(
            a.start_datetime == d.start_datetime and a.end_datetime == d.end_datetime
            for a, d in zip(assignments, state.shift_demands)
        ),
        hard_pass=report.hard_pass,
        violations=list(report.violations),
    )


def scenario_c04() -> None:
    conn = connect(":memory:")
    empty = profile_empty("PROF-C04")
    site, _ = bootstrap_site(conn, tag="C04", profile=empty, employee_count=5)
    first = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    current_id = get_current_version_id(conn, site, MONTH)
    before = get_schedule_snapshot(conn, current_id)
    durable_inputs.update_site_profile(conn, coordinator_id=COORD, site_id=site, profile=profile_dn("PROF-C04"))
    saved_profile = get_site_profile(conn, "PROF-C04")
    catalog_demands = generate_profile_demands(saved_profile, MONTH)
    assembled_after, _ = assemble_planning_state(conn, site_id=site, month=MONTH)
    second = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=None)
    persisted = get_schedule_snapshot(conn, current_id)
    emit(
        "C-04 shift catalog after empty WORKING",
        first_status=first.status,
        persisted_demands_before=len(before.shift_demands),
        saved_catalog_shift_count=len(saved_profile.standard_shifts),
        demands_generated_directly_from_saved_catalog=len(catalog_demands),
        demands_seen_by_assembler_with_existing_working=len(assembled_after.shift_demands),
        second_status=second.status,
        fresh_candidate_assignments=len(second.candidates[0]) if second.candidates else 0,
        persisted_demands_after=len(persisted.shift_demands),
        current_version_unchanged=get_current_version_id(conn, site, MONTH) == current_id,
    )


def scenario_c05() -> None:
    conn = connect(":memory:")
    site, employees = bootstrap_site(
        conn,
        tag="C05",
        profile=profile_dn("PROF-C05"),
        employee_count=5,
        target_ids={0, 1, 2, 3},
    )
    state, warnings = assemble_planning_state(conn, site_id=site, month=MONTH)
    result = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    emit(
        "C-05 missing target removes employee from fairness",
        roster=list(employees),
        missing_target_employee=employees[4],
        work_balance_employee_ids=sorted(w.employee_id for w in state.work_balances),
        preplan_assembly_warnings=list(warnings),
        **planning_facts(conn, site, result),
    )


def scenario_b03_b04() -> None:
    conn = connect(":memory:")
    site, employees = bootstrap_site(conn, tag="B03", profile=profile_dn("PROF-B03"), employee_count=5)
    initial = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    selected = plan_ops.select_candidate(conn, site_id=site, month=MONTH, candidate=initial.candidates[0], coordinator_id=COORD)
    snap = get_schedule_snapshot(conn, selected.version_id)
    fixed_original = next(a for a in snap.assignments if a.start_datetime.date() == date(2026, 9, 2))
    fixed = replace(fixed_original, state=AssignmentState.REALIZED, frozen=True)
    corrected = manual_edit.apply_manual_correction(
        conn,
        site_id=site,
        month=MONTH,
        coordinator_id=COORD,
        effective_from=date(2026, 9, 3),
        upsert_assignments=[fixed],
    )
    durable_inputs.append_availability(
        conn,
        coordinator_id=COORD,
        site_id=site,
        availability_id="AV-B03-SICK",
        employee_id=employees[0],
        kind=AvailabilityKind.SICK_LEAVE,
        start_date=date(2026, 9, 10),
        end_date=date(2026, 9, 14),
        active=True,
    )
    durable_inputs.append_availability(
        conn,
        coordinator_id=COORD,
        site_id=site,
        availability_id="AV-B04-LEAVE",
        employee_id=employees[1],
        kind=AvailabilityKind.LEAVE_GRANTED,
        start_date=date(2026, 9, 16),
        end_date=date(2026, 9, 16),
        active=True,
    )
    replanned = plan_ops.replan(
        conn,
        site_id=site,
        month=MONTH,
        coordinator_id=COORD,
        effective_from=date(2026, 9, 9),
    )
    fixed_preserved = False
    unavailable_assignments = []
    leave_assignments = []
    if replanned.candidates:
        candidate = replanned.candidates[0]
        fixed_preserved = any(
            a.assignment_id == fixed.assignment_id
            and a.employee_id == fixed.employee_id
            and a.state == AssignmentState.REALIZED
            and a.frozen
            for a in candidate
        )
        unavailable_assignments = [
            a.assignment_id
            for a in candidate
            if a.employee_id == employees[0] and date(2026, 9, 10) <= a.start_datetime.date() <= date(2026, 9, 14)
        ]
        leave_assignments = [
            a.assignment_id
            for a in candidate
            if a.employee_id == employees[1] and a.start_datetime.date() == date(2026, 9, 16)
        ]
    emit(
        "B-03/B-04 SICK replan plus another leave",
        initial_version=selected.version_id,
        corrected_version=corrected.version_id,
        replan_status=replanned.status,
        fixed_preserved=fixed_preserved,
        sick_employee_assignments_during_block=unavailable_assignments,
        leave_employee_assignments_during_block=leave_assignments,
        **planning_facts(conn, site, replanned),
    )


def scenario_b07() -> None:
    conn = connect(":memory:")
    august = date(2026, 8, 1)
    profile = profile_dn("PROF-B07")
    site, employees = bootstrap_site(conn, tag="B07", profile=profile, employee_count=5, month=august)
    for employee in employees:
        durable_inputs.set_target_hours(
            conn,
            coordinator_id=COORD,
            site_id=site,
            employee_id=employee,
            month=august,
            target_hours=160,
        )
        durable_inputs.set_target_hours(
            conn,
            coordinator_id=COORD,
            site_id=site,
            employee_id=employee,
            month=MONTH,
            target_hours=176,
        )
    for d in range(1, calendar.monthrange(MONTH.year, MONTH.month)[1] + 1):
        durable_inputs.set_calendar_day(
            conn,
            coordinator_id=COORD,
            site_id=site,
            day=CalendarDay(date(MONTH.year, MONTH.month, d), False),
        )
    durable_inputs.set_calendar_day(
        conn,
        coordinator_id=COORD,
        site_id=site,
        day=CalendarDay(date(2026, 8, 15), True),
    )
    august_result = plan_ops.plan_month(conn, site_id=site, month=august, coordinator_id=COORD, effective_from=august)
    plan_ops.select_candidate(conn, site_id=site, month=august, candidate=august_result.candidates[0], coordinator_id=COORD)
    september_result = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    state, _ = assemble_planning_state(conn, site_id=site, month=MONTH)
    report = validate(state, september_result.candidates[0]) if september_result.candidates else None
    emit(
        "B-07 REST month boundary",
        boundary_assignments=len(state.boundary_assignments),
        status=september_result.status,
        hard_pass=report.hard_pass if report else None,
        rest_violations=[v for v in (report.violations if report else []) if v.startswith("REST-01")],
    )


def scenario_b08_b09() -> None:
    db_path = Path(__file__).with_name("b08_restart.db")
    try:
        conn = store.open_store(db_path)
        site, _ = bootstrap_site(conn, tag="B08", profile=profile_dn("PROF-B08"), employee_count=5)
        result = plan_ops.plan_month(conn, site_id=site, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
        selected = plan_ops.select_candidate(conn, site_id=site, month=MONTH, candidate=result.candidates[0], coordinator_id=COORD)
        before = open_month.open_month(conn, site_id=site, month=MONTH)
        conn.close()
        reopened = store.open_store(db_path)
        after = open_month.open_month(reopened, site_id=site, month=MONTH)
        emit(
            "B-08 restart/reopen",
            identical=before == after,
            version_before=before.current_version.version_id,
            version_after=after.current_version.version_id,
            assignment_count=len(get_schedule_snapshot(reopened, after.current_version.version_id).assignments),
        )
        state, _ = assemble_planning_state(reopened, site_id=site, month=MONTH)
        acknowledged = {d.deviation_id for d in state.deviations}
        final = lifecycle_ops.finalize(
            reopened,
            site_id=site,
            month=MONTH,
            coordinator_id=COORD,
            acknowledged_deviation_ids=acknowledged,
        )
        parent_before = get_schedule_snapshot(reopened, final.version_id)
        target = parent_before.assignments[0]
        child = manual_edit.freeze_or_unfreeze(
            reopened,
            site_id=site,
            month=MONTH,
            coordinator_id=COORD,
            effective_from=date(2026, 9, 2),
            assignment_id=target.assignment_id,
            frozen=not target.frozen,
        )
        parent_after = get_schedule_snapshot(reopened, final.version_id)
        emit(
            "B-09 manual correction after FINAL",
            parent_version=final.version_id,
            parent_status=get_schedule_version_header(reopened, final.version_id).status.value,
            child_version=child.version_id,
            child_parent=child.parent_version_id,
            parent_unchanged=parent_before == parent_after,
            current_is_child=get_current_version_id(reopened, site, MONTH) == child.version_id,
        )
        reopened.close()
    finally:
        # Kept until the process has fully released SQLite on Windows. The
        # audit driver removes this artifact after recording the result.
        pass


def scenario_b10() -> None:
    # The valid durable-input boundary rejects malformed shift shapes before
    # PLAN.  The planner's own fail-closed owner is therefore probed with the
    # smallest unclassified persisted-demand shape at its public engine edge.
    from rota.domain import ShiftDemand
    from rota.planning.engine import plan
    from rota.planning.state import PlanningState

    conn = connect(":memory:")
    site, _ = bootstrap_site(conn, tag="B10", profile=profile_empty("PROF-B10"), employee_count=1)
    state, _ = assemble_planning_state(conn, site_id=site, month=MONTH)
    bad = ShiftDemand(
        "BAD-UNCLASSIFIED",
        "AUDIT",
        datetime(2026, 9, 1, 8),
        datetime(2026, 9, 1, 16),
        1,
    )
    malformed = replace(state, shift_demands=(bad,))
    result = plan(malformed)
    emit("B-10 invalid planner model/config", entrypoint="planning.engine.plan", status=result.status, error=result.error_message)


GROUPS = {
    "core": [scenario_b01, scenario_b02, scenario_b05, scenario_b06],
    "core_retry": [scenario_b05, scenario_b06],
    "lifecycle": [scenario_b03_b04, scenario_b07, scenario_b08_b09, scenario_b10],
    "lifecycle_retry": [scenario_b07, scenario_b08_b09],
    "restart_retry": [scenario_b08_b09],
    "incidents": [scenario_b11_c01, scenario_c02, scenario_c03, scenario_c04, scenario_c05],
    "incidents_retry": [scenario_c02, scenario_c03, scenario_c04],
    "c04_retry": [scenario_c04],
}


if __name__ == "__main__":
    group = sys.argv[1] if len(sys.argv) > 1 else "core"
    if group not in GROUPS:
        raise SystemExit(f"unknown group {group!r}; choose {', '.join(GROUPS)}")
    for function in GROUPS[group]:
        started = datetime.now()
        try:
            function()
        except Exception as exc:  # audit must record one failure and continue
            emit(function.__name__, probe_exception=f"{type(exc).__name__}: {exc}")
        finally:
            emit(function.__name__ + " timing", elapsed_seconds=round((datetime.now() - started).total_seconds(), 3))

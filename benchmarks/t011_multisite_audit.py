"""Reproducible multi-Site readiness evidence through ``rota.application.*``.

This audit distinguishes Site-owned state from facts intentionally shared by
one Employee across Sites: WorkBalance, availability and REST/LOAD context.
"""
from __future__ import annotations

import calendar
import json
import tempfile
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path

from rota.application import (
    balance_read,
    bootstrap,
    durable_inputs,
    lifecycle_ops,
    memory_read,
    open_month,
    plan_ops,
    rule_decisions,
    store,
)
from rota.application.assembler import assemble_planning_state
from rota.domain import (
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
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
)
from rota.planning.validator import validate

MONTH = date(2026, 10, 1)
QUARTER_MONTHS = (date(2026, 10, 1), date(2026, 11, 1), date(2026, 12, 1))
COORDINATOR_ID = "COORD-MULTISITE"
RULE_ID = "RULE-MULTISITE-SITE-A-ONLY"
DAY_ONLY_EXCEPTION_KIND = "EMPLOYEE_DAY_ONLY_N_EXCEPTION"


@dataclass(frozen=True)
class SiteCase:
    site_id: str
    profile_id: str
    employee_ids: tuple[str, ...]
    shift_kind: ShiftKind
    start_time: time
    end_time: time
    end_next_day: bool
    target_hours: int


def _profile(case: SiteCase) -> SiteProfile:
    return SiteProfile(
        case.profile_id,
        f"Profile {case.site_id}",
        True,
        [StandardShift(case.shift_kind, case.start_time, case.end_time, case.end_next_day, 1)],
        True,
        False,
        False,
        False,
        1,
        999,
    )


def _bootstrap_site(conn, case: SiteCase) -> None:
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn,
        coordinator_id=COORDINATOR_ID,
        site_id=case.site_id,
        coordinator=Coordinator(COORDINATOR_ID, "Multi-Site coordinator", True),
        site_profile=_profile(case),
        site=Site(case.site_id, case.profile_id, f"Site {case.site_id}", True),
        association=CoordinatorSiteAssociation(COORDINATOR_ID, case.site_id, True),
    )


def _configure_roster_and_targets(conn, case: SiteCase) -> None:
    for employee_id in case.employee_ids:
        durable_inputs.update_employee(
            conn,
            coordinator_id=COORDINATOR_ID,
            site_id=case.site_id,
            employee=Employee(employee_id, employee_id, date(2020, 1, 1), None, False),
        )
        durable_inputs.update_membership(
            conn,
            coordinator_id=COORDINATOR_ID,
            site_id=case.site_id,
            membership=SiteMembership(
                employee_id,
                case.site_id,
                MembershipKind.LOCAL,
                True,
                ReadinessState.READY_FOR_PRIMARY,
                ReadinessSource.DEFAULT,
            ),
        )
        for month in QUARTER_MONTHS:
            durable_inputs.set_target_hours(
                conn,
                coordinator_id=COORDINATOR_ID,
                site_id=case.site_id,
                employee_id=employee_id,
                month=month,
                target_hours=case.target_hours,
            )


def _write_calendar(conn, site_id: str) -> None:
    for day_number in range(1, calendar.monthrange(MONTH.year, MONTH.month)[1] + 1):
        durable_inputs.set_calendar_day(
            conn,
            coordinator_id=COORDINATOR_ID,
            site_id=site_id,
            day=CalendarDay(date(MONTH.year, MONTH.month, day_number), False),
        )


def _record_site_a_rule(conn, case: SiteCase) -> str:
    decision = rule_decisions.record_structured_rule_decision(
        conn,
        coordinator_id=COORDINATOR_ID,
        site_id=case.site_id,
        rule_id=RULE_ID,
        statement="Site A only: resolved day-only N exception provenance.",
        effective_from=MONTH,
        rule_content=rule_decisions.NewRuleContent(
            category=RuleCategory.CONFIRMED_EXCEPTION,
            rule_kind=DAY_ONLY_EXCEPTION_KIND,
            structured_parameters={"employee_id": case.employee_ids[0]},
            enforcement=RuleEnforcement.HARD,
            resolution_status=RuleResolution.RESOLVED,
            effective_to=date(2026, 10, 31),
            description="Multi-Site rule isolation probe",
            source="owner-requested multi-Site readiness audit",
            reason="Prove Site A rule never enters Site B",
        ),
    )
    assert decision.rule_version_id is not None
    return decision.rule_version_id


def _assert_ready(conn, *cases: SiteCase) -> None:
    active_site_ids = {
        site.site_id for site in bootstrap.active_sites_for_coordinator(conn, coordinator_id=COORDINATOR_ID)
    }
    assert active_site_ids == {case.site_id for case in cases}
    for case in cases:
        readiness = bootstrap.month_plan_readiness(
            conn, coordinator_id=COORDINATOR_ID, site_id=case.site_id, month=MONTH,
        )
        assert readiness.ready
        assert readiness.missing == ()
        assert readiness.target_hours_warnings == ()


def _active_primary(assignments) -> list:
    return [
        assignment for assignment in assignments
        if assignment.role == AssignmentRole.PRIMARY and assignment.state != AssignmentState.CANCELLED
    ]


def _plan_select_finalize(conn, case: SiteCase):
    result = plan_ops.plan_month(
        conn,
        site_id=case.site_id,
        month=MONTH,
        coordinator_id=COORDINATOR_ID,
        effective_from=MONTH,
    )
    assert result.status == "FEASIBLE"
    assert result.candidates
    plan_ops.select_candidate(
        conn,
        site_id=case.site_id,
        month=MONTH,
        candidate=result.candidates[0],
        coordinator_id=COORDINATOR_ID,
    )
    lifecycle_ops.revalidate(
        conn, site_id=case.site_id, month=MONTH, coordinator_id=COORDINATOR_ID,
    )
    state, warnings = assemble_planning_state(conn, site_id=case.site_id, month=MONTH)
    assert validate(state, list(state.existing_assignments)).hard_pass
    final = lifecycle_ops.finalize(
        conn,
        site_id=case.site_id,
        month=MONTH,
        coordinator_id=COORDINATOR_ID,
        acknowledged_deviation_ids={deviation.deviation_id for deviation in state.deviations},
        reason="Multi-Site readiness audit",
    )
    assert final.status.value.startswith("FINAL")
    return final, tuple(warnings)


def _quarter_planned_hours(conn, employee_id: str) -> int:
    balances, warnings = balance_read.quarter_balance(
        conn, employee_id=employee_id, quarter_first_month=MONTH,
    )
    assert warnings == []
    assert len(balances) == 3
    return balances[0].planned_hours


def _assignment_summary(state) -> dict:
    primary = _active_primary(state.existing_assignments)
    return {
        "count": len(primary),
        "employee_ids": sorted({assignment.employee_id for assignment in primary}),
        "version_ids": sorted({assignment.schedule_version_id for assignment in primary}),
    }


def _restart_and_compare(conn, db_path: Path, site_ids: tuple[str, str]):
    before = {site_id: open_month.open_month(conn, site_id=site_id, month=MONTH) for site_id in site_ids}
    conn.close()
    reopened = store.open_store(db_path)
    after = {site_id: open_month.open_month(reopened, site_id=site_id, month=MONTH) for site_id in site_ids}
    assert after == before
    return reopened, after


def _disjoint_cases() -> tuple[SiteCase, SiteCase]:
    return (
        SiteCase("SITE-MS-A", "PROFILE-MS-A", ("EMP-MS-A",), ShiftKind.N, time(18), time(6), True, 372),
        SiteCase("SITE-MS-B", "PROFILE-MS-B", ("EMP-MS-B",), ShiftKind.D, time(6), time(18), False, 372),
    )


def _initialize_disjoint(conn, site_a: SiteCase, site_b: SiteCase) -> str:
    for case in (site_a, site_b):
        _bootstrap_site(conn, case)
        _configure_roster_and_targets(conn, case)
    _write_calendar(conn, site_a.site_id)
    durable_inputs.append_availability(
        conn,
        coordinator_id=COORDINATOR_ID,
        site_id=site_a.site_id,
        availability_id="AV-MS-A-DAY-OFF",
        employee_id=site_a.employee_ids[0],
        kind=AvailabilityKind.LEAVE_PLAN,
        start_date=date(2026, 10, 10),
        end_date=date(2026, 10, 10),
        active=True,
    )
    rule_version_id = _record_site_a_rule(conn, site_a)
    _assert_ready(conn, site_a, site_b)

    pre_a, _ = assemble_planning_state(conn, site_id=site_a.site_id, month=MONTH)
    pre_b, _ = assemble_planning_state(conn, site_id=site_b.site_id, month=MONTH)
    assert {employee.employee_id for employee in pre_a.employees} == set(site_a.employee_ids)
    assert {employee.employee_id for employee in pre_b.employees} == set(site_b.employee_ids)
    assert {record.employee_id for record in pre_a.availability_records} == set(site_a.employee_ids)
    assert pre_b.availability_records == ()
    assert {rule.rule_version_id for rule in pre_a.site_rules} == {rule_version_id}
    assert pre_b.site_rules == ()
    return rule_version_id


def _disjoint_evidence(reopened, views, cases, summaries, warnings) -> dict:
    site_a, site_b = cases
    site_ids = (site_a.site_id, site_b.site_id)
    return {
        "scenario": "disjoint_full_cycle",
        "status": "PASS",
        "active_sites": sorted(
            site.site_id for site in bootstrap.active_sites_for_coordinator(reopened, coordinator_id=COORDINATOR_ID)
        ),
        "assignments": summaries,
        "current_versions": {site_id: views[site_id].current_version.version_id for site_id in site_ids},
        "applied_rules": {
            site_a.site_id: views[site_a.site_id].current_version.applied_rule_version_ids,
            site_b.site_id: views[site_b.site_id].current_version.applied_rule_version_ids,
        },
        "rule_history_keys": {
            site_id: sorted(memory_read.rules_history_for_site(reopened, site_id=site_id)) for site_id in site_ids
        },
        "months_with_schedule": {
            site_id: [month.isoformat() for month in open_month.months_with_schedule(reopened, site_id=site_id)]
            for site_id in site_ids
        },
        "quarter_planned_hours": {
            case.employee_ids[0]: _quarter_planned_hours(reopened, case.employee_ids[0]) for case in cases
        },
        "warnings": warnings,
        "site_a_unchanged_after_site_b_cycle": True,
    }


def run_disjoint_full_cycle(db_path: Path) -> dict:
    site_a, site_b = _disjoint_cases()
    conn = store.open_store(db_path)
    rule_version_id = _initialize_disjoint(conn, site_a, site_b)

    final_a, warnings_a = _plan_select_finalize(conn, site_a)
    site_a_after_finalize = open_month.open_month(conn, site_id=site_a.site_id, month=MONTH)
    unopened_b = open_month.open_month(conn, site_id=site_b.site_id, month=MONTH)
    assert unopened_b.current_version is None
    assert open_month.months_with_schedule(conn, site_id=site_b.site_id) == ()
    final_b, warnings_b = _plan_select_finalize(conn, site_b)
    assert open_month.open_month(conn, site_id=site_a.site_id, month=MONTH) == site_a_after_finalize

    state_a, _ = assemble_planning_state(conn, site_id=site_a.site_id, month=MONTH)
    state_b, _ = assemble_planning_state(conn, site_id=site_b.site_id, month=MONTH)
    assert state_a.other_site_assignments == ()
    assert state_b.other_site_assignments == ()
    assert final_a.version_id != final_b.version_id
    assert final_a.applied_rule_version_ids == [rule_version_id]
    assert final_b.applied_rule_version_ids == []
    summaries = {site_a.site_id: _assignment_summary(state_a), site_b.site_id: _assignment_summary(state_b)}

    reopened, views = _restart_and_compare(conn, db_path, (site_a.site_id, site_b.site_id))
    warnings = {site_a.site_id: list(warnings_a), site_b.site_id: list(warnings_b)}
    evidence = _disjoint_evidence(reopened, views, (site_a, site_b), summaries, warnings)
    reopened.close()
    return evidence


def _shared_cases(site_b_start: time) -> tuple[SiteCase, SiteCase]:
    shared = ("EMP-MS-SHARED",)
    site_b_end = time(site_b_start.hour + 1)
    return (
        SiteCase("SITE-MS-SHARED-A", "PROFILE-MS-SHARED-A", shared, ShiftKind.D, time(6), time(7), False, 62),
        SiteCase("SITE-MS-SHARED-B", "PROFILE-MS-SHARED-B", shared, ShiftKind.N, site_b_start, site_b_end, False, 62),
    )


def _setup_shared(conn, site_b_start: time) -> tuple[SiteCase, SiteCase]:
    site_a, site_b = _shared_cases(site_b_start)
    for case in (site_a, site_b):
        _bootstrap_site(conn, case)
        _configure_roster_and_targets(conn, case)
    _write_calendar(conn, site_a.site_id)
    _assert_ready(conn, site_a, site_b)
    return site_a, site_b


def _prepare_shared_full(conn, site_a: SiteCase, site_b: SiteCase) -> str:
    rule_version_id = _record_site_a_rule(conn, site_a)
    durable_inputs.append_availability(
        conn,
        coordinator_id=COORDINATOR_ID,
        site_id=site_a.site_id,
        availability_id="AV-MS-SHARED-LEAVE-PLAN",
        employee_id=site_a.employee_ids[0],
        kind=AvailabilityKind.LEAVE_PLAN,
        start_date=date(2026, 10, 15),
        end_date=date(2026, 10, 15),
        active=True,
    )
    initial_a, _ = assemble_planning_state(conn, site_id=site_a.site_id, month=MONTH)
    initial_b, _ = assemble_planning_state(conn, site_id=site_b.site_id, month=MONTH)
    assert {rule.rule_version_id for rule in initial_a.site_rules} == {rule_version_id}
    assert initial_b.site_rules == ()
    assert len(initial_a.availability_records) == 1
    assert initial_a.availability_records == initial_b.availability_records
    return rule_version_id


def _assert_shared_after_b(conn, site_a, site_b, final_a, final_b, site_a_after_finalize) -> None:
    after_a, _ = assemble_planning_state(conn, site_id=site_a.site_id, month=MONTH)
    after_b, _ = assemble_planning_state(conn, site_id=site_b.site_id, month=MONTH)
    assert len(after_a.other_site_assignments) == 31
    assert len(after_b.other_site_assignments) == 31
    assert len(after_a.existing_assignments) == 31
    assert len(after_b.existing_assignments) == 31
    assert after_a.existing_assignments == site_a_after_finalize.existing_assignments
    assert final_a.applied_rule_version_ids
    assert final_b.applied_rule_version_ids == []


def _shared_evidence(reopened, views, cases, finals, warnings) -> dict:
    site_a, site_b = cases
    final_a, final_b = finals
    site_ids = (site_a.site_id, site_b.site_id)
    shared_employee = site_a.employee_ids[0]
    return {
        "scenario": "shared_employee_full_cycle",
        "status": "PASS",
        "shared_employee_id": shared_employee,
        "site_assignment_hours": {site_a.site_id: 31, site_b.site_id: 31},
        "global_quarter_planned_hours": _quarter_planned_hours(reopened, shared_employee),
        "open_month_planned_hours": {
            site_id: next(balance.planned_hours for balance in views[site_id].work_balances if balance.month == MONTH)
            for site_id in site_ids
        },
        "other_site_assignment_counts": {site_a.site_id: 31, site_b.site_id: 31},
        "global_availability_counts": {site_a.site_id: 1, site_b.site_id: 1},
        "applied_rules": {
            site_a.site_id: final_a.applied_rule_version_ids,
            site_b.site_id: final_b.applied_rule_version_ids,
        },
        "rule_history_keys": {
            site_id: sorted(memory_read.rules_history_for_site(reopened, site_id=site_id)) for site_id in site_ids
        },
        "current_versions": {site_a.site_id: final_a.version_id, site_b.site_id: final_b.version_id},
        "months_with_schedule": {
            site_id: [month.isoformat() for month in open_month.months_with_schedule(reopened, site_id=site_id)]
            for site_id in site_ids
        },
        "warnings": warnings,
        "site_a_assignments_unchanged_after_site_b_cycle": True,
    }


def run_shared_full_cycle(db_path: Path) -> dict:
    conn = store.open_store(db_path)
    site_a, site_b = _setup_shared(conn, time(18))
    rule_version_id = _prepare_shared_full(conn, site_a, site_b)
    final_a, warnings_a = _plan_select_finalize(conn, site_a)
    site_a_after_finalize, _ = assemble_planning_state(conn, site_id=site_a.site_id, month=MONTH)
    before_b, _ = assemble_planning_state(conn, site_id=site_b.site_id, month=MONTH)
    assert len(before_b.other_site_assignments) == 31
    assert {item.schedule_version_id for item in before_b.other_site_assignments} == {final_a.version_id}
    final_b, warnings_b = _plan_select_finalize(conn, site_b)
    assert final_a.applied_rule_version_ids == [rule_version_id]
    _assert_shared_after_b(conn, site_a, site_b, final_a, final_b, site_a_after_finalize)

    reopened, views = _restart_and_compare(conn, db_path, (site_a.site_id, site_b.site_id))
    warnings = {site_a.site_id: list(warnings_a), site_b.site_id: list(warnings_b)}
    evidence = _shared_evidence(reopened, views, (site_a, site_b), (final_a, final_b), warnings)
    reopened.close()
    return evidence


def run_shared_rest_collision(db_path: Path) -> dict:
    conn = store.open_store(db_path)
    site_a, site_b = _setup_shared(conn, time(17))
    final_a, _ = _plan_select_finalize(conn, site_a)
    site_a_before = open_month.open_month(conn, site_id=site_a.site_id, month=MONTH)
    result = plan_ops.plan_month(
        conn,
        site_id=site_b.site_id,
        month=MONTH,
        coordinator_id=COORDINATOR_ID,
        effective_from=MONTH,
    )
    assert result.status == "DECISION_REQUIRED"
    assert result.candidates == []
    assert result.decision_payload is not None
    blockers = sorted({blocker.condition for blocker in result.decision_payload.blockers})
    assert blockers == ["REST-01"]
    assert open_month.open_month(conn, site_id=site_a.site_id, month=MONTH) == site_a_before
    assert open_month.months_with_schedule(conn, site_id=site_b.site_id) == ()

    site_b_view = open_month.open_month(conn, site_id=site_b.site_id, month=MONTH)
    assert site_b_view.current_version is not None
    conn.close()
    reopened = store.open_store(db_path)
    assert open_month.open_month(reopened, site_id=site_a.site_id, month=MONTH) == site_a_before
    reopened_b = open_month.open_month(reopened, site_id=site_b.site_id, month=MONTH)
    assert reopened_b == site_b_view
    evidence = {
        "scenario": "shared_employee_rest_collision",
        "status": result.status,
        "site_a_final_version": final_a.version_id,
        "site_a_assignment_count": len(_active_primary(assemble_planning_state(reopened, site_id=site_a.site_id, month=MONTH)[0].existing_assignments)),
        "site_b_assignment_count": len(_active_primary(assemble_planning_state(reopened, site_id=site_b.site_id, month=MONTH)[0].existing_assignments)),
        "site_b_blocking_demand_count": len(result.decision_payload.blocking_shift_demands),
        "site_b_blocker_conditions": blockers,
        "site_b_months_with_schedule": [
            month.isoformat() for month in open_month.months_with_schedule(reopened, site_id=site_b.site_id)
        ],
    }
    reopened.close()
    return evidence


def write_evidence(evidence: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")


def run_all(output_dir: Path) -> dict[str, dict]:
    runners = {
        "disjoint_full_cycle": run_disjoint_full_cycle,
        "shared_employee_full_cycle": run_shared_full_cycle,
        "shared_employee_rest_collision": run_shared_rest_collision,
    }
    evidence = {}
    with tempfile.TemporaryDirectory(prefix="t011-multisite-") as temp_dir:
        for name, runner in runners.items():
            outcome = runner(Path(temp_dir) / f"{name}.db")
            evidence[name] = outcome
            write_evidence(outcome, output_dir / f"{name}.json")
    return evidence


def main() -> int:
    evidence = run_all(Path("artifacts/t011_multisite"))
    for name, outcome in evidence.items():
        print(f"{name}: {outcome['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

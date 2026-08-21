"""Vertical full-stack regression: several DISTINCT realistic paths through
the CURRENT feature set (T012 catalog/24h, T017 multi-variant semantics via
select_candidate, T018 absence, T019 analytics, T019b action ledger, T020
PDF export, T022 planning-integrity fixes) via rota.application.* only --
the same entry points a real coordinator uses.

Per-task test files already cover each feature in isolation deeply. What is
missing (Paweł, 2026-08-21) is proof that the CURRENT set of features still
composes correctly end to end, through the real application/persistence
layers, not just each task's own dedicated fixture. Multiple independent
scenarios on purpose -- one scenario is one arbitrarily chosen path; a
single happy path proves nothing about a different one.
"""
from __future__ import annotations

import calendar as _calendar
from datetime import date, time
from pathlib import Path

from rota.application import bootstrap, durable_inputs, lifecycle_ops, manual_edit, memory_read, open_month, plan_ops, store
from rota.application.analytics_read import analytics_for_site_month
from rota.application.assembler import assemble_planning_state
from rota.application.schedule_export import ExportReady, generate_schedule_pdf
from rota.domain import (
    AssignmentRole,
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
    SiteProfile,
    StandardShift,
)
from rota.persistence.site_repository import SitePrintSettings, WorkCodeInterval, save_site_print_settings

COORD = "COORD-V1"


def _profile_h12(profile_id: str, *, rolling_threshold: int = 999) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id, display_name=profile_id, active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=rolling_threshold,
    )


def _profile_h24(profile_id: str) -> SiteProfile:
    # Mondays-only H24 on-call (7-day gap is well clear of the 24h rest wall, so a
    # single eligible employee can legally cover every occurrence alone) plus a
    # trivial Tuesday-only H12 filler shift so the profile is NOT all-24h -- that
    # matters because is_all_24h_profile() makes SHIFT-24-01/can_work_24h a no-op,
    # which would make this scenario prove nothing about the gate it targets.
    return SiteProfile(
        profile_id=profile_id, display_name=profile_id, active=True,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(8, 0), time(8, 0), True, 1, catalog_kind=ShiftCatalogKind.H24, required_rest_hours=24, active_weekdays=(1,)),
            StandardShift(ShiftKind.D, time(8, 0), time(20, 0), False, 1, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=11, active_weekdays=(2,)),
        ],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _profile_h12_dn(profile_id: str, *, rest_hours: int = 11) -> SiteProfile:
    return SiteProfile(
        profile_id=profile_id, display_name=profile_id, active=True,
        standard_shifts=[
            StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=rest_hours),
            StandardShift(ShiftKind.N, time(18, 0), time(6, 0), True, 1, catalog_kind=ShiftCatalogKind.H12, required_rest_hours=rest_hours),
        ],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _bootstrap(conn, *, site_id: str, profile_id: str, profile: SiteProfile, employees: tuple[str, ...], month: date) -> None:
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=site_id, coordinator=Coordinator(COORD, "Coord", True), site_profile=profile,
    )
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=site_id,
        site=Site(site_id, profile_id, site_id, True), association=CoordinatorSiteAssociation(COORD, site_id, True),
    )
    for employee_id in employees:
        durable_inputs.update_employee(conn, coordinator_id=COORD, site_id=site_id, employee=Employee(employee_id, employee_id, date(2020, 1, 1), None, False))
        durable_inputs.update_membership(
            conn, coordinator_id=COORD, site_id=site_id,
            membership=SiteMembership(employee_id, site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
        )
        durable_inputs.set_target_hours(conn, coordinator_id=COORD, site_id=site_id, employee_id=employee_id, month=month, target_hours=80)
    days_in_month = _calendar.monthrange(month.year, month.month)[1]
    for day in range(1, days_in_month + 1):
        durable_inputs.set_calendar_day(conn, coordinator_id=COORD, site_id=site_id, day=CalendarDay(date=date(month.year, month.month, day), holiday=False))


def _print_settings(site_id: str) -> SitePrintSettings:
    return SitePrintSettings(
        site_id=site_id, company_print_name="ELNATH DEMO", site_print_name=site_id, base_regime="12h",
        work_code_intervals={
            "D1": WorkCodeInterval("06:00", "18:00", False), "D2": None, "D3": None, "D4": None, "D5": None,
            "N1": WorkCodeInterval("18:00", "06:00", True), "N2": None, "N3": None, "N4": None, "N5": None,
        },
        reserve_hours={k: None for k in ("U3", "U4", "U5", "C3", "C4", "C5")},
    )


# --- Scenario 1: H12 catalog through plan -> select -> PDF -> analytics -> restart --


def test_scenario_1_h12_plan_to_pdf_to_analytics_to_restart(tmp_path: Path) -> None:
    site_id, profile_id, month = "SITE-V1", "PROF-V1", date(2026, 11, 1)
    employees = ("EMP-V1-1", "EMP-V1-2")
    db_path = tmp_path / "rota.db"
    conn = store.open_store(db_path)
    _bootstrap(conn, site_id=site_id, profile_id=profile_id, profile=_profile_h12(profile_id), employees=employees, month=month)
    save_site_print_settings(conn, _print_settings(site_id))

    result = plan_ops.plan_month(conn, site_id=site_id, month=month, coordinator_id=COORD, effective_from=month)
    assert result.status == "FEASIBLE"
    version = plan_ops.select_candidate(conn, site_id=site_id, month=month, candidate=result.candidates[0], coordinator_id=COORD)

    export = generate_schedule_pdf(conn, site_id=site_id, month=month, period_label="Listopad 2026")
    assert isinstance(export, ExportReady) and export.pdf_bytes

    analytics = analytics_for_site_month(conn, site_id=site_id, month=month)
    assert {r.employee_id for r in analytics.rows} == set(employees)

    state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
    acknowledged = {d.deviation_id for d in state.deviations}
    final_version = lifecycle_ops.finalize(conn, site_id=site_id, month=month, coordinator_id=COORD, acknowledged_deviation_ids=acknowledged)
    assert final_version.status.value.startswith("FINAL")

    before = open_month.open_month(conn, site_id=site_id, month=month)
    conn.close()
    reopened = store.open_store(db_path)
    after = open_month.open_month(reopened, site_id=site_id, month=month)
    assert after == before
    assert after.current_version.version_id == version.version_id
    reopened.close()


# --- Scenario 2: H24 catalog through plan -> select -> finalize (can_work_24h gating end to end) --


def test_scenario_2_h24_catalog_can_work_24h_gating_end_to_end(tmp_path: Path) -> None:
    site_id, profile_id, month = "SITE-V2", "PROF-V2", date(2026, 11, 1)
    employees = ("EMP-V2-OK", "EMP-V2-NO")
    db_path = tmp_path / "rota.db"
    conn = store.open_store(db_path)
    _bootstrap(conn, site_id=site_id, profile_id=profile_id, profile=_profile_h24(profile_id), employees=employees, month=month)
    durable_inputs.update_membership(
        conn, coordinator_id=COORD, site_id=site_id,
        membership=SiteMembership("EMP-V2-NO", site_id, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT, can_work_24h=False),
    )

    result = plan_ops.plan_month(conn, site_id=site_id, month=month, coordinator_id=COORD, effective_from=month)
    assert result.status == "FEASIBLE"
    candidate = result.candidates[0]
    # T012: a 24h catalog entry always expands into two 12h D/N components sharing
    # one work_period_template_id ("...-shift0-..." here, the profile's first entry) --
    # never one 24h Assignment -- so H24-catalog primaries are identified by that id, not duration.
    primaries = [a for a in candidate if a.role == AssignmentRole.PRIMARY]
    h24_primaries = [a for a in primaries if "-shift0-" in (a.work_period_id or "")]
    assert h24_primaries and all(a.employee_id != "EMP-V2-NO" for a in h24_primaries)

    version = plan_ops.select_candidate(conn, site_id=site_id, month=month, candidate=candidate, coordinator_id=COORD)
    state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
    acknowledged = {d.deviation_id for d in state.deviations}
    final_version = lifecycle_ops.finalize(conn, site_id=site_id, month=month, coordinator_id=COORD, acknowledged_deviation_ids=acknowledged)
    assert final_version.status.value.startswith("FINAL")
    assert final_version.version_id == version.version_id


# --- Scenario 3: manual zero-gap H12+H12 REST override -> ledger -> REPLAN --


def test_scenario_3_manual_zero_gap_rest_override_replan_ledger(tmp_path: Path) -> None:
    site_id, profile_id, month = "SITE-V3", "PROF-V3", date(2026, 11, 1)
    employees = ("EMP-V3-A", "EMP-V3-B")
    db_path = tmp_path / "rota.db"
    conn = store.open_store(db_path)
    _bootstrap(conn, site_id=site_id, profile_id=profile_id, profile=_profile_h12_dn(profile_id, rest_hours=0), employees=employees, month=month)

    result = plan_ops.plan_month(conn, site_id=site_id, month=month, coordinator_id=COORD, effective_from=month)
    assert result.status == "FEASIBLE"
    candidate = result.candidates[0]
    plan_ops.select_candidate(conn, site_id=site_id, month=month, candidate=candidate, coordinator_id=COORD)

    day1_primary = next(a for a in candidate if a.role == AssignmentRole.PRIMARY and a.start_datetime.date() == date(2026, 11, 1))
    day1_n = next(
        a for a in candidate if a.role == AssignmentRole.PRIMARY and a.start_datetime == day1_primary.end_datetime
    )
    from dataclasses import replace as _replace
    reassigned = _replace(day1_n, employee_id=day1_primary.employee_id)

    v2 = manual_edit.apply_manual_correction(
        conn, site_id=site_id, month=month, coordinator_id=COORD, effective_from=month, upsert_assignments=[reassigned],
    )
    snapshot_state, _ = assemble_planning_state(conn, site_id=site_id, month=month)
    rest_devs = [d for d in snapshot_state.deviations if d.source_reference == "REST-01"]
    assert rest_devs, "T022 zero-gap H12+H12 must surface as a REST-01 Deviation"

    override_key = f"REST-OVERRIDE:{v2.version_id}"
    override_history = memory_read.decision_chain_for_rule_family(conn, site_id=site_id, rule_id=override_key)
    assert override_history, "manual correction across the new T022 zero-gap shape must still write REST_OVERRIDE_RECORD (PH-1)"

    replan_result = lifecycle_ops.revalidate(conn, site_id=site_id, month=month, coordinator_id=COORD)
    assert replan_result.version_id == v2.version_id

    history = memory_read.material_action_history(conn, site_id=site_id)
    action_kinds = {a.action_kind for a in history}
    assert "SCHEDULE_CANDIDATE_SELECTED" in {k.value if hasattr(k, "value") else k for k in action_kinds}


# --- Scenario 4: two-Site isolation with one shared employee --


def test_scenario_4_two_site_isolation_shared_employee(tmp_path: Path) -> None:
    site_a, site_b = "SITE-V4A", "SITE-V4B"
    profile_a, profile_b = "PROF-V4A", "PROF-V4B"
    month = date(2026, 11, 1)
    shared_employee = "EMP-V4-SHARED"
    only_a = "EMP-V4-A-ONLY"
    only_b = "EMP-V4-B-ONLY"
    db_path = tmp_path / "rota.db"
    conn = store.open_store(db_path)

    _bootstrap(conn, site_id=site_a, profile_id=profile_a, profile=_profile_h12(profile_a), employees=(shared_employee, only_a), month=month)
    _bootstrap(conn, site_id=site_b, profile_id=profile_b, profile=_profile_h12(profile_b), employees=(shared_employee, only_b), month=month)
    save_site_print_settings(conn, _print_settings(site_a))
    save_site_print_settings(conn, _print_settings(site_b))

    result_a = plan_ops.plan_month(conn, site_id=site_a, month=month, coordinator_id=COORD, effective_from=month)
    assert result_a.status == "FEASIBLE"
    version_a = plan_ops.select_candidate(conn, site_id=site_a, month=month, candidate=result_a.candidates[0], coordinator_id=COORD)

    result_b = plan_ops.plan_month(conn, site_id=site_b, month=month, coordinator_id=COORD, effective_from=month)
    assert result_b.status == "FEASIBLE"
    plan_ops.select_candidate(conn, site_id=site_b, month=month, candidate=result_b.candidates[0], coordinator_id=COORD)

    view_a = open_month.open_month(conn, site_id=site_a, month=month)
    view_b = open_month.open_month(conn, site_id=site_b, month=month)
    assert only_b not in {e.employee_id for e in view_a.employees}
    assert only_a not in {e.employee_id for e in view_b.employees}

    analytics_a = analytics_for_site_month(conn, site_id=site_a, month=month)
    analytics_b = analytics_for_site_month(conn, site_id=site_b, month=month)
    assert only_b not in {r.employee_id for r in analytics_a.rows}
    assert only_a not in {r.employee_id for r in analytics_b.rows}

    replan_a = lifecycle_ops.revalidate(conn, site_id=site_a, month=month, coordinator_id=COORD)
    assert replan_a.version_id == version_a.version_id
    view_b_after = open_month.open_month(conn, site_id=site_b, month=month)
    assert view_b_after.current_version.version_id == view_b.current_version.version_id, "REPLAN-triggering revalidate on Site A must not move Site B's current pointer"

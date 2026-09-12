"""ROTA-T011-E (tasks/ROTA-T011-E/brief.md) TEST 2: a real HARD collision
stops PLAN, and there is no silent way around it -- every path to FEASIBLE
is either an explicit input change, an explicit rule correction in the
Decision Ledger, or a manual write whose HARD violation stays visible as a
Deviation. No import of rota.persistence anywhere in this file (checked
mechanically by the auditor; DEPENDENCY BOUNDARY makes this a FAIL
condition, not a style preference). The one exception the brief allows is
rota.planning.validator.validate, used as the independent second opinion on
a candidate exactly as the existing contract already does.
"""
from __future__ import annotations

import calendar as _calendar
import importlib
import inspect
import pkgutil
from datetime import date, time
from pathlib import Path

import pytest

import rota.application as application_pkg
from rota.application import bootstrap, durable_inputs, memory_read, plan_ops, rule_decisions, store
from rota.application.assembler import assemble_planning_state, generate_profile_demands
from rota.application.errors import CandidateRejected
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
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftKind,
    Site,
    SiteMembership,
    SiteProfile,
    StandardShift,
    SitePlanningRegime,
)
from rota.planning.validator import validate

# DEPENDENCY BOUNDARY: NewRuleContent is not imported from rota.site_memory_types
# directly -- rota.application.rule_decisions already has it in its own
# namespace (it accepts the type in its public function), so this stays
# within the application-layer surface this file is allowed to call.
NewRuleContent = rule_decisions.NewRuleContent

COORD = "COORD-E2"
SITE_ID = "SITE-E2"
PROFILE_ID = "PROFILE-E2"
EMP1 = "EMP-E2-1"
EMP2 = "EMP-E2-2"
MONTH = date(2026, 11, 1)
RULE_ID = "RULE-E2-D-BAN"
BLOCKED_ISO_WEEKDAY = 1  # Monday
FORBIDDEN_RULE_KIND = "EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS"


def _profile() -> SiteProfile:
    return SiteProfile(
        profile_id=PROFILE_ID, display_name="E2 Profile", active=True,
        standard_shifts=[StandardShift(ShiftKind.D, time(6, 0), time(18, 0), False, 1)],
        day_only_blocks_n=False, external_support_enabled=False,
        training_s_enabled=False, training_s_weekdays_only=False,
        training_s_default_readiness_threshold=1, rolling_7d_decision_threshold_hours=999,
    )


def _first_date_with_weekday(month: date, iso_weekday: int) -> date:
    days = _calendar.monthrange(month.year, month.month)[1]
    return next(
        date(month.year, month.month, day) for day in range(1, days + 1)
        if date(month.year, month.month, day).isoweekday() == iso_weekday
    )


BLOCKED_DATE = _first_date_with_weekday(MONTH, BLOCKED_ISO_WEEKDAY)
BLOCKED_DEMAND_ID = f"{BLOCKED_DATE.isoformat()}-{ShiftKind.D.value}"


def _bootstrap_and_fill(conn, employee_ids: tuple[str, ...]) -> None:
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=COORD, site_id=SITE_ID,
        coordinator=Coordinator(COORD, "Coord E2", True), site_profile=_profile(),
        site=Site(SITE_ID, PROFILE_ID, "Site E2", True, planning_regime=SitePlanningRegime.ORDINARY),
        association=CoordinatorSiteAssociation(COORD, SITE_ID, True),
    )
    for employee_id in employee_ids:
        durable_inputs.update_employee(
            conn, coordinator_id=COORD, site_id=SITE_ID,
            employee=Employee(employee_id, employee_id, date(2020, 1, 1), None, False),
        )
        durable_inputs.update_membership(
            conn, coordinator_id=COORD, site_id=SITE_ID,
            membership=SiteMembership(
                employee_id, SITE_ID, MembershipKind.LOCAL, True,
                ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
            ),
        )
    days = _calendar.monthrange(MONTH.year, MONTH.month)[1]
    for day in range(1, days + 1):
        durable_inputs.set_calendar_day(
            conn, coordinator_id=COORD, site_id=SITE_ID,
            day=CalendarDay(date=date(MONTH.year, MONTH.month, day), holiday=False),
        )


def _record_forbidding_rule(conn):
    return rule_decisions.record_structured_rule_decision(
        conn, coordinator_id=COORD, site_id=SITE_ID, rule_id=RULE_ID,
        statement="EMP-E2-1 nie pracuje na D w poniedzialki.", effective_from=MONTH, rel=None,
        rule_content=NewRuleContent(
            category=RuleCategory.LOCAL_RULE, rule_kind=FORBIDDEN_RULE_KIND,
            structured_parameters={"employee_id": EMP1, "weekdays": [BLOCKED_ISO_WEEKDAY], "forbidden_shift_kinds": ["D"]},
            enforcement=RuleEnforcement.HARD, resolution_status=RuleResolution.RESOLVED,
            effective_to=None, description=None, source=None, reason=None,
        ),
    )


def _assignment(demand, employee_id: str) -> Assignment:
    return Assignment(
        f"ASG-{demand.demand_id}", "", employee_id, demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None,
    )


def test_1_engine_stops_and_returns_decision_required_not_silent_feasible(tmp_path: Path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap_and_fill(conn, (EMP1,))  # EMP1 is the ONLY eligible employee
    _record_forbidding_rule(conn)

    result = plan_ops.plan_month(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH)

    assert result.status == "DECISION_REQUIRED"
    assert result.candidates == []  # never a hidden, HARD-violating grafik
    assert result.decision_payload is not None
    assert BLOCKED_DEMAND_ID in {d.demand_id for d in result.decision_payload.blocking_shift_demands}
    assert any(b.employee_id == EMP1 for b in result.decision_payload.blockers)


def test_4_route_b_decision_ledger_correction_unblocks_feasible(tmp_path: Path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    _bootstrap_and_fill(conn, (EMP1,))
    _record_forbidding_rule(conn)
    blocked = plan_ops.plan_month(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert blocked.status == "DECISION_REQUIRED"

    rule_decisions.record_structured_rule_decision(
        conn, coordinator_id=COORD, site_id=SITE_ID, rule_id=RULE_ID,
        statement="Wycofanie zakazu D w poniedzialki dla EMP-E2-1.", effective_from=MONTH, rel="rejects",
        rule_content=None,
    )
    # ROTA-T058 (ARCHITECT_RULING 2026-09-08, brief 2.5): once the SiteRule
    # is withdrawn, EMP1 alone would cover the whole month solo again --
    # that now genuinely trips the new HARD max-two-consecutive-PRIMARY-
    # shifts rule, unrelated to what this test isolates (a rejected
    # Decision Ledger entry unblocking FEASIBLE). Added only here, AFTER
    # the blocked assertion above, so the first plan_month call above still
    # exercises EMP1-alone-blocked-by-SiteRule untouched.
    durable_inputs.update_employee(
        conn, coordinator_id=COORD, site_id=SITE_ID, employee=Employee(EMP2, EMP2, date(2020, 1, 1), None, False),
    )
    durable_inputs.update_membership(
        conn, coordinator_id=COORD, site_id=SITE_ID,
        membership=SiteMembership(
            EMP2, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT,
        ),
    )

    unblocked = plan_ops.plan_month(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH)
    assert unblocked.status == "FEASIBLE"
    assert unblocked.candidates

    chain = memory_read.decision_chain_for_rule_family(conn, site_id=SITE_ID, rule_id=RULE_ID)
    assert len(chain) == 2
    assert chain[-1].rel == "rejects"


def test_5_select_candidate_rejects_a_hard_violating_candidate(tmp_path: Path) -> None:
    conn = store.open_store(tmp_path / "rota.db")
    # ROTA-T058 (ARCHITECT_RULING 2026-09-08, brief 2.5): the original
    # candidate put EMP1 on EVERY demand of the month, which now also trips
    # the independent new HARD max-two-consecutive-PRIMARY-shifts rule --
    # genuinely true, but not what this test isolates. EMP1/EMP2 alternate
    # daily below (never more than 1 consecutive day each), with EMP1
    # specifically kept on BLOCKED_DEMAND_ID so the tested SiteRule
    # violation still occurs; EMP2 must exist as a real eligible membership
    # or its presence in the candidate would itself trip MEMBERSHIP-01,
    # an unrelated HARD violation that would break the isolation this test
    # needs just as much as the new HARD rule would.
    _bootstrap_and_fill(conn, (EMP1, EMP2))
    decision = _record_forbidding_rule(conn)
    plan_ops.plan_month(conn, site_id=SITE_ID, month=MONTH, coordinator_id=COORD, effective_from=MONTH)

    # Full coverage everywhere -- alternating EMP1/EMP2, with EMP1 on the
    # one blocked day -- so the ONLY HARD violation possible is the tested
    # SiteRule; a candidate that also leaves COVERAGE-01 gaps would get
    # rejected for an independent reason and would not isolate this rule.
    demands = generate_profile_demands(_profile(), MONTH)
    hard_violating_candidate = [
        _assignment(demand, EMP1 if (demand.demand_id == BLOCKED_DEMAND_ID or index % 2 == 1) else EMP2)
        for index, demand in enumerate(demands)
    ]

    state, _warnings = assemble_planning_state(conn, site_id=SITE_ID, month=MONTH)
    report = validate(state, hard_violating_candidate)
    assert report.hard_pass is False
    assert {vd.rule for vd in report.violation_details} == {decision.rule_version_id}

    with pytest.raises(CandidateRejected):
        plan_ops.select_candidate(
            conn, site_id=SITE_ID, month=MONTH, candidate=hard_violating_candidate, coordinator_id=COORD,
        )

    # Equivalence check: once the SAME rule is explicitly rejected in the
    # Decision Ledger, the SAME candidate becomes hard_pass=True -- the
    # rejection above was attributable to this rule, not to some other
    # independent HARD source.
    rule_decisions.record_structured_rule_decision(
        conn, coordinator_id=COORD, site_id=SITE_ID, rule_id=RULE_ID,
        statement="Wycofanie zakazu D w poniedzialki dla EMP-E2-1 (rownowaznosc E-R3-2).",
        effective_from=MONTH, rel="rejects", rule_content=None,
    )
    state_after, _warnings = assemble_planning_state(conn, site_id=SITE_ID, month=MONTH)
    report_after = validate(state_after, hard_violating_candidate)
    assert report_after.hard_pass is True


def test_6_no_public_application_function_accepts_a_hard_override_parameter() -> None:
    suspicious_tokens = ("ignore", "disable", "bypass", "skip_validation", "force_hard", "override_hard")
    offenders = []
    for module_info in pkgutil.iter_modules(application_pkg.__path__, prefix="rota.application."):
        module = importlib.import_module(module_info.name)
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if func.__module__ != module.__name__ or name.startswith("_"):
                continue
            for param_name in inspect.signature(func).parameters:
                if any(token in param_name.lower() for token in suspicious_tokens):
                    offenders.append(f"{module.__name__}.{name}({param_name})")
    assert offenders == []

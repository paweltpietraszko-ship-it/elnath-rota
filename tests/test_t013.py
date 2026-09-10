"""ROTA-T013: coordinator-facing DECISION_REQUIRED guidance.

arch/FROZEN_ADDENDUM_DECISION_REQUIRED_COORDINATOR_COMMUNICATION_01.md +
tasks/ROTA-T013/brief.md. Covers decision_guidance.py's pure translation
(sections C/D/F/G/J/K) and engine.py's four terminal autonomy-boundary
paths end to end (sections A/H/I).
"""
from __future__ import annotations

import calendar as calendar_module
from datetime import date, datetime

import rota.planning.engine as engine_module
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
    CalendarDay,
    Employee,
    MembershipKind,
    ReadinessSource,
    ReadinessState,
    RuleCategory,
    RuleEnforcement,
    RuleResolution,
    ShiftDemand,
    SiteMembership,
    SiteRuleVersion,
)
from rota.planning.decision_guidance import build_unblocking_options, render_coordinator_blockers
from rota.planning.engine import plan
from rota.planning.engine_types import Blocker, DecisionRequiredPayload
from rota.planning.site_rules import (
    EMPLOYEE_ALLOWED_SHIFT_KINDS,
    EMPLOYEE_DAY_ONLY_N_EXCEPTION,
)
from rota.planning.solver import solve
from rota.planning.state import SiteRuleApplicability
from tests.support.minimal_state import SITE_ID, base_state

MONTH = date(2026, 10, 1)


def _texts(options) -> list[str]:
    """ROTA-T062: unblocking_options is now a list[UnblockingOption]
    (text + stable navigation target), not bare strings -- this file's
    assertions only care about the rendered text, same as before."""
    return [o.text for o in options]


def _employee(employee_id: str, display_name: str | None = None, *, day_only: bool = False) -> Employee:
    return Employee(employee_id, display_name or employee_id, date(2020, 1, 1), None, day_only)


def _membership(employee_id: str, **overrides) -> SiteMembership:
    return SiteMembership(
        employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY,
        ReadinessSource.DEFAULT, **overrides,
    )


def _d_demand(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 5, 0), datetime(2026, 10, day, 17, 0), 1)


def _n_demand(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 17, 0), datetime(2026, 10, day + 1, 5, 0), 1)


def _full_month_calendar(month: date = MONTH) -> tuple[CalendarDay, ...]:
    last_day = calendar_module.monthrange(month.year, month.month)[1]
    return tuple(CalendarDay(date(month.year, month.month, day), False) for day in range(1, last_day + 1))


def _site_rule(rule_version_id: str, *, employee_id: str = "A", description: str | None = None) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id, f"rule-{rule_version_id}", SITE_ID, RuleCategory.LOCAL_RULE,
        EMPLOYEE_ALLOWED_SHIFT_KINDS, {"employee_id": employee_id, "allowed_shift_kinds": ["N"]},
        RuleEnforcement.HARD, RuleResolution.RESOLVED, MONTH, None,
        datetime(2026, 9, 1), "COORD", None, description, None, None,
    )


def _exception_rule(rule_version_id: str, employee_id: str) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id, f"rule-{rule_version_id}", SITE_ID, RuleCategory.CONFIRMED_EXCEPTION,
        EMPLOYEE_DAY_ONLY_N_EXCEPTION, {"employee_id": employee_id},
        RuleEnforcement.HARD, RuleResolution.RESOLVED, MONTH, date(2026, 10, 31),
        datetime(2026, 9, 1), "COORD", None, None, None, None,
    )


def _applicability(rule: SiteRuleVersion) -> SiteRuleApplicability:
    return SiteRuleApplicability(rule.rule_version_id, rule.effective_from, rule.effective_to)


# M1 --------------------------------------------------------------------


def test_m1_exact_built_in_condition_mapping():
    state = base_state(employees=(_employee("A"),))
    mapping = {
        "UNAVAILABLE-01": "Koliduje z ustawieniem: Ogólna dostępność",
        "DAY_ONLY-01": "Koliduje z ustawieniem: Nocka",
        "SICK_LEAVE-01": "Koliduje z zapisem: Chorobowe",
        "LEAVE_GRANTED-01": "Koliduje z zapisem: Urlop",
        "REST-01": "Koliduje z odpoczynkiem dobowym",
        "LOAD-01": "Koliduje z tygodniowym czasem pracy",
        "EXTERNAL-01": "Wsparcie zewnętrzne",
        "EXTERNAL_SUPPORT_DISABLED": "Wsparcie zewnętrzne",
        "SHIFT-24-01": "Koliduje z ustawieniem: 24",
        "DAY_SHIFT_OFF-01": "Koliduje z zapisem: Wolne w dzień",
    }
    for raw, expected in mapping.items():
        assert render_coordinator_blockers(state, [Blocker("A", raw)]) == [Blocker("A", expected)]


# M2/M3 -----------------------------------------------------------------


def test_m2_m3_membership_conditions_hidden():
    state = base_state(employees=(_employee("A"),))
    for raw in ("MEMBERSHIP_DISABLED", "MEMBERSHIP-01"):
        assert render_coordinator_blockers(state, [Blocker("A", raw)]) == []
        options = build_unblocking_options(state, [Blocker("A", raw)], None)
        assert _texts(options) == ["Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach."]


# M4 ----------------------------------------------------------------------


def test_m4_emp02_has_no_dedicated_owner():
    """EMP-02 was retired by T016; T013 does not resurrect it as a
    coordinator-facing concept -- it is neither hidden nor specially worded."""
    state = base_state(employees=(_employee("A"),))
    assert render_coordinator_blockers(state, [Blocker("A", "EMP-02")]) == [Blocker("A", "EMP-02")]


# M5 ----------------------------------------------------------------------


def test_m5_day_shift_off_has_polish_text_and_generates_no_action():
    # T048: DAY_SHIFT_OFF-01 used to be the one condition left untranslated;
    # it now has Polish text like every sibling condition, but still has no
    # _ACTION_TEMPLATES entry (a separate, unrequested gap -- see brief.md).
    state = base_state(employees=(_employee("A"),))
    assert render_coordinator_blockers(state, [Blocker("A", "DAY_SHIFT_OFF-01")]) == [Blocker("A", "Koliduje z zapisem: Wolne w dzień")]
    options = build_unblocking_options(state, [Blocker("A", "DAY_SHIFT_OFF-01")], None)
    assert _texts(options) == ["Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach."]


# M6 ----------------------------------------------------------------------


def test_m6_shift_24_uses_24_naming():
    state = base_state(employees=(_employee("A"),))
    assert render_coordinator_blockers(state, [Blocker("A", "SHIFT-24-01")]) == [Blocker("A", "Koliduje z ustawieniem: 24")]
    assert _texts(build_unblocking_options(state, [Blocker("A", "SHIFT-24-01")], None)) == ["Zmień 24: A"]


# M7/M8 ---------------------------------------------------------------------


def test_m7_site_rule_description_replaces_version_id():
    rule = _site_rule("RV-1", description="  Nie pracuje w weekendy  ")
    state = base_state(employees=(_employee("A"),), site_rules=(rule,))
    rendered = render_coordinator_blockers(state, [Blocker("A", "RV-1")])
    assert rendered == [Blocker("A", "Nie pracuje w weekendy")]


def test_m8_blank_site_rule_description_uses_generic_text():
    for description in (None, "", "   "):
        rule = _site_rule("RV-2", description=description)
        state = base_state(employees=(_employee("A"),), site_rules=(rule,))
        assert render_coordinator_blockers(state, [Blocker("A", "RV-2")]) == [Blocker("A", "Koliduje z zapisaną regułą obiektu")]


# M9/M10/I.1 -- unassignable path --------------------------------------------


def test_m9_m10_i1_unassignable_options_are_evidence_backed():
    demand = _d_demand("D1", 6)
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 6), date(2026, 10, 6), True, None, None)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),), shift_demands=(demand,),
        availability_records=(sick,), calendar_days=_full_month_calendar(),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.blocking_shift_demands
    assert all(b.condition == "Koliduje z zapisem: Chorobowe" for b in result.decision_payload.blockers)
    assert _texts(result.decision_payload.unblocking_options) == ["Ręczna korekta mimo zapisu Chorobowe zgodnie z kontraktem: A"]


# M11/M12 -- external support -------------------------------------------------


def test_m11_external_blocker_gets_human_text_and_dynamic_option():
    demand = _d_demand("D1", 6)
    employee = _employee("A", "Anna Zewnętrzna")
    membership = SiteMembership("A", SITE_ID, MembershipKind.EXTERNAL_SUPPORT, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)
    state = base_state(employees=(employee,), memberships=(membership,), shift_demands=(demand,))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Wsparcie zewnętrzne" for b in result.decision_payload.blockers)
    assert _texts(result.decision_payload.unblocking_options) == ["Skonfiguruj Wsparcie zewnętrzne: Anna Zewnętrzna"]
    assert not any("X/Y" in o for o in _texts(result.decision_payload.unblocking_options))


def test_m12_no_external_blocker_means_no_external_option():
    from dataclasses import replace as _replace

    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(_membership("A"),), shift_demands=(_d_demand("D1", 6),))
    state = _replace(state, profile=_replace(state.profile, rolling_7d_decision_threshold_hours=11))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert not any("Wsparcie zewnętrzne" in o for o in _texts(result.decision_payload.unblocking_options))
    assert not any(b.condition == "Wsparcie zewnętrzne" for b in result.decision_payload.blockers)


# M13/H -- final DAY_ONLY --------------------------------------------------


def test_m13_h_final_day_only_gives_nocka_option_only_after_fallback_exhausted(monkeypatch):
    demand = _n_demand("N1", 6)
    employee = _employee("A", day_only=True)
    calls = []
    real_solve = solve

    def _tracking_solve(state, **kwargs):
        calls.append((kwargs.get("allow_day_only_n_fallback", False), kwargs.get("allow_emergency_24h", False)))
        return real_solve(state, **kwargs)

    monkeypatch.setattr(engine_module, "solve", _tracking_solve)
    state = base_state(employees=(employee,), memberships=(_membership("A"),), shift_demands=(demand,))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Koliduje z ustawieniem: Nocka" for b in result.decision_payload.blockers)
    assert "Zmień Nocka: A" in _texts(result.decision_payload.unblocking_options)
    # H: T013 does not alter T018's call order/flags. Stage 3's shortage is
    # terminal (no exception ever authorized this employee), so Stage 4 is
    # never reached -- unchanged T018 semantics.
    assert calls == [(False, False), (True, False), (True, True)]


# M14/H -- intermediate DAY_ONLY shortage then Stage2 FEASIBLE --------------


def test_m14_h_intermediate_day_only_shortage_then_stage2_feasible_gives_no_decision():
    demand = _n_demand("N1", 6)
    employee = _employee("A", day_only=True)
    rule = _exception_rule("RV-EXC", "A")
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), shift_demands=(demand,),
        site_rules=(rule,), site_rule_applicability=(_applicability(rule),),
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.decision_payload is None


# M15/I.2 -- REST conflict --------------------------------------------------


def test_m15_i2_rest_conflict_gives_only_relevant_rest_guidance():
    demand_n = ShiftDemand("N1", "test-v1", datetime(2026, 10, 1, 17, 0), datetime(2026, 10, 2, 5, 0), 1)
    demand_d2 = ShiftDemand("D2", "test-v1", datetime(2026, 10, 2, 5, 0), datetime(2026, 10, 2, 17, 0), 1)
    employee = Employee("A", "Anna", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(_membership("A"),), shift_demands=(demand_n, demand_d2))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Koliduje z odpoczynkiem dobowym" for b in result.decision_payload.blockers)
    assert _texts(result.decision_payload.unblocking_options) == ["Ręczna korekta z uwzględnieniem odpoczynku dobowego zgodnie z kontraktem: Anna"]
    assert not any("Wsparcie zewnętrzne" in o or "Nocka" in o for o in _texts(result.decision_payload.unblocking_options))


# M16/I.3 -- frozen conflict --------------------------------------------------


def test_m16_i3_frozen_conflict_gives_unfreeze_option_and_translated_blockers():
    demand_d = ShiftDemand("D1", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)
    employee = Employee("A", "Anna", date(2026, 9, 1), None, False)
    frozen = Assignment(
        "frozen-1", "test-v1", "A", demand_d.start_datetime, demand_d.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand_d.demand_id, None,
    )
    unavailable = AvailabilityRecord("u1", "u1v1", "A", AvailabilityKind.UNAVAILABLE_24H, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), shift_demands=(demand_d,),
        existing_assignments=(frozen,), availability_records=(unavailable,),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert any(b.condition == "Koliduje z ustawieniem: Ogólna dostępność" for b in result.decision_payload.blockers)
    assert "Odmroź zapisane przypisania i uruchom planowanie ponownie" in _texts(result.decision_payload.unblocking_options)


# M17/I.4 -- LOAD only --------------------------------------------------------


def test_m17_i4_load_only_gives_load_option_and_human_condition():
    from dataclasses import replace

    employee = Employee("A", "Anna", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(_membership("A"),), shift_demands=(_d_demand("D1", 1),))
    state = replace(state, profile=replace(state.profile, rolling_7d_decision_threshold_hours=11))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.decision_payload.load_blocker is not None
    assert all(b.condition == "Koliduje z tygodniowym czasem pracy" for b in result.decision_payload.blockers)
    assert "Dodaj pracownika do obsady i zaplanuj ponownie" in _texts(result.decision_payload.unblocking_options)
    assert "Odmroź zapisane przypisania i uruchom planowanie ponownie" not in _texts(result.decision_payload.unblocking_options)


# M18 -- frozen + LOAD together ----------------------------------------------


def test_m18_frozen_and_load_gives_both_option_families():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    demand_d = ShiftDemand("2026-10-01-D", "test-v1", datetime(2026, 10, 1, 5, 0), datetime(2026, 10, 1, 17, 0), 1)
    boundary = tuple(
        Assignment(f"f{d}", "test-v1", "A", datetime(2026, 9, d, 5, 0), datetime(2026, 9, d, 17, 0),
                   AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, None, None)
        for d in range(25, 31)
    )
    frozen_demand = Assignment(
        "f-demand", "test-v1", "A", demand_d.start_datetime, demand_d.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, True, demand_d.demand_id, None,
    )
    sick = AvailabilityRecord("s1", "s1v1", "A", AvailabilityKind.SICK_LEAVE, date(2026, 10, 1), date(2026, 10, 1), True, None, None)
    state = base_state(
        employees=(employee,), memberships=(_membership("A"),), shift_demands=(demand_d,),
        existing_assignments=boundary + (frozen_demand,), availability_records=(sick,),
        calendar_days=_full_month_calendar(),
    )
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    options = _texts(result.decision_payload.unblocking_options)
    assert "Odmroź zapisane przypisania i uruchom planowanie ponownie" in options
    assert "Dodaj pracownika do obsady i zaplanuj ponownie" in options
    conditions = {b.condition for b in result.decision_payload.blockers}
    assert "Koliduje z tygodniowym czasem pracy" in conditions
    assert "Koliduje z zapisem: Chorobowe" in conditions


# M19 -- hidden/internal-only diagnosis --------------------------------------


def test_m19_hidden_only_diagnosis_gives_exact_no_solution_fallback():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(), shift_demands=(_d_demand("D1", 6),))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert _texts(result.decision_payload.unblocking_options) == ["Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach."]


# M20/K -- determinism / dedup -----------------------------------------------


def test_m20_k_deterministic_order_and_dedup_independent_of_input_order():
    state = base_state(employees=(_employee("A", "Zofia"), _employee("B", "Adam")))
    forward = [Blocker("A", "REST-01"), Blocker("B", "REST-01"), Blocker("A", "REST-01")]
    reversed_ = [Blocker("A", "REST-01"), Blocker("B", "REST-01")][::-1] + [Blocker("A", "REST-01")]
    assert render_coordinator_blockers(state, forward) == render_coordinator_blockers(state, reversed_)
    assert len(render_coordinator_blockers(state, forward)) == 2
    forward_options = build_unblocking_options(state, forward, None)
    reversed_options = build_unblocking_options(state, reversed_, None)
    assert forward_options == reversed_options
    assert _texts(forward_options) == ["Ręczna korekta z uwzględnieniem odpoczynku dobowego zgodnie z kontraktem: Adam, Zofia"]


def test_m20_multiple_site_rule_versions_same_description_give_one_action():
    rule_a = _site_rule("RV-A", description="Zakaz nocek")
    rule_b = _site_rule("RV-B", description="Zakaz nocek")
    state = base_state(employees=(_employee("A"),), site_rules=(rule_a, rule_b))
    options = build_unblocking_options(state, [Blocker("A", "RV-A"), Blocker("A", "RV-B")], None)
    assert _texts(options) == ["Zmień zapisaną regułę: Zakaz nocek"]
    # ROTA-T062 (brief section 4 point 9, R1 audit finding): this option
    # used to get target="obiekt" -- verified against the real "Obiekt" tab
    # (ControlPanel.tsx: shift catalog + print settings only, no editor for
    # an arbitrary saved SiteRuleVersion) that this is a fake button
    # pointing nowhere useful. An unrecognized/general rule with no real
    # editor stays information only.
    assert options[0].target is None


def test_m20_rule_version_id_never_appears_in_coordinator_text():
    rule = _site_rule("RV-SECRET-ID", description=None)
    state = base_state(employees=(_employee("A"),), site_rules=(rule,))
    blockers = render_coordinator_blockers(state, [Blocker("A", "RV-SECRET-ID")])
    options = build_unblocking_options(state, [Blocker("A", "RV-SECRET-ID")], None)
    assert "RV-SECRET-ID" not in blockers[0].condition
    assert not any("RV-SECRET-ID" in o for o in _texts(options))


# M21/M22/M23 -- payload shape / status mapping unchanged -------------------


def test_m21_decision_payload_is_existing_dataclass_shape():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(), shift_demands=(_d_demand("D1", 6),))
    result = plan(state)
    assert isinstance(result.decision_payload, DecisionRequiredPayload)


def test_m22_feasible_payload_unchanged():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(_membership("A"),), shift_demands=(_d_demand("D1", 6),))
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert result.decision_payload is None


def test_m23_technical_error_mapping_unchanged():
    bad_demand = ShiftDemand("bad-1", "test-v1", datetime(2026, 10, 1, 8, 0), datetime(2026, 10, 1, 16, 0), 1)
    state = base_state(shift_demands=(bad_demand,))
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"
    assert result.decision_payload is None


# L -- no technical attempt trace ---------------------------------------


def test_l_no_stage_or_solver_internals_leak_into_coordinator_payload():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(), shift_demands=(_d_demand("D1", 6),))
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    forbidden = ("Stage 1", "Stage 2", "Stage 3", "Stage 4", "allow_day_only_n_fallback", "allow_emergency_24h", "uncapped")
    haystack = " ".join(_texts(result.decision_payload.unblocking_options)) + " ".join(b.condition for b in result.decision_payload.blockers)
    assert not any(term in haystack for term in forbidden)


if __name__ == "__main__":
    print("test_t013 module OK")

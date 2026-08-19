"""ROTA-T017: multi-variant FEASIBLE planning.

arch/FROZEN_ADDENDUM_MULTI_VARIANT_PLAN_01.md + tasks/ROTA-T017/brief.md.
Covers solver.py's diversity search (canonical metric, cuts, frozen
lexicographic minima) and engine.py's multi-candidate assembly/validation/
warning association end to end.
"""
from __future__ import annotations

from datetime import date, datetime

from ortools.sat.python import cp_model

import rota.planning.engine as engine_module
import rota.planning.solver as solver_module
from rota.domain import (
    Assignment,
    AssignmentRole,
    AssignmentState,
    AvailabilityKind,
    AvailabilityRecord,
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
from rota.planning.engine import plan
from rota.planning.site_rules import EMPLOYEE_DAY_ONLY_N_EXCEPTION
from rota.planning.state import SiteRuleApplicability
from rota.planning.validator import validate as real_validate
from tests.support.minimal_state import SITE_ID, base_state

MONTH = date(2026, 10, 1)


def _employee(employee_id: str, *, day_only: bool = False) -> Employee:
    return Employee(employee_id, employee_id, date(2020, 1, 1), None, day_only)


def _membership(employee_id: str) -> SiteMembership:
    return SiteMembership(employee_id, SITE_ID, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT)


def _d_demand(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 5, 0), datetime(2026, 10, day, 17, 0), 1)


def _n_demand(demand_id: str, day: int) -> ShiftDemand:
    return ShiftDemand(demand_id, "test-v1", datetime(2026, 10, day, 17, 0), datetime(2026, 10, day + 1, 5, 0), 1)


def _exception_rule(rule_version_id: str, employee_id: str) -> SiteRuleVersion:
    return SiteRuleVersion(
        rule_version_id, f"rule-{rule_version_id}", SITE_ID, RuleCategory.CONFIRMED_EXCEPTION,
        EMPLOYEE_DAY_ONLY_N_EXCEPTION, {"employee_id": employee_id},
        RuleEnforcement.HARD, RuleResolution.RESOLVED, MONTH, date(2026, 10, 31),
        datetime(2026, 9, 1), "COORD", None, None, None, None,
    )


def _applicability(rule: SiteRuleVersion) -> SiteRuleApplicability:
    return SiteRuleApplicability(rule.rule_version_id, rule.effective_from, rule.effective_to)


def _symmetric_pool_state(count: int, **overrides):
    """`count` fully-interchangeable employees, `count` one-per-day D
    demands (spaced a full day apart -- always >=11h rest regardless of
    pairing), no work_balances (flat TARGET) so many pairwise-distinct
    legal solutions exist."""
    demands = tuple(_d_demand(f"D{i}", i + 1) for i in range(count))
    employees = tuple(_employee(chr(65 + i)) for i in range(count))
    memberships = tuple(_membership(e.employee_id) for e in employees)
    return base_state(employees=employees, memberships=memberships, shift_demands=demands, month=MONTH, **overrides)


def _signature(candidate: list[Assignment]) -> frozenset:
    return frozenset((a.covers_demand_id, a.employee_id) for a in candidate if a.role == AssignmentRole.PRIMARY and a.state != AssignmentState.CANCELLED)


def _pairwise_distances(candidates: list[list[Assignment]]) -> list[int]:
    signatures = [_signature(c) for c in candidates]
    return [
        len(signatures[i] ^ signatures[j]) // 2
        for i in range(len(signatures)) for j in range(i + 1, len(signatures))
    ]



def test_m1_at_least_three_diverse_solutions_gives_exactly_three():
    state = _symmetric_pool_state(6)
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert len(result.candidates) == 3
    for candidate in result.candidates:
        report = real_validate(state, candidate)
        assert report.hard_pass
    # M12/oracle 9: candidate 3 pairwise->=K against BOTH 1 and 2.
    n = 6
    k = (15 * n + 99) // 100
    assert all(distance >= k for distance in _pairwise_distances(result.candidates))



def test_m2_only_one_legal_solution_gives_feasible_len_one():
    state = _symmetric_pool_state(1)
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert len(result.candidates) == 1



def test_m3_only_two_legal_solutions_gives_feasible_len_two():
    from dataclasses import replace

    # A low LOAD-01 cap forces each employee to cover at most one of the two
    # demands, so exactly two full coverings exist: (A,B) and (B,A).
    state = _symmetric_pool_state(2)
    state = replace(state, profile=replace(state.profile, rolling_7d_decision_threshold_hours=12))
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert len(result.candidates) == 2
    assert _pairwise_distances(result.candidates)[0] >= 1



def test_m4_m5_threshold_formula_boundaries():
    assert (15 * 20 + 99) // 100 == 3
    assert (15 * 7 + 99) // 100 == 2
    assert (15 * 6 + 99) // 100 == 1


def _distinct_employee_demands(by_demand, demand_ids, count):
    chosen = []
    for demand_id in demand_ids:
        if all(by_demand[demand_id] != by_demand[d] for d in chosen):
            chosen.append(demand_id)
            if len(chosen) == count:
                return chosen
    raise AssertionError(f"could not find {count} demands with pairwise-distinct employees")


def _capture_model_with_single_diversity_cut(monkeypatch, state):
    """Capture the REAL live plan() CpModel + x right after cut #1 is added
    (RHS=N-K vs candidate 1), then stop the search -- isolates one real cut."""
    captured: dict = {}
    real_candidate_signature = solver_module._candidate_signature

    def _spy_signature(solver, x, slots):
        captured.setdefault("x", x)
        return real_candidate_signature(solver, x, slots)

    real_run_solver = solver_module._run_solver
    call_count = {"n": 0}

    def _spy_run_solver(model):
        call_count["n"] += 1
        captured["model"] = model
        solver, status = real_run_solver(model)
        if call_count["n"] == 2:
            return solver, cp_model.INFEASIBLE  # stop the search right after cut #1
        return solver, status

    monkeypatch.setattr(solver_module, "_candidate_signature", _spy_signature)
    monkeypatch.setattr(solver_module, "_run_solver", _spy_run_solver)
    result = plan(state)
    monkeypatch.undo()
    return result, captured["model"], captured["x"]


def test_m4_n20_k3_operational_cut_rejects_distance_two_accepts_distance_three(monkeypatch):
    """N=20 -> K=3: pin a full distance-2/distance-3 alternate onto the REAL
    live production model+cut and re-solve -- proves the real cut rejects
    distance 2, admits distance 3."""
    n, k = 20, (15 * 20 + 99) // 100
    assert k == 3

    result, model, x = _capture_model_with_single_diversity_cut(monkeypatch, _symmetric_pool_state(n))
    assert result.status == "FEASIBLE"
    first_signature = _signature(result.candidates[0])
    assert len(first_signature) == n
    by_demand = dict(first_signature)
    demand_ids = sorted(by_demand)
    d0, d1 = _distinct_employee_demands(by_demand, demand_ids, 2)
    swapped_two = {(d0, by_demand[d1]), (d1, by_demand[d0])} | {
        (d, e) for d, e in first_signature if d not in (d0, d1)
    }
    for demand_id, employee_id in swapped_two:
        model.add(x[employee_id, demand_id] == 1)
    _, status_two = solver_module._run_solver(model)
    assert status_two == cp_model.INFEASIBLE

    result2, model2, x2 = _capture_model_with_single_diversity_cut(monkeypatch, _symmetric_pool_state(n))
    first_signature2 = _signature(result2.candidates[0])
    by_demand2 = dict(first_signature2)
    demand_ids2 = sorted(by_demand2)
    da, db, dc = _distinct_employee_demands(by_demand2, demand_ids2, 3)
    swapped_three = {(da, by_demand2[db]), (db, by_demand2[dc]), (dc, by_demand2[da])} | {
        (d, e) for d, e in first_signature2 if d not in (da, db, dc)
    }
    for demand_id, employee_id in swapped_three:
        model2.add(x2[employee_id, demand_id] == 1)
    _, status_three = solver_module._run_solver(model2)
    assert status_three in (cp_model.OPTIMAL, cp_model.FEASIBLE)



def test_m6_one_employee_substitution_counts_as_one_changed_placement():
    a = [Assignment("x1", "v1", "A", datetime(2026, 10, 1, 5), datetime(2026, 10, 1, 17), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D1", None)]
    b = [Assignment("x2", "v1", "B", datetime(2026, 10, 1, 5), datetime(2026, 10, 1, 17), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D1", None)]
    assert _pairwise_distances([a, b]) == [1]


def test_m7_assignment_id_only_change_does_not_count():
    a = [Assignment("x1", "v1", "A", datetime(2026, 10, 1, 5), datetime(2026, 10, 1, 17), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D1", None)]
    b = [Assignment("x2", "v1", "A", datetime(2026, 10, 1, 5), datetime(2026, 10, 1, 17), AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D1", None)]
    assert _signature(a) == _signature(b)


def test_m8_list_ordering_does_not_count():
    d1 = ShiftDemand("D1", "v1", datetime(2026, 10, 1, 5), datetime(2026, 10, 1, 17), 1)
    d2 = ShiftDemand("D2", "v1", datetime(2026, 10, 2, 5), datetime(2026, 10, 2, 17), 1)
    a = [
        Assignment("x1", "v1", "A", d1.start_datetime, d1.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D1", None),
        Assignment("x2", "v1", "B", d2.start_datetime, d2.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D2", None),
    ]
    assert _signature(a) == _signature(list(reversed(a)))


def test_m9_work_period_provenance_only_difference_does_not_count():
    d1 = ShiftDemand("D1", "v1", datetime(2026, 10, 1, 5), datetime(2026, 10, 1, 17), 1)
    a = Assignment("x1", "v1", "A", d1.start_datetime, d1.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D1", None, work_period_id="wp-1")
    b = Assignment("x1", "v1", "A", d1.start_datetime, d1.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, "D1", None, work_period_id="wp-2")
    assert _signature([a]) == _signature([b])


def test_m10_trainee_cancelled_fixed_facts_absent_from_signature():
    d1 = ShiftDemand("D1", "v1", datetime(2026, 10, 1, 5), datetime(2026, 10, 1, 17), 1)
    trainee = Assignment("t1", "v1", "T", d1.start_datetime, d1.end_datetime, AssignmentRole.TRAINEE, AssignmentState.PLANNED, False, None, "mentor-1")
    cancelled = Assignment("c1", "v1", "X", d1.start_datetime, d1.end_datetime, AssignmentRole.PRIMARY, AssignmentState.CANCELLED, False, "D1", None)
    assert _signature([trainee, cancelled]) == frozenset()


def test_m11_fixed_realized_fact_never_contributes_to_diversity_and_never_changes():
    """A fixed (REALIZED) PRIMARY is never a CP-SAT slot, so it can never be
    part of the diversity signature and must be identical in every candidate."""
    demands = tuple(_d_demand(f"D{i}", i + 1) for i in range(6))
    employees = tuple(_employee(chr(65 + i)) for i in range(6))
    memberships = tuple(_membership(e.employee_id) for e in employees)
    fixed = Assignment(
        "fixed-a-d0", "test-v1", "A", demands[0].start_datetime, demands[0].end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, demands[0].demand_id, None,
    )
    state = base_state(
        employees=employees, memberships=memberships, shift_demands=demands,
        existing_assignments=(fixed,), month=MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    for candidate in result.candidates:
        by_demand = {a.covers_demand_id: a.employee_id for a in candidate}
        assert by_demand[demands[0].demand_id] == "A"


def test_m11_n_zero_gives_at_most_one_candidate():
    """N=0 (every demand already covered by a fixed fact): the variant search
    must not run at all -- at most one candidate."""
    demand = _d_demand("D1", 6)
    fixed = Assignment(
        "fixed-a-d1", "test-v1", "A", demand.start_datetime, demand.end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.REALIZED, False, demand.demand_id, None,
    )
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),),
        shift_demands=(demand,), existing_assignments=(fixed,), month=MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert len(result.candidates) == 1



# T017-R3-1: literal placement signature captured once from BASE_SHA
# d1a0ec0438718b1b7fd91e5c146e67b58c4eb4f9 (pre-T017), by running
# solve(_symmetric_pool_state(6), enforce_load_cap=True,
# allow_day_only_n_fallback=False, allow_emergency_24h=False) -- the exact
# Stage 1 capped call plan() makes first -- on that commit and recording its
# deterministic output (num_search_workers=1, random_seed=0). A real
# historical oracle, not a second current-code call.
PRE_T017_STAGE1_SIGNATURE = frozenset({
    ("D0", "B"), ("D1", "A"), ("D2", "E"), ("D3", "F"), ("D4", "A"), ("D5", "A"),
})


def test_m13_first_candidate_matches_pre_t017_deterministic_result():
    """Candidate 1 of a multi-variant plan() result must match the frozen
    pre-T017 placement oracle for the same state and capability context."""
    state = _symmetric_pool_state(6)
    result = plan(state)
    assert result.status == "FEASIBLE"
    first_full = [a for a in result.candidates[0] if a.covers_demand_id]
    assert _signature(first_full) == PRE_T017_STAGE1_SIGNATURE



def test_m14_m16_replan_all_candidates_preserve_same_minimum_reshuffle():
    demands = tuple(_d_demand(f"D{i}", i + 1) for i in range(6))
    employees = tuple(_employee(chr(65 + i)) for i in range(7))  # one extra, redistributable
    memberships = tuple(_membership(e.employee_id) for e in employees)
    baseline = Assignment(
        "baseline-a-d0", "test-v1", "A", demands[0].start_datetime, demands[0].end_datetime,
        AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demands[0].demand_id, None,
    )
    state = base_state(
        employees=employees, memberships=memberships, shift_demands=demands,
        existing_assignments=(baseline,), month=MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    for candidate in result.candidates:
        by_demand = {a.covers_demand_id: a.employee_id for a in candidate}
        # 0 reshuffle is always achievable here (A can simply keep D0 while
        # any other employee covers the rest) -- every variant must find it,
        # never a larger reshuffle merely to buy diversity.
        assert by_demand[demands[0].demand_id] == "A"



def test_m15_day_only_fallback_all_candidates_preserve_exceptional_n_minimum():
    n1, n2 = _n_demand("N1", 6), _n_demand("N2", 13)
    a = _employee("A", day_only=True)
    b = _employee("B", day_only=True)
    c = _employee("C")
    rule_a, rule_b = _exception_rule("RV-A", "A"), _exception_rule("RV-B", "B")
    c_leave = AvailabilityRecord("c-leave", "v1", "C", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 13), date(2026, 10, 13), True, None, None)
    state = base_state(
        employees=(a, b, c), memberships=(_membership("A"), _membership("B"), _membership("C")),
        shift_demands=(n1, n2), availability_records=(c_leave,),
        site_rules=(rule_a, rule_b), site_rule_applicability=(_applicability(rule_a), _applicability(rule_b)),
        month=MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    for candidate in result.candidates:
        by_demand = {a.covers_demand_id: a.employee_id for a in candidate}
        assert by_demand["N1"] == "C"
        assert by_demand["N2"] in {"A", "B"}



def _tracking_solve(monkeypatch):
    real_solve = solver_module.solve
    calls: list[tuple] = []

    def _wrapped(state, **kwargs):
        calls.append((kwargs.get("enforce_load_cap", True), kwargs.get("allow_day_only_n_fallback", False), kwargs.get("allow_emergency_24h", False)))
        return real_solve(state, **kwargs)

    monkeypatch.setattr(engine_module, "solve", _wrapped)
    return calls


def test_m17_stage1_feasible_one_variant_never_calls_stage2(monkeypatch):
    calls = _tracking_solve(monkeypatch)
    state = _symmetric_pool_state(1)
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert calls == [(True, False, False)]


def test_m18_stage2_first_feasible_variants_stay_in_stage2(monkeypatch):
    n1, n2 = _n_demand("N1", 6), _n_demand("N2", 13)
    a = _employee("A", day_only=True)
    rule = _exception_rule("RV-EXC", "A")
    calls = _tracking_solve(monkeypatch)
    state = base_state(
        employees=(a,), memberships=(_membership("A"),), shift_demands=(n1, n2),
        site_rules=(rule,), site_rule_applicability=(_applicability(rule),), month=MONTH,
    )
    result = plan(state)
    assert result.status == "FEASIBLE"
    assert [c[:2] for c in calls] == [(True, False)] + [(True, True)] * (len(calls) - 1)
    assert all(not c[2] for c in calls)  # emergency never requested


def test_m19_stage3_first_feasible_with_variants_never_reaches_stage4(monkeypatch):
    """Stage 1/2 proven INFEASIBLE, Stage 3 the first FEASIBLE: Stage 4 must never run."""
    demand = _d_demand("D1", 6)
    employees = (_employee("A"), _employee("B"))
    memberships = tuple(_membership(e.employee_id) for e in employees)
    state = base_state(employees=employees, memberships=memberships, shift_demands=(demand,), month=MONTH)
    first = Assignment("first", "test-v1", "A", demand.start_datetime, demand.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None)
    second = Assignment("second", "test-v1", "B", demand.start_datetime, demand.end_datetime, AssignmentRole.PRIMARY, AssignmentState.PLANNED, False, demand.demand_id, None)
    calls: list[tuple[bool, bool, bool]] = []

    def _fake_solve(_state, enforce_load_cap=True, allow_emergency_24h=False, allow_day_only_n_fallback=False):
        calls.append((enforce_load_cap, allow_day_only_n_fallback, allow_emergency_24h))
        if len(calls) < 3:
            return solver_module.SolverOutcome("INFEASIBLE", None, [], [], {}, [], {})
        return solver_module.SolverOutcome("OPTIMAL", [first], [], [], {}, [], {}, alternatives=[([second], [])])

    monkeypatch.setattr(engine_module, "solve", _fake_solve)
    result = plan(state)

    assert result.status == "FEASIBLE"
    assert len(result.candidates) == 2
    assert calls == [(True, False, False), (True, True, False), (True, True, True)]

# (already exercised structurally by M2/M3's exact 1/2-candidate results)



def _run_solver_forcing_second_call(monkeypatch, forced_status):
    real_run_solver = solver_module._run_solver
    call_count = {"n": 0}

    def _fake_run_solver(model):
        call_count["n"] += 1
        solver, status = real_run_solver(model)
        if call_count["n"] == 2:
            return solver, forced_status
        return solver, status

    monkeypatch.setattr(solver_module, "_run_solver", _fake_run_solver)


def test_m22_optional_unknown_status_fails_whole_result_closed(monkeypatch):
    from ortools.sat.python import cp_model

    _run_solver_forcing_second_call(monkeypatch, cp_model.UNKNOWN)
    result = plan(_symmetric_pool_state(6))
    assert result.status == "TECHNICAL_ERROR"
    assert result.candidates == []


def test_m23_optional_model_invalid_status_fails_whole_result_closed(monkeypatch):
    from ortools.sat.python import cp_model

    _run_solver_forcing_second_call(monkeypatch, cp_model.MODEL_INVALID)
    result = plan(_symmetric_pool_state(6))
    assert result.status == "TECHNICAL_ERROR"
    assert result.candidates == []

# (already asserted inside M1's test)



def test_m25_injected_validator_failure_on_candidate2_fails_whole_result_closed(monkeypatch):
    real_validator = engine_module.validate
    call_count = {"n": 0}

    def _fake_validate(state, assignments):
        call_count["n"] += 1
        report = real_validator(state, assignments)
        if call_count["n"] == 2:
            from dataclasses import replace as _replace
            return _replace(report, hard_pass=False, violations=["injected failure"])
        return report

    monkeypatch.setattr(engine_module, "validate", _fake_validate)
    state = _symmetric_pool_state(6)
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"
    assert result.candidates == []



def test_m26_m28_multi_candidate_real_warnings_keep_prefix_order_and_body():
    """A real (non-vacuous) 2-candidate, 2-warning DAY_ONLY scenario, proving
    prefix ordering (M26) and the full legacy body under the prefix (M28)."""
    n1, n2 = _n_demand("N1", 6), _n_demand("N2", 13)
    a = _employee("A", day_only=True)
    b = _employee("B", day_only=True)
    c = _employee("C")
    rule_a, rule_b = _exception_rule("RV-A", "A"), _exception_rule("RV-B", "B")
    c_leave = AvailabilityRecord("c-leave", "v1", "C", AvailabilityKind.LEAVE_GRANTED, date(2026, 10, 13), date(2026, 10, 13), True, None, None)
    state = base_state(
        employees=(a, b, c), memberships=tuple(_membership(e) for e in ("A", "B", "C")),
        shift_demands=(n1, n2), availability_records=(c_leave,),
        site_rules=(rule_a, rule_b), site_rule_applicability=(_applicability(rule_a), _applicability(rule_b)),
        month=MONTH,
    )

    result = plan(state)

    assert result.status == "FEASIBLE"
    assert len(result.candidates) == 2
    assert len(result.warnings) == 2
    seen_prefixes = [w.split(" | ", 1)[0] for w in result.warnings]
    assert seen_prefixes == sorted(seen_prefixes, key=lambda p: int(p.split("=")[1]))
    for index, warning in enumerate(result.warnings, start=1):
        assert warning.startswith(f"candidate={index} | DAY_ONLY-N-FALLBACK-01 SOFT:")
        for required in ("employee=", "demand=N2", "date=2026-10-13", "rule_version_id=RV-"):
            assert required in warning


def test_m27_single_candidate_real_warning_shape_is_legacy_unprefixed():
    """A real DAY_SHIFT_OFF-01 SOFT warning on a single-candidate result
    keeps the exact legacy unprefixed body, not just an empty warning list."""
    n1 = _n_demand("N1", 6)
    day_off = AvailabilityRecord("a-dayoff", "v1", "A", AvailabilityKind.DAY_SHIFT_OFF, date(2026, 10, 7), date(2026, 10, 7), True, None, None)
    state = base_state(
        employees=(_employee("A"),), memberships=(_membership("A"),),
        shift_demands=(n1,), availability_records=(day_off,), month=MONTH,
    )

    result = plan(state)

    assert result.status == "FEASIBLE"
    assert len(result.candidates) == 1
    assert not any(w.startswith("candidate=") for w in result.warnings)
    assert "DAY_SHIFT_OFF-01 SOFT: A prior N enters day off until 05:00 on 2026-10-07" in result.warnings



def test_m30_decision_required_still_has_empty_candidates():
    employee = Employee("A", "A", date(2026, 9, 1), None, False)
    state = base_state(employees=(employee,), memberships=(), shift_demands=(_d_demand("D1", 6),), month=MONTH)
    result = plan(state)
    assert result.status == "DECISION_REQUIRED"
    assert result.candidates == []


def test_m31_technical_error_still_has_empty_candidates():
    bad_demand = ShiftDemand("bad-1", "test-v1", datetime(2026, 10, 1, 8, 0), datetime(2026, 10, 1, 16, 0), 1)
    state = base_state(shift_demands=(bad_demand,), month=MONTH)
    result = plan(state)
    assert result.status == "TECHNICAL_ERROR"
    assert result.candidates == []



def test_m32_repeated_same_input_gives_same_ordered_signatures():
    state = _symmetric_pool_state(6)
    first = plan(state)
    second = plan(state)
    assert [_signature(c) for c in first.candidates] == [_signature(c) for c in second.candidates]



def test_m29_select_candidate2_real_persistence_roundtrip(tmp_path):
    from rota.application import bootstrap, durable_inputs, lifecycle_ops, open_month, plan_ops, store
    from rota.application.assembler import assemble_planning_state
    from rota.domain import Coordinator, CoordinatorSiteAssociation, ShiftKind, Site, SiteProfile, StandardShift

    coord, site, profile_id = "T017-COORD", "T017-SITE", "T017-PROFILE"
    month = date(2026, 10, 1)
    db_path = tmp_path / "t017-roundtrip.db"

    conn = store.open_store(db_path)
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=coord, site_id=site, coordinator=Coordinator(coord, "T017 coordinator", True),
        site_profile=SiteProfile(profile_id, "T017 profile", True, [StandardShift(ShiftKind.D, datetime(2026, 10, 1, 5).time(), datetime(2026, 10, 1, 17).time(), False, 1)], True, False, False, False, 1, 999),
    )
    bootstrap.bootstrap_or_resume_coordinator_context(
        conn, coordinator_id=coord, site_id=site, site=Site(site, profile_id, "T017 site", True),
        association=CoordinatorSiteAssociation(coord, site, True),
    )
    for letter in "ABCDEF":
        durable_inputs.update_employee(conn, coordinator_id=coord, site_id=site, employee=_employee(letter))
        durable_inputs.update_membership(
            conn, coordinator_id=coord, site_id=site,
            membership=SiteMembership(letter, site, MembershipKind.LOCAL, True, ReadinessState.READY_FOR_PRIMARY, ReadinessSource.DEFAULT),
        )
    import calendar as _calendar_module
    from rota.domain import CalendarDay

    for day in range(1, _calendar_module.monthrange(2026, 10)[1] + 1):
        durable_inputs.set_calendar_day(conn, coordinator_id=coord, site_id=site, day=CalendarDay(date(2026, 10, day), False))

    result = plan_ops.plan_month(conn, site_id=site, month=month, coordinator_id=coord, effective_from=month)
    assert result.status == "FEASIBLE"
    # T017-R3-2: a hard assertion, not a conditional skip -- this fixture must
    # keep yielding >=2 diverse candidates so the candidate-2 round-trip stays
    # a live oracle rather than silently degrading into a no-op.
    assert len(result.candidates) >= 2
    chosen = result.candidates[1]
    plan_ops.select_candidate(conn, site_id=site, month=month, candidate=chosen, coordinator_id=coord)
    lifecycle_ops.finalize(conn, site_id=site, month=month, coordinator_id=coord, acknowledged_deviation_ids=set())
    conn.close()

    reopened = store.open_store(db_path)
    view = open_month.open_month(reopened, site_id=site, month=month)
    state, _ = assemble_planning_state(reopened, site_id=site, month=month)
    assert view.current_version is not None
    persisted_signature = _signature(list(state.existing_assignments))
    assert persisted_signature == _signature(chosen)
    reopened.close()


if __name__ == "__main__":
    print("test_t017 module OK")

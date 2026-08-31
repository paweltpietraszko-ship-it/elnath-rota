"""ROTA-T044 (tasks/ROTA-T044/brief.md R8, TASK_CHATGPT.md,
TASK_CHATGPT_CORRECTION_R1/R2, ARCHITECT_FINAL_PREIMPLEMENTATION_GATE.md):
Symulator Koordynatora Wariant B pytest entry point.

Checkpoint A: layered calculator oracle (5/10/9/4), free per-(kind,weekday)
required_primary_count generation, legal overlap kept, zero-coverage
rejected. Checkpoint B: real API vertical, initial-setup-only absences
(urlop 10/5, L4 ~25%), EXTERNAL reaction after a real DECISION_REQUIRED,
HEADCOUNT/CLOSED WORLD invariants. Checkpoint C: Hypothesis stateful state
machine over the real backend, database=None/deadline=None/derandomize=False,
profile numbers from tasks/ROTA-T044/round_01/tests/hypothesis_profile_measurement.md
(measured, not guessed).

Wariant A (test_coordinator_simulator.py) is untouched; this file is fully
additive, per TASK_SCOPE."""
from __future__ import annotations

import json
import os
import random
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from hypothesis import settings
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, precondition, rule

from api.deps import get_conn
from api.main import app
from rota.persistence.db import connect
from tests.property import coordinator_simulator as sim

REPORT_DIR = Path(__file__).resolve().parents[2] / "tasks" / "ROTA-T044" / "round_01" / "tests"
FAILURES_DIR = REPORT_DIR / "failures"

# The complete real status vocabulary (rota/planning/engine_types.py::PlanningResult.status)
# -- found via a real Hypothesis-generated NARROW_SEARCH_EXHAUSTED case
# during this Task's own implementation (seed=1420): a genuine REPLAN
# outcome (T033's "replan must differ" search can exhaust its narrowed
# space), not a harness bug. Checking against the FULL vocabulary here,
# not a guessed subset, is what keeps a real product status from being
# misreported as a tool crash.
_KNOWN_PLAN_STATUSES = {
    "FEASIBLE", "DECISION_REQUIRED", "TECHNICAL_ERROR",
    "NO_ALTERNATIVE", "NARROW_SEARCH_EXHAUSTED", "SEARCH_INCOMPLETE",
}


# ===========================================================================
# Checkpoint A -- pure arithmetic + generator, no backend
# ===========================================================================

def test_calc_01_uniform_req1_gives_5():
    assert sim.layered_headcount_b(sim.CONTROL_ATOMS_UNIFORM_1_B) == 5


def test_calc_02_uniform_req2_gives_10():
    assert sim.layered_headcount_b(sim.CONTROL_ATOMS_UNIFORM_2_B) == 10


def test_calc_03_mixed_workday2_weekend1_gives_9():
    assert sim.layered_headcount_b(sim.CONTROL_ATOMS_MIXED_B) == 9


def test_calc_04_devils_advocate_counterexample_gives_4_not_5():
    """ARCHITECT_FINAL_PREIMPLEMENTATION_GATE.md section 3.2 / CC devil's
    advocate finding 2: the naive "sum of independent per-layer maxima"
    gave 5 for this exact shape; the canonical max_m(sum_k(...)) formula
    must give the true worst-single-month 4."""
    assert sim.layered_headcount_b(sim.CONTROL_ATOMS_COUNTEREXAMPLE_B) == 4


def test_has_any_coverage_b_rejects_empty_atoms():
    assert sim.has_any_coverage_b(()) is False
    assert sim.has_any_coverage_b(sim.CONTROL_ATOMS_UNIFORM_1_B) is True


@pytest.mark.parametrize("seed", range(30))
def test_t44_b_04_headcount_invariant_holds_for_every_generated_object(seed):
    spec = sim.random_object_spec_b(seed)
    sim.assert_headcount_b(spec)


def test_t44_b_05_generator_can_represent_owners_mixed_shape():
    """T44-B-05: the generator's DATA MODEL supports the owner's reference
    mixed object (workdays req=2, weekend req=1) -- CALC-03 already proves
    the arithmetic, this proves the shape is representable at all."""
    atoms = sim.CONTROL_ATOMS_MIXED_B
    weekday_reqs = {a.required_primary_count for a in atoms if a.weekday in sim.WEEKDAYS}
    weekend_reqs = {a.required_primary_count for a in atoms if a.weekday in sim.WEEKEND}
    assert weekday_reqs == {2}
    assert weekend_reqs == {1}


def test_t44_b_06_legal_catalog_overlap_is_not_collapsed_or_filtered():
    """rota/planning/shift_catalog.py::generate_catalog_demands documents
    that multiple entries/overlaps are legal, independent occurrences.
    Two D-kind rows on the same weekday at different hours/required counts
    must both survive grouping as distinct catalog rows."""
    from datetime import time as _time
    atoms = (
        sim.DemandAtomB("D", _time(5, 0), _time(9, 0), 1, 1),
        sim.DemandAtomB("D", _time(9, 0), _time(17, 0), 2, 1),
    )
    rows = sim.catalog_rows_from_atoms_b(atoms)
    assert len(rows) == 2
    assert {r["required_primary_count"] for r in rows} == {1, 2}


def test_t44_b_07_zero_coverage_object_is_never_produced():
    rng_seed = 0
    for seed in range(200):
        spec = sim.random_object_spec_b(seed + rng_seed)
        assert sim.has_any_coverage_b(spec.atoms)


def test_t44_r10_01_generator_reaches_h24_and_varied_hours_and_same_day_overlap():
    """R10-01 regression: the first generator drew only two fixed canonical
    D 05-17 / N 17-05 windows, so H24 and other durations/start hours were
    unreachable, and no (kind, weekday) ever had two independent entries."""
    all_windows = set()
    h24_count = 0
    same_kind_weekday_max = 0
    for seed in range(500):
        spec = sim.random_object_spec_b(seed)
        counts: dict[tuple[str, int], int] = {}
        for a in spec.atoms:
            all_windows.add((a.kind, a.start, a.end))
            if a.start == a.end:
                h24_count += 1
            counts[(a.kind, a.weekday)] = counts.get((a.kind, a.weekday), 0) + 1
        if counts:
            same_kind_weekday_max = max(same_kind_weekday_max, max(counts.values()))
    assert len(all_windows) > 2, f"only {len(all_windows)} distinct (kind,start,end) windows ever appeared"
    assert h24_count > 0, "H24 (start==end) never appeared across 500 seeds"
    assert same_kind_weekday_max >= 2, "same-kind-same-weekday legal overlap never appeared across 500 seeds"


def test_generated_objects_vary_across_seeds_not_a_fixed_scenario():
    """Real variety, not scenario-replay: two different seeds produce
    canonically different objects (month and/or atom set differ)."""
    a = sim.random_object_spec_b(1)
    b = sim.random_object_spec_b(2)
    assert (a.month, a.atoms) != (b.month, b.atoms)


# --- T44-B-08: urlop boundary for roster sizes 1, 5, 10 --------------------

class _FakeSpecForUrlop:
    def __init__(self, month: date, employee_count: int):
        self.month = month
        self.employee_count = employee_count


def _workdays_covered(start: date, end: date) -> int:
    from datetime import timedelta as _td
    return sum(1 for i in range((end - start).days + 1) if sim._is_workday_b(start + _td(days=i)))


@pytest.mark.parametrize("month", [date(2026, 1, 1), date(2026, 4, 1), date(2026, 11, 1), date(2026, 12, 1)])
def test_t44_r10_02_urlop_blocks_cover_exact_workdays_across_a_holiday(month):
    """R10-02 regression: months containing a POLISH_2026_HOLIDAYS date
    used to give a shorter-than-promised block (e.g. 9 working days instead
    of 10) because the old implementation added a fixed 14/7 calendar days
    without checking for holidays inside the span."""
    spec = _FakeSpecForUrlop(month, 5)
    ten, five = sim.urlop_blocks_b(spec)
    assert _workdays_covered(ten.start_date, ten.end_date) == 10
    assert _workdays_covered(five.start_date, five.end_date) == 5


@pytest.mark.parametrize("employee_count", [1, 5, 10])
def test_t44_b_08_urlop_scale_never_tries_10_5_for_every_employee(employee_count):
    spec = _FakeSpecForUrlop(date(2026, 7, 1), employee_count)
    blocks = sim.urlop_blocks_b(spec)
    if employee_count == 1:
        assert len(blocks) == 1
        assert blocks[0].employee_index == 0
        assert (blocks[0].end_date - blocks[0].start_date).days == 13  # 2 calendar weeks
    else:
        assert len(blocks) == 2
        indices = {b.employee_index for b in blocks}
        assert indices == {0, 1}
        ten, five = sorted(blocks, key=lambda b: (b.end_date - b.start_date), reverse=True)
        assert (ten.end_date - ten.start_date).days == 13
        assert (five.end_date - five.start_date).days == 6
        assert ten.end_date < five.start_date or five.end_date < ten.start_date


# --- T44-B-09: L4 semantics -------------------------------------------------

def test_t44_b_09_sick_leave_is_five_calendar_days_local_only():
    spec = sim.random_object_spec_b(3)
    for trial_seed in range(50):
        rng = random.Random(trial_seed)
        draw = sim.sick_leave_draw_b(spec, rng)
        if draw is not None:
            assert draw.kind == "SICK_LEAVE"
            assert 0 <= draw.employee_index < spec.employee_count
            assert (draw.end_date - draw.start_date).days == 4  # 5 calendar days inclusive


def test_t44_b_09_sick_leave_frequency_is_roughly_one_quarter_not_fixed_schedule():
    spec = sim.random_object_spec_b(3)
    hits = sum(1 for s in range(2000) if sim.sick_leave_draw_b(spec, random.Random(s)) is not None)
    rate = hits / 2000
    assert 0.15 < rate < 0.35, f"observed L4 rate {rate}, expected roughly 0.25, not a rigid schedule"


# ===========================================================================
# Checkpoint B -- real API vertical
# ===========================================================================

@pytest.fixture
def client():
    connection = connect(":memory:")
    app.dependency_overrides[get_conn] = lambda: (yield connection)
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_conn, None)
        connection.close()


def test_t44_b_10_first_plan_uses_only_declared_local(client):
    spec = sim.random_object_spec_b(5)
    site_id = sim.build_object_b(client, spec)
    rng = random.Random(5 * 104729 + 1)
    draws = sim.initial_absences_b(spec, rng)
    sim.apply_absences_b(client, site_id, spec, draws)

    result = sim.run_plan(client, site_id, spec.month)
    assert result["status"] in _KNOWN_PLAN_STATUSES
    if result["status"] == "FEASIBLE":
        used = {a["employee_id"] for a in result["candidates"][0]}
        assert used <= set(sim.declared_roster_b(spec))


def test_t44_b_11_external_reaction_after_real_decision_required_correct_ordering(client):
    spec = sim.random_object_spec_b(0)
    if spec.employee_count < 2:
        pytest.skip("needs a roster large enough to leave exactly one enabled LOCAL")
    site_id = sim.build_object_b(client, spec)

    # Force a real, unforced DECISION_REQUIRED: disable all but one LOCAL
    # through the real roster PATCH -- same technique as Wariant A's own
    # equivalent test.
    for i in range(1, spec.employee_count):
        resp = client.patch(
            f"/api/workspace/sites/{site_id}/roster/{sim.local_employee_id_b(spec, i)}", json={"enabled": False},
        )
        assert resp.status_code == 204, resp.text

    first_result = sim.run_plan(client, site_id, spec.month)
    if first_result["status"] != "DECISION_REQUIRED" or not first_result.get("decision_payload"):
        pytest.skip(f"one enabled LOCAL was still sufficient for this generated object (status={first_result['status']})")

    reaction = sim.external_support_reaction_b(client, site_id, spec.month, spec, attempt=1)
    assert reaction["external_employee_id"] == sim.external_support_employee_id_b(spec, 1)

    roster = client.get(f"/api/workspace/sites/{site_id}/roster").json()
    external_rows = [r for r in roster if r["employee_id"] == reaction["external_employee_id"]]
    assert len(external_rows) == 1
    assert external_rows[0]["membership_kind"] == "EXTERNAL_SUPPORT"
    local_rows = [r for r in roster if r["membership_kind"] == "LOCAL"]
    assert len(local_rows) == spec.employee_count, "EXTERNAL reaction must never change LOCAL headcount"

    # First PLAN's own result is preserved untouched.
    assert first_result["status"] == "DECISION_REQUIRED"
    assert reaction["retry_result"]["status"] in _KNOWN_PLAN_STATUSES


def test_t44_b_12_external_limit_stops_at_initial_local_count(client):
    """A hand-built, deliberately unsatisfiable-even-with-one-EXTERNAL
    object (required_primary_count=3, a value the Wariant B *generator*
    never draws -- Codex R2-02 narrows {1,2} -- but the real product/
    catalog itself has no such restriction, so this is a legitimate direct
    use of the real API to exercise the loop's own termination bound, not a
    claim about what the generator produces)."""

    class _Spec:
        seed = 999
        month = date(2026, 7, 1)
        regime = "ORDINARY"
        rolling_7d_threshold_hours = 60
        employee_count = 1
        target_hours_per_employee = sim.nominal_monthly_hours_kp(date(2026, 7, 1), sim.POLISH_2026_HOLIDAYS)

    spec = _Spec()
    resp = client.post(
        "/api/workspace/sites",
        json={"display_name": "SIMB-999", "profile_display_name": "SIMB-PROFILE-999",
              "rolling_7d_decision_threshold_hours": 60, "planning_regime": "ORDINARY"},
    )
    assert resp.status_code == 201, resp.text
    site_id = resp.json()["site_id"]
    resp = client.put(
        f"/api/workspace/sites/{site_id}/shift-catalog",
        json={"shifts": [{"kind": "D", "start_time": "08:00", "end_time": "08:00", "required_primary_count": 3, "active_weekdays": list(sim.ALL_WEEK)}]},
    )
    assert resp.status_code == 204, resp.text
    sim.seed_calendar(client, site_id, spec.month)
    sim.add_local_employee_b(client, site_id, spec, 0)

    first_result = sim.run_plan(client, site_id, spec.month)
    if first_result["status"] != "DECISION_REQUIRED" or not first_result.get("decision_payload"):
        pytest.skip(f"product satisfied a 1-vs-3 headcount gap without DECISION_REQUIRED (status={first_result['status']})")

    loop = sim.run_with_external_loop_b(client, site_id, spec.month, spec, first_result)
    assert len(loop["externals"]) <= spec.employee_count
    if loop["final_result"]["status"] == "DECISION_REQUIRED":
        assert loop["exhausted_limit"] is True
        assert len(loop["externals"]) == spec.employee_count


def test_t44_b_13_closed_world_detects_a_foreign_employee_id():
    declared = ["SIMB-1-EMP-0", "SIMB-1-EMP-1"]
    external = ["SIMB-EXTERNAL-1-1"]
    ok_assignments = [{"assignment_id": "A1", "employee_id": "SIMB-1-EMP-0"}, {"assignment_id": "A2", "employee_id": "SIMB-EXTERNAL-1-1"}]
    sim.assert_closed_world_b(ok_assignments, declared, external)  # must not raise

    bad_assignments = ok_assignments + [{"assignment_id": "A3", "employee_id": "SOMEONE-ELSE"}]
    with pytest.raises(AssertionError):
        sim.assert_closed_world_b(bad_assignments, declared, external)


def test_t44_r10_03_all_candidate_assignments_b_covers_every_candidate_not_just_first():
    """R10-03 regression: a FEASIBLE result with a foreign employee_id
    hidden in the SECOND candidate must be caught -- checking only
    candidates[0] silently missed exactly this case."""
    declared = ["SIMB-1-EMP-0"]
    result = {
        "status": "FEASIBLE",
        "candidates": [
            [{"assignment_id": "A1", "employee_id": "SIMB-1-EMP-0"}],
            [{"assignment_id": "A2", "employee_id": "NOT-DECLARED"}],
        ],
    }
    flattened = sim.all_candidate_assignments_b(result)
    assert len(flattened) == 2
    with pytest.raises(AssertionError):
        sim.assert_closed_world_b(flattened, declared, [])


def test_absences_are_written_before_first_plan_never_after():
    """CC devil's-advocate finding 1 / CORRECTION_R2: absences are a
    strictly initial-setup-only step in this harness's own driver code --
    there is no function anywhere in this module that writes an
    AbsenceDraw after run_plan/run_replan has already been called for that
    site. This test documents and pins that ordering at the call-site
    level actually used by Checkpoint B and the state machine below."""
    import inspect
    plan_source = inspect.getsource(sim.run_with_external_loop_b) + inspect.getsource(sim.external_support_reaction_b)
    assert "apply_absences_b" not in plan_source, (
        "PLAN/EXTERNAL-reaction machinery must never call apply_absences_b -- "
        "absences are initial-setup-only (CORRECTION_R2)."
    )


def test_t44_r11_01_non_assertion_backend_failure_still_writes_failure_json(monkeypatch, tmp_path):
    """R11-01 regression (tests_r11.txt): every wrapped stage used to catch
    only AssertionError, so a genuine backend crash (any other exception
    TestClient can propagate) passed through _write_and_reraise unnoticed
    -- exactly reproduced by the audit with a monkeypatched run_plan()
    raising RuntimeError. Broadened to `except Exception` everywhere."""
    import sys
    monkeypatch.setattr(sys.modules[__name__], "FAILURES_DIR", tmp_path)

    machine = CoordinatorVariantBMachine()
    machine.setup_fresh_object(seed=1)

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated backend crash")

    monkeypatch.setattr(sim, "run_plan", _boom)
    with pytest.raises(RuntimeError):
        machine.do_plan()
    machine.teardown()

    failure_files = list(tmp_path.glob("*.json"))
    assert failure_files, "a non-AssertionError backend failure must still write a failure JSON"
    payload = json.loads(failure_files[0].read_text(encoding="utf-8"))
    assert payload["stage"] == "plan"
    assert payload["seed"] == 1


# ===========================================================================
# Checkpoint C -- Hypothesis stateful, real backend
# ===========================================================================

# Measured, not guessed (tasks/ROTA-T044/round_01/tests/hypothesis_profile_measurement.md):
# ~9.89s/full-cycle example on this machine -> default profile stays well
# under Wariant A's measured ~750s full-portfolio run.
_DEFAULT_MAX_EXAMPLES = 8
_DEFAULT_STEP_COUNT = 4
_FULL_MAX_EXAMPLES = 30
_FULL_STEP_COUNT = 8
_USE_FULL_PROFILE = os.environ.get("ROTA_SIM_VARIANT_B_FULL") == "1"


def _write_failure_json_b(name: str, payload: dict) -> None:
    """OWNER-08 (TASK_CHATGPT.md section 10): a real, complete, machine-
    readable artifact per harness violation/awaria -- run id, generated
    catalog/month, calculator result and declared roster, targets and
    absences, action ordering, decision payloads, returned Assignments.
    Hypothesis's own failure printout already gives an executable
    `--hypothesis-seed=...` reproduction command for the state machine
    (T44-B-18's "gotowa komenda"); this artifact adds the full structured
    snapshot Hypothesis's printout does not capture on its own."""
    FAILURES_DIR.mkdir(parents=True, exist_ok=True)
    (FAILURES_DIR / f"{name}.json").write_text(
        json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8",
    )


class CoordinatorVariantBMachine(RuleBasedStateMachine):
    """Real backend, fresh SQLite :memory: + fresh Site per Hypothesis
    example (via @initialize, run exactly once per example). Preconditions
    keep the harness from generating illegal action orderings; a bad
    PRODUCT result (DECISION_REQUIRED forever, TECHNICAL_ERROR, an unfair
    FEASIBLE spread, ...) is a finding to keep, never something this
    machine tries to repair."""

    def __init__(self):
        super().__init__()
        self.connection = None
        self.client = None
        self.spec = None
        self.absence_draws: list = []
        self.plan_result = None
        self.final_result = None
        self.externals: list[dict] = []
        self.has_selected = False
        self.replan_results: list[dict] = []
        self.action_log: list[str] = []

    @initialize(seed=st.integers(min_value=0, max_value=2_000_000_000))
    def setup_fresh_object(self, seed):
        self.connection = connect(":memory:")
        app.dependency_overrides[get_conn] = lambda: (yield self.connection)
        self.client = TestClient(app)
        self.plan_result = None
        self.final_result = None
        self.externals = []
        self.has_selected = False
        self.replan_results = []
        self.action_log = []
        try:
            self.spec = sim.random_object_spec_b(seed)
            sim.assert_headcount_b(self.spec)
            self.action_log.append("build_object_b")
            self.site_id = sim.build_object_b(self.client, self.spec)
            rng = random.Random(seed * 104729 + 1)
            self.absence_draws = sim.initial_absences_b(self.spec, rng)
            self.action_log.append("apply_absences_b")
            sim.apply_absences_b(self.client, self.site_id, self.spec, self.absence_draws)
        except Exception as exc:
            self._write_and_reraise("setup", exc)

    def _snapshot(self, stage: str) -> dict:
        return {
            "stage": stage, "seed": self.spec.seed if self.spec else None,
            "month": self.spec.month.isoformat() if self.spec else None,
            "regime": self.spec.regime if self.spec else None,
            "atoms": [vars(a) for a in self.spec.atoms] if self.spec else None,
            "declared_local": sim.declared_roster_b(self.spec) if self.spec else None,
            "calculator_result": sim.layered_headcount_b(self.spec.atoms) if self.spec else None,
            "target_hours_per_employee": self.spec.target_hours_per_employee if self.spec else None,
            "absence_draws": [vars(d) for d in self.absence_draws],
            "action_log": self.action_log,
            "plan_result": self.plan_result, "externals": self.externals, "final_result": self.final_result,
            "selected": self.has_selected, "replan_results": self.replan_results,
            "reproduction": sim.reproduction_command_b(self.spec.seed, len(self.replan_results)) if self.spec else None,
        }

    def _write_and_reraise(self, stage: str, exc: Exception) -> None:
        _write_failure_json_b(f"stateful-seed{self.spec.seed if self.spec else 'unknown'}-{stage}", self._snapshot(stage))
        raise exc

    @rule()
    @precondition(lambda self: self.spec is not None and self.plan_result is None)
    def do_plan(self):
        try:
            self.action_log.append("run_plan")
            self.plan_result = sim.run_plan(self.client, self.site_id, self.spec.month)
            self.final_result = self.plan_result
            if self.plan_result["status"] == "DECISION_REQUIRED" and self.plan_result.get("decision_payload"):
                self.action_log.append("run_with_external_loop_b")
                loop = sim.run_with_external_loop_b(self.client, self.site_id, self.spec.month, self.spec, self.plan_result)
                self.externals = loop["externals"]
                self.final_result = loop["final_result"]
            assert self.plan_result["status"] in _KNOWN_PLAN_STATUSES
        except Exception as exc:
            self._write_and_reraise("plan", exc)

    @rule()
    @precondition(lambda self: self.plan_result is not None and not self.has_selected and self.final_result["status"] == "FEASIBLE")
    def do_select_candidate(self):
        try:
            self.action_log.append("select_first_candidate")
            sim.select_first_candidate(self.client, self.site_id, self.spec.month, self.final_result)
            self.has_selected = True
        except Exception as exc:
            self._write_and_reraise("select_candidate", exc)

    @rule()
    @precondition(lambda self: self.has_selected)
    def do_replan(self):
        try:
            self.action_log.append("run_replan")
            result = sim.run_replan(self.client, self.site_id, self.spec.month)
            assert result["status"] in _KNOWN_PLAN_STATUSES
            self.replan_results.append(result)
        except Exception as exc:
            self._write_and_reraise("replan", exc)

    @rule()
    def observe(self):
        """Always-available no-op: a terminal PLAN outcome (TECHNICAL_ERROR,
        an exhausted DECISION_REQUIRED, NARROW_SEARCH_EXHAUSTED, ...) leaves
        do_plan/do_select_candidate/do_replan all without a true
        precondition -- Hypothesis's RuleBasedStateMachine requires at
        least one rule to always be valid, or it raises InvalidDefinition
        instead of just ending the example. This changes nothing; the
        @invariant() below still runs after it."""

    @invariant()
    def headcount_and_closed_world_hold(self):
        if self.spec is None:
            return
        try:
            sim.assert_headcount_b(self.spec)
            declared = sim.declared_roster_b(self.spec)
            external_ids = [e["external_employee_id"] for e in self.externals]
            if self.final_result is not None and self.final_result["status"] == "FEASIBLE":
                sim.assert_closed_world_b(sim.all_candidate_assignments_b(self.final_result), declared, external_ids)
            for replan_result in self.replan_results:
                if replan_result["status"] == "FEASIBLE":
                    sim.assert_closed_world_b(sim.all_candidate_assignments_b(replan_result), declared, external_ids)
        except Exception as exc:
            self._write_and_reraise("invariant", exc)

    def teardown(self):
        if self.connection is not None:
            app.dependency_overrides.pop(get_conn, None)
            self.connection.close()


TestVariantBStateMachine = CoordinatorVariantBMachine.TestCase
TestVariantBStateMachine.settings = settings(
    max_examples=_FULL_MAX_EXAMPLES if _USE_FULL_PROFILE else _DEFAULT_MAX_EXAMPLES,
    stateful_step_count=_FULL_STEP_COUNT if _USE_FULL_PROFILE else _DEFAULT_STEP_COUNT,
    database=None, deadline=None, derandomize=False,
)


def test_two_distinct_run_identifiers_generate_different_canonical_objects():
    """Explicit, deterministic proof of real variety (brief 1.3): two
    named identifiers (not 'usually differs') produce different objects."""
    RUN_A, RUN_B = 111, 222
    spec_a = sim.random_object_spec_b(RUN_A)
    spec_b = sim.random_object_spec_b(RUN_B)
    assert (spec_a.month, spec_a.atoms) != (spec_b.month, spec_b.atoms)
    # Same identifier reproduces the same canonical object -- reproduction
    # relies on this, not on Hypothesis's own example database (database=None).
    spec_a_again = sim.random_object_spec_b(RUN_A)
    assert (spec_a.month, spec_a.atoms) == (spec_a_again.month, spec_a_again.atoms)


# ===========================================================================
# Targeted Wariant A regression (TASK_CHATGPT.md OWNER-05: must still pass,
# contract unchanged) -- re-imports and re-runs one cheap Wariant A vertical
# rather than duplicating its full suite, which stays test_coordinator_simulator.py's job.
# ===========================================================================

def test_variant_a_headcount_rule_is_unaffected_by_variant_b():
    spec_a = sim.random_object_spec(0, date(2026, 9, 1))
    assert spec_a.employee_count == 5 * spec_a.layer_count  # R4 frozen rule, untouched

from __future__ import annotations

import ast
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest

from tools import solver_scenario_lab as lab


def _real_candidate(family: str = "ordinary_12h_single_5", seed: int = 10):
    spec = lab.build_scenario(family, seed)
    conn = lab.connect(":memory:")
    commands = []
    lab._bootstrap(conn, spec, commands)
    lab._apply_initial_decisions(conn, spec, commands)
    result = lab.plan_month(
        conn, site_id=spec.site_id, month=spec.month,
        coordinator_id=spec.coordinator_id, effective_from=spec.month,
    )
    assert result.status == "FEASIBLE"
    state, _ = lab.assemble_planning_state(conn, site_id=spec.site_id, month=spec.month)
    return conn, spec, state, result.candidates[0]


def test_six_object_variants_have_owner_accepted_roster_sizes_and_targets():
    expected = {
        "ordinary_12h_single_5": (12, 1, 5),
        "ordinary_12h_double_10": (12, 2, 10),
        "ochrona_24h_single_4": (24, 1, 4),
        "ochrona_24h_single_5": (24, 1, 5),
        "ochrona_24h_double_8": (24, 2, 8),
        "ochrona_24h_double_10": (24, 2, 10),
    }
    for family, shape in expected.items():
        spec = lab.build_scenario(family, 10)
        assert (spec.shift_hours, spec.required_primary_count, len(spec.local_employee_ids)) == shape
        assert spec.target_hours == 168
        assert spec.external_employee_id.startswith("LAB-EXTERNAL-")
        assert spec.external_employee_id not in spec.local_employee_ids


def test_month_shapes_include_28_29_30_31_and_february_roster_does_not_shrink():
    specs = [lab.build_scenario(v.name, 10) for v in lab.OBJECT_VARIANTS[:4]]
    assert {lab.calendar.monthrange(s.month.year, s.month.month)[1] for s in specs} == {28, 29, 30, 31}
    assert len(lab.build_scenario("ordinary_12h_single_5", 10).local_employee_ids) == 5


def test_generation_is_deterministic_and_seed_changes_real_input():
    one = lab.build_scenario("ordinary_12h_single_5", 11)
    replay = lab.build_scenario("ordinary_12h_single_5", 11)
    other = lab.build_scenario("ordinary_12h_single_5", 12)
    assert one == replay
    assert one.summary() == replay.summary()
    assert one.summary() != other.summary()


def test_seed_conditions_cover_baseline_leave_sickness_matrix_and_shortage():
    conditions = [lab.build_scenario("ordinary_12h_single_5", seed).condition for seed in range(10, 15)]
    assert conditions == list(lab.CONDITIONS)
    leave = lab.build_scenario("ordinary_12h_single_5", 11)
    assert leave.leave is not None
    assert (leave.leave.end_date - leave.leave.start_date).days == 13
    sickness = lab.build_scenario("ordinary_12h_single_5", 12).sickness
    assert sickness is not None and 1 <= (sickness.end_date - sickness.start_date).days + 1 <= 21


@pytest.mark.parametrize("family", [variant.name for variant in lab.OBJECT_VARIANTS])
def test_real_baseline_runs_on_production_seams_and_uses_fresh_memory_database(family, monkeypatch):
    opened = []
    real_connect = lab.connect

    def tracked(path):
        opened.append(path)
        return real_connect(path)

    monkeypatch.setattr(lab, "connect", tracked)
    outcome = lab.execute_scenario(lab.build_scenario(family, 10))
    assert outcome.ok, outcome.message
    assert outcome.statuses and all(status in ("FEASIBLE", "DECISION_REQUIRED") for status in outcome.statuses)
    assert opened == [":memory:"]
    assert not any(c["command"] == "add_external_support_window" for c in outcome.commands)


def test_sickness_is_written_after_selected_baseline_and_uses_replan():
    spec = lab.build_scenario("ordinary_12h_single_5", 12)
    outcome = lab.execute_scenario(spec)
    assert outcome.ok, outcome.message
    names = [item["command"] for item in outcome.commands]
    assert "append_availability" in names
    assert "replan" in names
    assert names.index("replan") > names.index("append_availability")


def test_leave_and_sickness_may_overlap_for_same_employee():
    spec = lab.build_scenario("ordinary_12h_single_5", 11)
    assert spec.leave is not None and spec.sickness is not None
    assert spec.leave.employee_id == spec.sickness.employee_id
    assert spec.leave.start_date <= spec.sickness.end_date
    assert spec.sickness.start_date <= spec.leave.end_date
    outcome = lab.execute_scenario(spec)
    assert outcome.ok, outcome.message


def test_matrix_decision_uses_production_wrapper():
    outcome = lab.execute_scenario(lab.build_scenario("ordinary_12h_single_5", 13))
    assert outcome.ok, outcome.message
    matrix_commands = [c["command"] for c in outcome.commands if "unavailability" in c["command"]]
    assert matrix_commands in (["create_employee_shift_unavailability"], ["create_employee_weekday_unavailability"])


def test_external_window_is_created_only_after_real_proposal_and_use_is_reported():
    outcome = lab.execute_scenario(lab.build_scenario("ordinary_12h_single_5", 14))
    assert outcome.ok, outcome.message
    assert outcome.statuses == ["DECISION_REQUIRED", "FEASIBLE"]
    commands = [c["command"] for c in outcome.commands]
    assert commands.count("add_external_support_window") == 1
    assert commands.index("add_external_support_window") > commands.index("plan_month")
    assert outcome.external_assignments
    assert {a["employee_id"] for a in outcome.external_assignments} == {"LAB-EXTERNAL-14"}


@pytest.mark.parametrize("mutation, expected", [
    (lambda a: replace(a, employee_id="FOREIGN"), "foreign employee"),
    (lambda a: replace(a, covers_demand_id="FOREIGN"), "foreign demand"),
    (lambda a: replace(a, covers_demand_id=None), "not demand-backed"),
    (lambda a: replace(a, end_datetime=a.end_datetime + timedelta(hours=1)), "extra hours"),
])
def test_closed_world_rejects_candidate_mutants_independent_of_validator(mutation, expected):
    conn, spec, state, candidate = _real_candidate()
    try:
        mutant = [mutation(candidate[0]), *candidate[1:]]
        problems = lab.check_closed_world(state, mutant, spec, external_enabled=False)
        assert any(expected in problem for problem in problems)
    finally:
        conn.close()


def test_closed_world_rejects_external_before_consent():
    conn, spec, state, candidate = _real_candidate()
    try:
        mutant = [replace(candidate[0], employee_id=spec.external_employee_id), *candidate[1:]]
        problems = lab.check_closed_world(state, mutant, spec, external_enabled=False)
        assert "external employee used before coordinator consent" in problems
    finally:
        conn.close()


def test_source_uses_only_authorized_architecture_and_line_limits():
    source_path = Path(lab.__file__)
    test_path = Path(__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert not any((getattr(node, "module", "") or "").startswith("api") for node in imports)
    assert ".execute(" not in source
    calls = {getattr(node.func, "id", None) for node in ast.walk(tree) if isinstance(node, ast.Call)}
    assert not {"PlanningState", "ShiftDemand"} & calls
    assert len(source.splitlines()) <= 600
    assert len(test_path.read_text(encoding="utf-8").splitlines()) <= 600


def test_failure_record_is_replayable_safe_and_never_overwritten(tmp_path, monkeypatch):
    spec = lab.build_scenario("ordinary_12h_single_5", 10)
    outcome = lab.CaseOutcome(False, "CANDIDATE_INVALID", "broken", ["FEASIBLE"],
                              [{"command": "plan_month", "input": {}}], spec.summary(), [], [], [])
    monkeypatch.setattr(lab, "_build_sha", lambda: "TEST-SHA")
    path = lab._write_failure(tmp_path, 99, 0, spec, outcome)
    before = path.read_bytes()
    payload = lab.json.loads(before)
    assert payload["build_sha"] == "TEST-SHA"
    assert f"--family {spec.family} --case-seed {spec.case_seed}" in payload["replay"]
    assert payload["replay"].endswith("--expected-sha TEST-SHA")
    assert "LAB-" in path.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        lab._write_failure(tmp_path, 99, 0, spec, outcome)
    assert path.read_bytes() == before


def test_pass_writes_no_file_and_cli_summary_is_exact(tmp_path, monkeypatch, capsys):
    spec = lab.build_scenario("ordinary_12h_single_5", 10)
    good = lab.CaseOutcome(True, "PASS", "", ["FEASIBLE"], [], spec.summary(), [], [], [])
    monkeypatch.setattr(lab, "execute_scenario", lambda ignored: good)
    assert lab.run_cases(cases=1, seed=77, output_dir=tmp_path) == 0
    assert capsys.readouterr().out.strip() == "CASES=1 PASS=1 FAIL=0 SEED=77"
    assert not list(tmp_path.rglob("*.json"))


def test_replay_warns_when_build_sha_differs(monkeypatch, capsys):
    spec = lab.build_scenario("ordinary_12h_single_5", 10)
    good = lab.CaseOutcome(True, "PASS", "", ["FEASIBLE"], [], spec.summary(), [], [], [])
    monkeypatch.setattr(lab, "execute_scenario", lambda ignored: good)
    monkeypatch.setattr(lab, "_build_sha", lambda: "CURRENT")
    assert lab.main(["--family", spec.family, "--case-seed", "10", "--expected-sha", "OLD"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "WARNING replay SHA=OLD differs from current SHA=CURRENT"


@pytest.mark.parametrize("argv", [["--cases", "0"], ["--family", "ordinary_12h_single_5"], ["--case-seed", "1"]])
def test_cli_rejects_invalid_argument_combinations(argv):
    with pytest.raises(SystemExit) as exc:
        lab.main(argv)
    assert exc.value.code == 2

# DELIVERY r1 — ROTA-PRESERVED-FACTS-REPLAN

EXACT SHA under audit: b25956387eb1840f1f8246da88b630cd16e020ee. BASE (repo_before.hash): 5371a53d00960702628067d278d6c96e392fa911 (brief a6b2ac6 + main 81c264b + carried Codex precheck tests_r1.txt 58baf63).
CC merit review: brief ACCEPTED (matches OWNER 2026-10-16: coordinator decisions preserved, automat obeys rules for new proposals).

## Change (brief §3 A/B/C)
- NEW rota/planning/preserved_violations.py — single owner used by engine and plan_ops.select_candidate. Three classes only:
  (1) THIRD-CONSECUTIVE-SHIFT-01 and (2) NIGHT-STREAK-01 whose ids are all fixed_existing_assignments the candidate carries unchanged (empty ids = all boundary);
  (3) COVERAGE-01 (single demand, no ids) where at least one already-started PRIMARY+CANCELLED+NN fact (solver._historical_nn_facts, kept field-for-field in the candidate) attributes to that demand AND counting those NN back in (via _attributed_overlap_intervals + coverage_segments) makes EVERY segment exactly required -> no leftover gap, no excess. NN is cause, never coverage. gating_hard_pass: hard_pass=False with empty details stays False.
- engine.py: _evaluate_candidate / _feasible_result alternatives / _has_non_load_violations / _split_frozen_violations use the owner; old _is_fully_historical_third_shift/_gating_hard_pass removed (moved, semantics kept + unchanged-fact check). Validator report never edited.
- plan_ops.select_candidate: Przelicz acceptance uses gating_hard_pass with ONE cutover_at captured before validation and reused by the existing pre_check / recorded_at; first PLAN (no source version) stays strict report.hard_pass; child deviations = materialize_deviations(report) (empty for ordinary candidates; real COVERAGE/LAW Deviations, unacknowledged, for preserved ones). _coerce_unproven_realized_to_planned, cutover pre_check, atomicity untouched.
- constraints.py: night window starts [month_start-2, month_end] (T058-symmetric); fully-fixed night window skipped instead of model.add(3<=2).
- validator_checks_patterns._check_night_streak: same window (boundary context to month_end+2).

## FLAG for Codex/architect — one necessary extension beyond the literal §3A text (TRACE)
R2 (frozen manual N/N/N must replan) still went DECISION_REQUIRED after 3A: the same trio is also a THIRD-CONSECUTIVE-SHIFT-01 window, and T058's existing fully-fixed skip (_third_shift_window_assumption) only fired when all three terms were plain ints. With an open same-date D slot for the same employee the term is "fixed 1 + BoolVar", so the window looked mixed and got sum(occupied)<=2 with occupied forced 1 on all three dates -> INFEASIBLE. Experiment: solve() INFEASIBLE even with night constraints removed; feasible after the fix.
Fix: constraints._fixed_part(term) reads the constant component (int / LinearExpr int_offset / unit-coefficient IntAffine offset; anything else -> 0 = conservative, old behaviour). A window whose every date has fixed part >= 1 is the same fully-fixed historical window T058 §2.3A already exempts; applied to the T058 window and the night window. solver.py untouched; fixed_existing_assignments, objective, weights, fairness, budgets untouched. Note: _fixed_part relies on solver._build_day_kind_terms adding slot vars before fixed ints (verified: 0+x+...+1 -> int_offset 1); other orders return 0 (no skip).

## Evidence
- base_repro.txt: new R1/R2/R3 tests against BASE production files: 6 failed (R1 NN TECHNICAL_ERROR, R2 x4, R3 fourth-night), month-end validator test: 2 failed; all pass at exact SHA.
- tests/test_preserved_facts_replan.py: 14 passed. R1 real mark-not-worked -> POST plan -> select-candidate -> readback (NN exact, gap = COVERAGE Deviation on that demand, parent unchanged). R2 real manual-correction N/N/N (LAW + T058 freeze) on the live current month -> plan FEASIBLE -> accept -> LAW Deviation unacked (skips if < 3 free days left in month); frozen/started/REALIZED variants via engine.plan. R3 month-end (Mar, Dec->Jan) + no fourth night next to a fixed trio. R4 classifier negatives (other demand, future NN vs cutover, dropped/altered NN, plain CANCELLED, excess, required 2 with one NN). R5 forged candidates (NN dropped / NN turned into work) rejected via HTTP with current unchanged; preserved+new REST-01 still gates; empty details stays False.
- affected_area_tests.txt: every tests/*.py touching NIGHT-STREAK/NN/select_candidate/cutover/DECISION_REQUIRED/constraints (69 files): 925 passed, 1 skipped. Earlier run before the _fixed_part change: 911 passed. No existing test modified. No full regression (brief).
- WHERE_MAP: where_map_after.txt (run on committed SHA; where.py reads git, not the working tree).

## backend.py (verbatim head, full in backend_r1.txt)
STATUS: FAIL
HEAD_SHA: b25956387eb1840f1f8246da88b630cd16e020ee
REASON: SIZE_FILE constraints.py 795 / engine.py 952 / plan_ops.py 857; SIZE_FUNC add_max_two_consecutive_night_constraints 66, _check_third_consecutive_shift 82, _plan_requiring_different_result_narrow 123, plan_month 135, tests/test_t058.py::test_t58_15 65.
CC: all pre-existing at BASE (sizes: constraints 770, engine 984, plan_ops 845; night fn 61, others identical); the brief forbids splitting these files. Only growth: constraints +25 (docstrings + _fixed_part), night fn +5 docstring lines; engine shrank. Owner decision on the gate exception required.

## For Codex
Audit exact SHA b259563 in your own worktree; report round_01/tests/tests_r2.txt on audit/rota-preserved-facts-precheck (r1 kept); update only your BOARD row; no commits to task branch; no merge. Please falsify especially: _fixed_part soundness/conservatism, NN coverage attribution with multi-person/partial intervals, select_candidate clock sharing, no new HARD relaxation for new proposals.

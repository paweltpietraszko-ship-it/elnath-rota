# ROTA-T023b — ARCHITECT IMPLEMENTATION REVIEW

DATE: 2026-08-23
IMPLEMENTATION_SHA_REVIEWED: `ea91176f1c21999f455836857dee9d45026088fb`
EVIDENCE_HEAD_BEFORE_THIS_REVIEW: `c819080db4000988b1c5f23e072bcd8053ac7f73`
CONTRACT_HEAD: `50ac0cb1c6b09661dbd16d15c3bad8228f995507`
R8_REPORT: `tasks/ROTA-T023b/round_01/tests/tests_r8.txt`

## REVIEW MODE

This is the architect's own exact-SHA technical + substantive review. I did **not** rerun CC/Codex tests or quality gates. Reported execution evidence from R8 is treated as evidence, while product semantics and ownership were independently reviewed in source.

## OWNER DELIVERY DECISION RECORDED

Owner accepts the backend delivery exceptions described by R8 / `backend_output_r6fix.txt`:

- NEW_FILES over the historical limit;
- SIZE_FILE / SIZE_FUNC hits caused by mechanically touched pre-existing oversized test files/functions;
- RATIO and TOTAL_LINES exceptions for this task.

Owner also accepts excluding the obsolete T023 Checkpoint-B source-diff proof `test_t23_54_t012_legality_rest_modules_unmodified_by_checkpoint_b` from T023b delivery. That test freezes that T023 must not modify `constraints.py` / `work_periods.py`; T023b explicitly and deliberately supersedes that source-shape assumption. This exclusion does not waive behavioural T023 regressions.

These accepted delivery exceptions are not product defects and do not require product-code shrinking solely to make historical size/source-diff gates green.

## CONFIRMED — R5-3 / REGIME PROVENANCE

R5-3 is architecturally closed.

- `Site.planning_regime` is explicit and ordinary Site writes cannot change it.
- the exceptional correction command is separately authorized/audited;
- ScheduleVersion persists planning-regime provenance;
- `version_requires_regime_replan()` derives the obligation after restart from persisted facts;
- finalize / restore fail closed on regime-stale PLANNED content;
- selected-candidate persistence is the normal automatic path that adopts current Site regime provenance;
- PDF presentation fails closed while regime replan is required.

No additional lifecycle state/table is needed.

## PRODUCT FINDING A1 — WEEKLY-REST-01 BOUNDARY PARITY GAP

**VERDICT: BLOCKER — PRODUCT PASS NOT YET CONFIRMED BY ARCHITECT.**

Frozen addendum §4/§6 says T023b uses recorded target-Site work and clips work intervals to the complete weekly window. Therefore target-Site work beginning in the previous month and continuing past midnight on day 1 is occupied time inside the first settlement week.

The canonical assembler already exposes this existing fact as same-Site `state.boundary_assignments`; its context read is intentionally unbounded and excludes only the target ScheduleVersion.

Solver behaviour is correct: `solve()` builds WEEKLY target fixed intervals from `fixed_existing_assignments + state.boundary_assignments` while explicitly excluding `state.other_site_assignments`.

Independent validator behaviour is narrower: `_check_weekly_rest()` groups only the `assignments` argument passed to `validate()` and does not add non-CANCELLED `state.boundary_assignments`.

Manual weekly REST-override reconstruction mirrors the same narrower input: `_weekly_rest_override_facts()` uses only `corrected_assignments`.

Consequences:

1. solver and independent validator do not implement identical WEEKLY-REST-01 facts;
2. a same-Site shift crossing from the previous month into day 1 can reduce the first week's uninterrupted rest in solver but be invisible to validator;
3. manual correction / fresh finalize validation can therefore miss that weekly violation and persist/finalize without the required `WEEKLY-REST-01` LAW deviation / REST override record.

This is not a new cross-Site or hypothetical external-work case. It is an existing reachable same-Site month-boundary Assignment supplied by the canonical assembler.

### Minimal required correction

Do not redesign the task. Keep solver unchanged.

- `_check_weekly_rest()` must evaluate non-CANCELLED target candidate/current Assignments **plus non-CANCELLED `state.boundary_assignments`**, then clip them through the existing pure weekly oracle.
- `_weekly_rest_override_facts()` must reconstruct from the same target-Site fact set.
- add one focused regression where previous-month same-Site work overlaps day 1 and changes the 35h outcome; prove validator/manual facts match the solver/pure oracle.
- `state.other_site_assignments` remains excluded.

No new module, status, table, action kind, lifecycle workflow, legal rule or contract redesign is authorized by this finding.

## TECHNICAL / SUBSTANTIVE RESULT

Reported R8 execution evidence is strong and all previously reported product findings, including R5-3, are closed. The backend size/diff exceptions and obsolete T023 source-diff proof are accepted by owner.

However, source review found A1 above. Therefore the architect's current result is:

**FAIL — ONE NARROW PRODUCT CORRECTION REQUIRED (WEEKLY-REST-01 SAME-SITE BOUNDARY PARITY).**

CC does not need another broad architecture or Codex design round. After the narrow A1 correction, provide the exact implementation SHA and the focused result; architect can issue the final exact-SHA delivery verdict. Merge remains an explicit owner action.

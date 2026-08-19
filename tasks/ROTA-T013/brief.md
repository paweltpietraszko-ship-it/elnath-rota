# ROTA-T013 — coordinator-facing DECISION_REQUIRED guidance

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — ROUND 2 — NOT READY FOR CC
DATE: 2026-08-19
TASK_ID: ROTA-T013
BASE_SHA: 5b35e3225f546bc7763c51b34e8a7ebe77553b58
BASE_BRANCH: main
TASK_BRANCH: task/ROTA-T013
OWNER_SOURCE: arch/T013_solver_communication_architect_brief.md
FROZEN_ADDENDUM: arch/FROZEN_ADDENDUM_DECISION_REQUIRED_COORDINATOR_COMMUNICATION_01.md
DEPENDS_ON: T012 + T016 + T018 merged on main
PREIMPLEMENTATION_ROUND_1: FAIL — T013-R1-1 LEGACY TEST SCOPE AMENDMENT REQUIRED; all other Round 1 sections remain CLOSED/PASS

## CEL

Końcowy `DECISION_REQUIRED` ma mówić koordynatorowi po ludzku:
- co realnie blokuje grafik;
- jakie konkretne decyzje są istotne w tej sytuacji;
- albo że przy obecnej obsadzie i zapisanych ograniczeniach nie ma automatycznego rozwiązania.

Nie pokazywać koordynatorowi drogi solvera do tego wyniku.

T013 jest zadaniem komunikacji istniejących autonomy boundaries. Nie tworzy nowych reguł produktowych ani nowego sposobu planowania.

## BASELINE — POST T018 IS FROZEN INPUT

Projekt powstaje na exact `main` SHA `5b35e3225f546bc7763c51b34e8a7ebe77553b58`, który zawiera zmergowane T018.

Literalna kolejność T018 pozostaje:
1. NORMAL capped — DAY_ONLY fallback OFF, emergency 24h OFF;
2. DAY_ONLY fallback capped — fallback ON, emergency 24h OFF;
3. DAY_ONLY + emergency 24h capped;
4. uncapped LOAD diagnosis z oboma capability ON.

T013 NIE może:
- zakończyć planowania komunikatem po Stage 1/2, jeśli istnieje jeszcze automatyczny kolejny stage;
- cofnąć DAY_ONLY do ordinary bypass;
- emitować `Zmień Nocka` zanim aktualny T018 DAY_ONLY fallback został wyczerpany;
- zmienić emergency-24h T012;
- zmienić absence accounting T018 A;
- użyć technical status jako dowodu dla coordinator decision.

## CURRENT SHAPE

`DecisionRequiredPayload` pozostaje bez zmian:
- `blocking_shift_demands`;
- `blockers: list[Blocker]`;
- `load_blocker`;
- `unblocking_options: list[str]`.

`Blocker` pozostaje:
- `employee_id`;
- `condition: str`.

Nie dodawać nowego DTO ani publicznego pola raw/human condition.

## ARCHITECTURE CHOICE

Wprowadzić jeden pure module:
`rota/planning/decision_guidance.py`.

To jest owner końcowego coordinator-facing payloadu, nie nowa warstwa workflow.

Minimalny odpowiedzialny kształt:
- `render_coordinator_blockers(state, raw_blockers) -> list[Blocker]` lub równoważny pure helper;
- `build_unblocking_options(state, raw_blockers, load_blocker, *, frozen_boundary=False) -> list[str]` lub równoważny pure helper;
- opcjonalnie jeden `build_decision_payload(...)`, jeżeli usuwa duplikację czterech konstruktorów engine.

Nie tworzyć równoległych modeli.

## TASK_SCOPE

TASK_SCOPE:
- arch/T013_solver_communication_architect_brief.md
- arch/FROZEN_ADDENDUM_DECISION_REQUIRED_COORDINATOR_COMMUNICATION_01.md
- tasks/ROTA-T013/brief.md
- rota/planning/decision_guidance.py
- rota/planning/engine.py
- tests/test_t013.py
- tests/test_audit_r12_findings.py
- tests/test_audit_r13_findings.py
- tests/test_audit_r17_findings.py
- tests/test_audit_r20_r21_findings.py
- tests/test_audit_r22_findings.py
- tests/test_audit_r25_findings.py
- tests/test_audit_r26_findings.py
- tests/test_audit_t007_r3.py
- tests/test_audit_t007_r4.py
- tests/test_audit_t007_r5.py
- tests/test_sick_leave.py
- tests/test_site_rules_execution.py
- tests/test_t016_emp02_retirement.py
- tests/test_t018.py

Żaden inny plik bez STOP + amendment architekta.

## EXPLICITLY OUT OF SCOPE

Nie zmieniać:
- arch/spec.md;
- arch/FROZEN.lock;
- rota/domain.py;
- rota/planning/engine_types.py;
- rota/planning/solver.py;
- rota/planning/eligibility.py;
- rota/planning/validator.py;
- rota/planning/site_rules.py;
- rota/planning/constraints.py;
- rota/planning/work_periods.py;
- rota/application/*;
- rota/persistence/*;
- persistence schema.

Jeżeli implementacja wymaga zmiany któregokolwiek z powyższych, STOP przed edycją i wrócić do architekta z konkretnym blockerem.

## NEW_FILES

Dozwolone nowe pliki:
- `arch/T013_solver_communication_architect_brief.md` — owner source;
- `arch/FROZEN_ADDENDUM_DECISION_REQUIRED_COORDINATOR_COMMUNICATION_01.md` — frozen product addendum;
- `tasks/ROTA-T013/brief.md` — task contract;
- `rota/planning/decision_guidance.py` — jeden pure production module;
- `tests/test_t013.py` — dedykowane oracles T013.

Zero nowych DTO/model/persistence modules.

## A. FINAL PAYLOAD BOUNDARY

T013 działa wyłącznie przy tworzeniu KOŃCOWEGO `DecisionRequiredPayload`.

`_dispatch_or_continue()` Stage 1/2 T018 pozostaje bez coordinator guidance i nadal zwraca `None` dla retryable INFEASIBLE/unassignable.

Coordinator guidance może zostać zbudowane dopiero w istniejących terminalnych ścieżkach:
1. `_decision_for_unassignable`;
2. `_decision_for_conflict`;
3. `_decision_for_conflicts`;
4. `_load_decision`.

`_decision_for_load` pozostaje istniejącym validator wrapperem i finalnie używa tej samej polityki przez `_load_decision` albo `_decision_for_conflicts`.

## B. RAW FACTS MUST NOT BE REDEFINED

Engine nadal buduje raw blockers z:
- `SolverOutcome.unassignable_reasons`;
- `eligible_employees_for_demands` + `REST-01`;
- `site_rule_exclusions`;
- exhaustive frozen `ViolationDetail`;
- LOAD report.

T013 nie przepina diagnostyki na inne źródło i nie zmienia priorytetów eligibility.

Guidance builder dostaje raw `Blocker` i finalne path facts, a następnie renderuje coordinator-facing payload.

## C. BLOCKER RENDERING

Implementacja exact mapping z frozen addendum.

Wymagane built-in coordinator conditions:
- `UNAVAILABLE-01` -> `Koliduje z checkbox: Ogólna dostępność`;
- `DAY_ONLY-01` -> `Koliduje z checkbox: Nocka`;
- `SICK_LEAVE-01` -> `Koliduje z zapisem: Chorobowe`;
- `LEAVE_GRANTED-01` -> `Koliduje z zapisem: Urlop`;
- `REST-01` -> `Koliduje z odpoczynkiem dobowym`;
- `LOAD-01` -> `Koliduje z tygodniowym czasem pracy`;
- `EXTERNAL-01` / `EXTERNAL_SUPPORT_DISABLED` -> `Wsparcie zewnętrzne`;
- `SHIFT-24-01` -> `Koliduje z checkbox: 24`;
- `DAY_SHIFT_OFF-01` -> literal raw code unchanged.

Raw membership conditions are omitted.

Raw `INSUFFICIENT_COVERAGE` / `UNKNOWN` are internal and omitted.

## D. SITE RULE DISPLAY

Rozpoznać raw condition jako SiteRule wyłącznie przez exact membership w `{rule.rule_version_id: rule}` z `state.site_rules`.

Jeżeli matched:
- nonblank `rule.description` -> exact stripped description jako coordinator condition;
- blank/None -> `Koliduje z zapisaną regułą obiektu`.

Nie używać `rule_id`, `rule_version_id`, `source` ani `reason` jako automatycznego fallbacku opisu.

Nie robić repository lookup.

## E. MEMBERSHIP / ROSTER AUTONOMY

`MEMBERSHIP_DISABLED` i `MEMBERSHIP-01` są invisible.

Nie tworzyć na ich podstawie opcji:
- `dodaj pracownika`;
- `włącz membership`;
- `przywróć do obsady`;
- żadnej równoważnej sugestii konkretnego kandydata.

Program nie mutuje obsady.

## F. DYNAMIC GUIDANCE — NO STATIC LISTS

Usunąć obecne hardcoded `unblocking_options=[...]` z czterech finalnych konstruktorów.

Nowa lista jest liczona z raw final blockers/facts.

Wybrana technika T013: evidence-backed heuristic per blocker/final path fact.

Nie wykonywać dodatkowych solver runs tylko po to, aby zbudować tekst.

Nie budować hipotetycznego PlanningState, nie dodawać diagnostic override flags.

### F1. Employee scoped groups

Dla action family zbierać unique employee IDs z raw blockerów i renderować nazwy z `Employee.display_name`.

Stabilny fallback, gdy employee nie istnieje w `state.employees`: `employee_id`.

Nazwy unique, deterministic sort.

### F2. Exact action templates

- `UNAVAILABLE-01` -> `Zmień Ogólna dostępność: <names>`;
- `DAY_ONLY-01` -> `Zmień Nocka: <names>`;
- `SHIFT-24-01` -> `Zmień 24: <names>`;
- `EXTERNAL-01` / `EXTERNAL_SUPPORT_DISABLED` -> `Skonfiguruj Wsparcie zewnętrzne: <names>`;
- `SICK_LEAVE-01` -> `Ręczna korekta mimo zapisu Chorobowe zgodnie z kontraktem: <names>`;
- `LEAVE_GRANTED-01` -> `Ręczna korekta mimo zapisu Urlop zgodnie z kontraktem: <names>`;
- `REST-01` -> `Ręczna korekta z uwzględnieniem odpoczynku dobowego zgodnie z kontraktem: <names>`;
- matched SiteRule -> `Zmień zapisaną regułę: <rendered SiteRule description>`.

`DAY_SHIFT_OFF-01` nie generuje własnej opcji.

### F3. Path facts

Frozen conflict path (`_decision_for_conflicts`) dodaje:
`Odmroź zapisane przypisania i uruchom planowanie ponownie`.

Tylko ta path ma prawo wygenerować tę opcję.

Gdy finalny payload ma `load_blocker is not None`, dodać:
`Świadomie zaakceptuj przekroczenie tygodniowego czasu pracy`.

Nie generować load acceptance bez rzeczywistego finalnego load blocker.

## G. EXTERNAL SUPPORT

Nie używać tekstu `X/Y` w coordinator-facing blockers/options.

External option pojawia się tylko przy realnym raw `EXTERNAL-01` lub `EXTERNAL_SUPPORT_DISABLED`.

Nie proponować wsparcia zewnętrznego dlatego tylko, że demand jest unassignable.

Nie inventować external employee, membership ani window.

## H. DAY_ONLY / T018 NON-REGRESSION

T013 test musi udowodnić:
- Stage 1 DAY_ONLY shortage nie emituje coordinator decision, jeśli Stage 2 istnieje;
- Stage 2 success -> FEASIBLE i zero final guidance;
- `Zmień Nocka` może pojawić się dopiero w finalnym `DECISION_REQUIRED`, gdy raw `DAY_ONLY-01` rzeczywiście pozostał po aktualnych fallbackach;
- T013 nie zmienia `allow_day_only_n_fallback` flags ani kolejności solve calls.

## I. FOUR PATHS REQUIRED

Dedykowane oracles muszą przejść przez wszystkie cztery finalne konstrukcje.

1. Unassignable:
- blocking demand preserved;
- membership hidden;
- visible blockers translated;
- dynamic options only from present raw causes.

2. Cross-demand conflict:
- REST human text;
- SiteRule description zamiast id, jeżeli relevant exclusion istnieje;
- brak static external/day_only options bez blocker evidence.

3. Frozen conflict:
- all exhaustive frozen blockers humanized;
- unfreeze option present;
- LOAD acceptance only when coexisting load fact exists;
- unexplained violation nadal TECHNICAL_ERROR jak dziś.

4. Load:
- `LOAD-01` human text;
- load acceptance present;
- relevant SiteRule description preserved;
- no unrelated options.

## J. EMPTY-ACTION FALLBACK

Jeżeli finalny diagnosis ma autonomy boundary, ale wszystkie raw reasons są hidden/internal albo nie mają zatwierdzonej action family:

`unblocking_options == ["Brak automatycznego rozwiązania przy obecnej obsadzie i zapisanych ograniczeniach."]`

Nie zwracać pustej listy.

## K. DETERMINISM

W `tests/test_t013.py` wymagane:
- input blocker ordering reversed -> identical coordinator blockers/options;
- duplicate raw blockers -> no duplicate rendered blocker/action;
- multiple employees same family -> one action with stable sorted names;
- multiple SiteRule versions with same description -> one identical action text;
- `rule_version_id` never appears in coordinator-facing blocker/action.

## L. NO TECHNICAL ATTEMPT TRACE

Coordinator-facing payload/warnings nie mogą zawierać tekstów opisujących:
- Stage 1/2/3/4;
- `allow_day_only_n_fallback`;
- `allow_emergency_24h`;
- `uncapped`;
- solver status transitions.

Existing technical `warnings` unrelated to T013 are not globally redesigned by this task. T013 nie dodaje do nich trace prób.

## M. TESTS — MINIMUM T013 MATRIX

`tests/test_t013.py` minimum:
1. exact built-in condition mapping;
2. MEMBERSHIP_DISABLED hidden;
3. MEMBERSHIP-01 hidden;
4. EMP-02 absent/no mapping owner;
5. DAY_SHIFT_OFF-01 remains raw;
6. SHIFT-24-01 uses `24`;
7. SiteRule description replaces exact version id;
8. blank SiteRule description uses generic text and never id;
9. unassignable options are evidence-backed, no static extras;
10. no membership-driven roster suggestion;
11. EXTERNAL blocker -> human `Wsparcie zewnętrzne` + dynamic option;
12. no external blocker -> no external option;
13. final DAY_ONLY -> Nocka option;
14. intermediate T018 DAY_ONLY shortage then Stage2 FEASIBLE -> no DECISION_REQUIRED;
15. REST conflict -> only relevant REST/SiteRule guidance;
16. frozen conflict -> unfreeze option + translated blockers;
17. LOAD-only -> load option and human condition;
18. frozen + LOAD -> both relevant option families;
19. hidden/internal-only final diagnosis -> exact no-automatic-solution fallback;
20. deterministic order/dedup;
21. all four terminal paths return existing `DecisionRequiredPayload` shape;
22. FEASIBLE payload unchanged;
23. TECHNICAL_ERROR mapping unchanged.

## N. LEGACY TEST ENUMERATION — PREIMPLEMENTATION REQUIRED

T013 intentionally changes coordinator-facing strings and static option lists. Existing legacy tests may assert old raw `Blocker.condition` or exact old `unblocking_options`.

Architect does NOT authorize broad test rewrites in advance.

Before CC, Codex must mechanically enumerate every existing `tests/*.py` file whose assertions/fakes must change solely because of T013 coordinator-facing presentation.

Required output:
- exact file list;
- exact tests/assertions affected;
- classification: mechanical coordinator-facing expectation only vs real semantic conflict.

If any legacy test file requires edit, architect amends literal TASK_SCOPE before CC.

No implementation before this enumeration PASS.

## N1. ROUND 1 LEGACY TEST SCOPE AMENDMENT — T013-R1-1

Round 1 Codex audit on exact contract SHA `94e64b68e43327319d4dc27fe39a9bfd66323595` found exactly one blocker: 14 existing legacy test files require presentation-only expectation updates. All other Round 1 contract sections are PASS/CLOSED and are not reopened by this amendment.

The 14 files are now in literal TASK_SCOPE above. Only the exact tests/assertion classes below are opened:

1. `tests/test_audit_r12_findings.py`
   - `test_finding3_rest01_combination_conflict_is_decision_required`;
   - `test_finding4_decision_required_has_concrete_blockers`.

2. `tests/test_audit_r13_findings.py`
   - `test_r13_1a_pure_load_conflict_is_load01_not_rest01`;
   - `test_r13_1b_load_conflict_crossing_month_boundary_is_load01`;
   - `test_r13_1c_pure_headcount_shortage_is_not_rest01`.

3. `tests/test_audit_r17_findings.py`
   - `test_r17_2a_missing_membership_gives_concrete_blocker`;
   - `test_r17_2b_other_site_only_membership_gives_concrete_blocker`.
   These tests must preserve status and blocking demand; coordinator-facing assertions change only to prove Membership is hidden and no autonomous roster suggestion is emitted.

4. `tests/test_audit_r20_r21_findings.py`
   - `test_r20_2a_frozen_conflict_with_unavailable_is_decision_required`;
   - `test_r20_2b_frozen_conflict_with_leave_granted_is_decision_required`;
   - `test_r20_2c_frozen_conflict_with_sick_leave_is_decision_required`;
   - `test_r20_2d_mentor_linked_non_frozen_conflict_is_decision_required`.

5. `tests/test_audit_r22_findings.py`
   - `test_r22_2a_frozen_conflict_with_concurrent_load01_includes_load_blocker`.

6. `tests/test_audit_r25_findings.py`
   - `test_r25_1a_day_only_does_not_mask_concurrent_sick_leave`;
   - `test_r25_1b_sick_leave_does_not_mask_concurrent_rest01`;
   - `test_sick_leave_wins_over_leave_granted_on_overlapping_day`;
   - `test_leave_granted_still_reported_outside_the_sick_range`.

7. `tests/test_audit_r26_findings.py`
   - `test_r26_1a_leave_granted_and_sick_leave_on_different_days_are_both_reported`;
   - `test_r26_1a_reversed_record_order_gives_same_result`;
   - `test_r26_1b_unavailable_24h_and_sick_leave_no_established_priority_both_reported`;
   - `test_r26_1_sick_leave_still_wins_over_leave_granted_on_the_actual_shared_day`;
   - `test_r26_2_unavailable_condition_code_is_canonical`;
   - `test_r26_3_sibling_rest_between_two_fixed_assignments_stays_decision_required`.

8. `tests/test_audit_t007_r3.py`
   - `test_r3_profile_scope_does_not_depend_on_profile_id_text`;
   - `test_r3_cross_demand_conflict_preserves_site_rule_provenance`;
   - `test_r3_load_fallback_preserves_site_rule_provenance`.

9. `tests/test_audit_t007_r4.py`
   - `test_r4_load_payload_does_not_attribute_an_unrelated_site_rule`.
   The negative provenance oracle MUST remain non-vacuous: adapt fixture/assertion to distinguish relevant vs unrelated SiteRule via unique coordinator-facing description, never merely assert absence of raw rule_version_id.

10. `tests/test_audit_t007_r5.py`
    - `test_r5_load_provenance_includes_overnight_shift_entering_worst_window`.

11. `tests/test_sick_leave.py`
    - `test_sick_leave_hard_blocks_assignment_on_sick_day`.

12. `tests/test_site_rules_execution.py`
    - `test_k_valid_hard_site_rule_shortage_is_decision_required_with_rule_version_id`;
    - `test_p_frozen_assignment_conflicting_with_hard_site_rule_is_decision_required_not_moved`.

13. `tests/test_t016_emp02_retirement.py`
    - `test_disabled_membership_still_blocks_regardless_of_active_period`;
    - `test_availability_hard_still_blocks_employee_outside_active_period`.

14. `tests/test_t018.py`
    - `test_a7_7_weekend_absence_still_hard_blocks_assignment`;
    - `test_b10_7a_sick_leave_still_blocks_in_fallback_pass`;
    - `test_b10_7b_membership_disabled_still_blocks_in_fallback_pass`;
    - `test_b10_7c_leave_granted_still_blocks_in_fallback_pass`;
    - `test_b10_7d_another_site_rule_still_blocks_in_fallback_pass`;
    - `test_b10_7h_unavailable_24h_still_blocks_in_fallback_pass`.

### N1.1 Allowed changes in these 14 files

Only mechanical coordinator-facing presentation adaptations are allowed:
- translated `DecisionRequiredPayload.blockers[*].condition` according to sections C/D;
- Membership blocker invisibility according to section E;
- dynamic `unblocking_options` according to section F/J;
- deterministic ordering/dedup according to section K;
- SiteRule coordinator description replacing raw version id while preserving a non-vacuous provenance oracle.

### N1.2 Explicitly not opened

The amendment does NOT authorize:
- any status change;
- any change to `blocking_shift_demands` semantics or expected demands;
- any change to `load_blocker` semantics;
- any change to solver/validator raw conditions, eligibility priorities, retry order or HARD behavior;
- any change to direct assertions on `validator.violation_details.rule` — those remain raw;
- any change of `DAY_SHIFT_OFF-01` coordinator wording; it remains raw and generates no action;
- weakening/removing an old finding merely because raw code becomes hidden;
- changes elsewhere in the 14 files unrelated to the exact listed tests/presentation assertions.

`tests/test_real_object_benchmark.py` remains outside the amendment: it intentionally constructs arbitrary UI wording and needs no T013 adaptation.

`tests/test_t011_e_pipeline_e2e_hard_stop.py` remains outside the amendment: it verifies presence of the blocked employee rather than raw condition wording and needs no T013 adaptation.

If implementation finds any 15th legacy test file or any semantic expectation change beyond this list, STOP + architect amendment before editing.

## O. PREIMPLEMENTATION CODEX AUDIT

Round 1 already closed all architecture/product sections except T013-R1-1. The full checklist below remains the final contract checklist, but Round 2 is deliberately narrow and MUST NOT reopen Round 1 PASS sections without a concrete contradiction introduced by this amendment.

Codex final checklist:
1. Does the design preserve T018 4-stage retry literally and ensure guidance is terminal-only?
2. Does it cover all four final DECISION_REQUIRED paths?
3. Are membership codes hidden and is automatic roster suggestion impossible?
4. Are exact owner blocker texts preserved, including SiteRule description instead of version id?
5. Is `DAY_SHIFT_OFF-01` correctly left untranslated/no new action?
6. Is T012 naming `24` preserved for SHIFT-24 communication?
7. Is dynamic guidance evidence-backed rather than static, without a second solver or override mechanism?
8. Is `DecisionRequiredPayload` reused without new DTO/persistence?
9. Are solver/eligibility/validator/site_rules/domain/application/persistence outside implementation scope?
10. Are the 14 Round 1 legacy test files now literally in TASK_SCOPE with only the N1 presentation adaptations authorized?
11. Does any clause introduce a product decision not supported by owner brief? If yes: FAIL with exact clause.

### O1. ROUND 2 — NARROW AUDIT ONLY

Round 2 checks only T013-R1-1:
1. literal TASK_SCOPE contains exactly the 14 legacy files enumerated in N1, in addition to `tests/test_t013.py`;
2. exact affected tests match the Round 1 report;
3. allowed changes are presentation-only and preserve status/blocking-demand/raw solver-validator semantics;
4. membership tests preserve their original planning outcome while proving hidden coordinator presentation/no roster autonomy;
5. T007 provenance tests remain non-vacuous through SiteRule descriptions, not absence of raw IDs;
6. direct validator raw-rule assertions remain closed;
7. DAY_SHIFT_OFF remains raw/no-action;
8. `tests/test_real_object_benchmark.py` and `tests/test_t011_e_pipeline_e2e_hard_stop.py` remain outside amendment;
9. no production/test implementation is included in the contract amendment;
10. all Round 1 PASS sections remain closed.

Required Round 2 verdict:
`PASS — READY_FOR_IMPLEMENTATION`.

Until that exact PASS:
**CC MUST NOT START T013 IMPLEMENTATION.**

## P. IMPLEMENTATION GATE / FINAL AUDIT

After implementation Codex audits exact PRODUCT SHA and full BASE_SHA -> HEAD diff.

Required:
- T013 dedicated matrix PASS;
- all mechanically authorized legacy tests PASS;
- full `tests/` suite PASS;
- T018 regressions including 4-stage retry PASS;
- T012 emergency regressions PASS;
- ROTA-REG-001 PASS;
- Ruff PASS;
- `python guard.py check arch/spec.md` PASS;
- `git diff --check` PASS;
- `arch/spec.md` and `arch/FROZEN.lock` unchanged;
- backend.py run on literal TASK_SCOPE;
- every SIZE_FILE/SIZE_FUNC/RATIO/TOTAL_LINES `WYMAGA_DECYZJI` returns to architect with exact PRODUCT SHA.

Only after Codex PASS and architect final acceptance:
`ARCHITECT FINAL GATE ACCEPTANCE — ROTA-T013: PASS — READY FOR MERGE`.
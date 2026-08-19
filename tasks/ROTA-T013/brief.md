# ROTA-T013 — coordinator-facing DECISION_REQUIRED guidance

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC
DATE: 2026-08-19
TASK_ID: ROTA-T013
BASE_SHA: 5b35e3225f546bc7763c51b34e8a7ebe77553b58
BASE_BRANCH: main
TASK_BRANCH: task/ROTA-T013
OWNER_SOURCE: arch/T013_solver_communication_architect_brief.md
FROZEN_ADDENDUM: arch/FROZEN_ADDENDUM_DECISION_REQUIRED_COORDINATOR_COMMUNICATION_01.md
DEPENDS_ON: T012 + T016 + T018 merged on main

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

## O. PREIMPLEMENTATION CODEX AUDIT

Codex audits exact contract SHA and answers only:

1. Does the design preserve T018 4-stage retry literally and ensure guidance is terminal-only?
2. Does it cover all four final DECISION_REQUIRED paths?
3. Are membership codes hidden and is automatic roster suggestion impossible?
4. Are exact owner blocker texts preserved, including SiteRule description instead of version id?
5. Is `DAY_SHIFT_OFF-01` correctly left untranslated/no new action?
6. Is T012 naming `24` preserved for SHIFT-24 communication?
7. Is dynamic guidance evidence-backed rather than static, without a second solver or override mechanism?
8. Is `DecisionRequiredPayload` reused without new DTO/persistence?
9. Are solver/eligibility/validator/site_rules/domain/application/persistence outside implementation scope?
10. What legacy test files require mechanical expectation updates?
11. Does any clause introduce a product decision not supported by owner brief? If yes: FAIL with exact clause.

Required verdict:
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

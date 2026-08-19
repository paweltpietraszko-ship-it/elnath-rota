# ROTA-T018 — WORKDAY ABSENCE ACCOUNTING + DAY_ONLY N FALLBACK

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT
DATE: 2026-08-19
TASK_ID: ROTA-T018
BASE_SHA: c55722dfa689baa2ae39ba51a0c290f35d7f2112
BASE_BRANCH: main
TASK_BRANCH: task/ROTA-T018
OWNER_SOURCE: arch/ARCHITECT_BRIEF_WORKDAY_ABSENCE_AND_DAY_ONLY_FALLBACK_2026-08-19.md
FROZEN_ADDENDA:
- arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md
- arch/FROZEN_ADDENDUM_DAY_ONLY_N_FALLBACK_01.md
DEPENDS_ON: ROTA-T012 integrated on main
BLOCKS: human-facing follow-ups that depend on stable retry/absence semantics

## CEL

Wdrożyć dokładnie dwie decyzje właściciela z 2026-08-19 bez nowego subsystemu:

A. `SICK_LEAVE` / `LEAVE_GRANTED` redukują normę o 8 h wyłącznie za dzień roboczy = Monday-Friday AND `CalendarDay.holiday=False`.

B. `EMPLOYEE_DAY_ONLY_N_EXCEPTION` nie jest zwykłym bypass DAY_ONLY. Normalny pass zachowuje DAY_ONLY HARD; dopiero po braku kompletnego grafiku uruchamiany jest wąski fallback N, z prawdziwym leksykograficznym minimum liczby użytych exceptional N przed TARGET/fairness. Ten fallback ma pierwszeństwo przed T012 emergency 24 h.

Nie zmieniać innych frozen zachowań.

## SOURCE FINDINGS / ORACLES

- `tasks/ROTA-T012/round_01/tests/tests_r23.txt` — ABS-R23-1;
- `tasks/ROTA-T012/round_01/tests/tests_r24.txt` — DAY-R24-1;
- `tasks/ROTA-T012/round_01/tests/test_absence_workday_accounting_r23.py` — 3 istniejące reproduktory;
- `tasks/ROTA-T012/scenarios/t012_owner_march_2027_probe.py` — pełny oracle 62 demandów;
- `tasks/ROTA-T012/scenarios/t012_owner_march_2027_probe_result.json` — dowód obecnego błędnego rozkładu A.N=8 i kontroli A.N=0.

Powyższe pliki są źródłami/regresją. Nie zmieniać ich tylko po to, aby test przeszedł.

## ARCHITECTURE PRINCIPLES

1. Bez nowego calendar service — istniejący `CalendarDay` + `calendar_repository` są źródłem danych.
2. Bez generic SOFT SiteRule engine — persisted `EMPLOYEE_DAY_ONLY_N_EXCEPTION` zachowuje istniejący wąski shape; zmienia się tylko sposób jego użycia przez solver.
3. Bez publicznego ignore_hard / override flag.
4. Bez nowej tabeli/DTO/event dla fallback provenance.
5. Bez własnego search/backtracking — wszystkie kombinacje i lexicographic minima przez OR-Tools CP-SAT.
6. Bez zmiany T012 emergency pair semantics.
7. Bez zmiany HARD blokowania SICK_LEAVE/LEAVE_GRANTED.
8. Bez dodawania LEAVE_GRANTED do live solver TARGET adjustment.
9. Bez przebudowy PlanningResult statusów.

## TASK_SCOPE

TASK_SCOPE:
- arch/FROZEN_ADDENDUM_ABSENCE_WORKDAY_ACCOUNTING_01.md
- arch/FROZEN_ADDENDUM_DAY_ONLY_N_FALLBACK_01.md
- tasks/ROTA-T018/brief.md
- rota/planning/absence.py
- rota/balance.py
- rota/persistence/work_balance_repository.py
- rota/planning/site_rules.py
- rota/planning/eligibility.py
- rota/planning/solver.py
- rota/planning/engine.py
- rota/planning/validator.py
- tests/test_t018.py

Żaden inny plik bez STOP + amendment architekta.

Nie zmieniać:
- arch/spec.md;
- arch/FROZEN.lock;
- rota/domain.py;
- rota/planning/constraints.py;
- rota/planning/work_periods.py;
- rota/application/assembler.py;
- rota/application/plan_ops.py;
- rota/application/lifecycle_ops.py;
- persistence schema;
- istniejących T012 audit/scenario plików.

NEW_FILES:
- contract docs są częścią task pipeline;
- jedyny nowy plik implementacyjno-testowy: `tests/test_t018.py`;
- zero nowych production modules.

## CHECKPOINT A — ABSENCE WORKDAY ACCOUNTING

### A1. Canonical pure owner

`rota/planning/absence.py` pozostaje jedynym ownerem liczenia excused absence days.

Rozszerzyć kompatybilnie `excused_absence_days_in_month(...)` o `calendar_days` jako dane wejściowe. Zachować obecny trzeci argument `kinds` i jego znaczenie.

Nie implementować osobnego weekday/holiday filtra w solverze ani balance.

### A2. Workday definition

Kwalifikowana data:
- ISO weekday <=5;
- matching CalendarDay istnieje;
- `holiday=False`.

Union/dedup dat per employee przed policzeniem. Inclusive ranges i month clipping bez zmian.

### A3. Fail closed

Dodać w `rota/planning/absence.py` jeden jawny exception type, np. `IncompleteAbsenceCalendarError`.

Jeżeli dany miesiąc ma aktywny AvailabilityRecord z konsumowanych `kinds` przecinający miesiąc, wymagany jest kompletny CalendarDay coverage każdego dnia tego miesiąca. Brak/niepełność/sprzeczność -> exception; bez weekday-only fallbacku.

Jeżeli brak kwalifikowanej absencji, legacy call bez calendar_days może nadal zwrócić dotychczasowy wynik, bo kalendarz nie wpływa na 0 redukcji.

### A4. Solver TARGET

`_sick_adjusted_targets(state)` przekazuje `state.calendar_days` do canonical helper.

Pozostaje tylko `SICK_LEAVE`.

`plan()` mapuje `IncompleteAbsenceCalendarError` na TECHNICAL_ERROR. W normalnym application flow assembler już wymaga kompletnego month calendar; ten catch chroni direct/legacy PlanningState i nie tworzy DECISION_REQUIRED.

### A5. WorkBalance

`compute_month_balance(...)` i `compute_quarter_balance(...)` dostają kompatybilnie dopisany na końcu opcjonalny `calendar_days`.

`compute_month_balance`: SICK_LEAVE + LEAVE_GRANTED jak dziś, ale tylko workdays.

`compute_quarter_balance`: przekazuje calendar_days do każdego month computation; brak kalendarza jest oceniany per miesiąc z kwalifikowaną absencją.

### A6. Persistence supply

`reconstruct_month_balance` ładuje CalendarDay dla pełnego miesiąca przez istniejące `list_calendar_days` i przekazuje do balance.

`reconstruct_quarter_balance` ładuje CalendarDay dla całego quarter interval przez ten sam existing repository API i przekazuje do `compute_quarter_balance`.

Żadnego SQL w `rota.balance` / planning / application.

### A7. A tests minimum

W `tests/test_t018.py`:
1. SICK_LEAVE range przez weekendy -> tylko weekdays;
2. LEAVE_GRANTED identycznie w WorkBalance;
3. weekday holiday=True wykluczony;
4. weekend holiday=True nadal 0;
5. overlap SICK/LEAVE dedup;
6. cross-month clipping;
7. absence weekend/holiday nadal HARD-blockuje Assignment;
8. complete-calendar missing one day -> explicit fail closed;
9. direct plan with incomplete calendar + sick absence -> TECHNICAL_ERROR;
10. legacy balance call bez absence i bez calendar_days zachowuje wynik;
11. existing three Round23 reproducers PASS bez zmiany oracle;
12. marzec 2027: B target 56 h przy target 168 i L4 2..19 marca.

### GATE A

Codex audytuje dokładny PRODUCT SHA A.

Musi potwierdzić:
- jeden counting owner;
- solver nie dostał LEAVE_GRANTED target adjustment;
- HARD availability nie osłabło;
- no guessed holidays;
- existing calendar repository reused;
- relevant tests + full suite + Ruff + guard + diff-check PASS.

Dopiero PASS A pozwala implementować B.

## CHECKPOINT B — DAY_ONLY N FALLBACK

### B1. Persisted rule shape unchanged

Nie migrować `EMPLOYEE_DAY_ONLY_N_EXCEPTION` do enforcement=SOFT.

Pozostaje `CONFIRMED_EXCEPTION / HARD / RESOLVED / {employee_id}` jako explicit coordinator authorization boundary. Generic SOFT SiteRule execution pozostaje unsupported.

Zmienia się execution semantics: normalny pass nie używa tej zgody jako bypass; fallback-enabled pass może.

### B2. Pure authorization lookup

W `rota/planning/site_rules.py` zachować wąski helper dla applicable DAY_ONLY exception. Dozwolone jest rozszerzenie go tak, aby zwracał exact authorizing rule_version_id potrzebny do provenance.

Nie zmieniać generic `rule_allows_assignment` dla pozostałych rule kinds.

### B3. Narrow eligibility switch

`check_eligibility` / private hard gate mogą dostać wyłącznie wewnętrzny, default-false parametr `allow_day_only_n_fallback`.

False:
- day_only + N + blocking profile => DAY_ONLY-01 niezależnie od zapisanej zgody.

True:
- bypass DAY_ONLY-01 tylko przy applicable `EMPLOYEE_DAY_ONLY_N_EXCEPTION` dla employee/date;
- każdy inny HARD sprawdzany jak dziś.

### B4. Solver slot provenance

Solver musi wiedzieć, które legalne sloty N są wyjątkowe wyłącznie dzięki fallback authorization, oraz exact rule_version_id do walidacji/warning provenance.

Nie dodawać tego do persisted Assignment ani PlanningState.

### B5. Lexicographic optimization

Dla fallback-enabled pass `exceptional_n_count = sum(x)` po exceptional N slots.

Initial PLAN:
1. minimize exceptional_n_count;
2. wymaga PROVEN OPTIMAL;
3. constrain count == minimum;
4. ordinary TARGET/fairness/SOFT objective.

REPLAN:
1. istniejące REPLAN-MIN-01 minimum reshuffle — PROVEN OPTIMAL;
2. constrain reshuffle minimum;
3. minimize exceptional_n_count — PROVEN OPTIMAL;
4. constrain exceptional minimum;
5. ordinary TARGET/fairness/SOFT.

Nie odwracać REPLAN-MIN-01. Nie zastępować tego dużą wagą liczbową.

Jeżeli lexical minimum phase zwróci FEASIBLE bez OPTIMAL / UNKNOWN / MODEL_INVALID -> TECHNICAL_ERROR; minimum nie jest udowodnione.

### B6. Engine retry order — literal

1. NORMAL CAPPED:
   `allow_day_only_n_fallback=False`, `allow_emergency_24h=False`.
2. DAY_ONLY CAPPED:
   `allow_day_only_n_fallback=True`, `allow_emergency_24h=False`.
3. DAY_ONLY + EMERGENCY CAPPED:
   `allow_day_only_n_fallback=True`, `allow_emergency_24h=True`.
4. LOAD diagnosis UNCAPPED:
   `allow_day_only_n_fallback=True`, `allow_emergency_24h=True`.

Transition rules:
- Stage 1 candidate HARD PASS -> return, no retry;
- Stage 1 INFEASIBLE OR unassignable -> Stage 2;
- Stage 2 candidate HARD PASS -> return, no emergency;
- Stage 2 INFEASIBLE OR unassignable -> Stage 3;
- Stage 3 candidate HARD PASS -> return;
- Stage 3 unassignable -> final existing DECISION_REQUIRED shortage;
- Stage 3 INFEASIBLE -> Stage 4;
- any technical status at any stage -> TECHNICAL_ERROR, no later retry.

Nie uruchamiać uncapped przed Stage 3. Nie robić extra retry.

### B7. Independent validator + warning

Validator pozostaje independent od solver variables.

Dla day_only N na blocking profile:
- brak applicable exception -> DAY_ONLY-01 HARD;
- legal applicable exception -> HARD pass for DAY_ONLY only + dokładnie jeden warning `DAY_ONLY-N-FALLBACK-01` zawierający employee_id, demand_id, date, exact rule_version_id.

Nie materializować tego warningu jako Deviation i nie wymagać acknowledgement.

Jeżeli employee/day/date nie pasują, warning nie powstaje i DAY_ONLY pozostaje HARD.

### B8. Durable provenance

Bez nowej persistence.

Po select/restart/finalize muszą nadal istnieć wystarczające fakty do deterministic reconstruction:
- Assignment;
- covering ShiftDemand;
- ScheduleVersion.applied_rule_version_ids;
- immutable SiteRuleVersion history.

Test nie wymaga nowego warning row. Ma udowodnić, że po round-trip można wskazać ten sam employee/demand/date/rule_version_id dla faktycznie użytej exceptional N.

### B9. T012 emergency provenance unchanged

Stage 3 używa istniejącego emergency pair modelu/provenance dokładnie jak T012. Nie dodawać emergency-used warning ani nowego bytu.

Jeżeli Stage 3 ma oba fallbacki, day_only warning współistnieje z istniejącym work_period provenance emergency pair.

### B10. B tests minimum

W `tests/test_t018.py`:
1. active exception + Stage1 FEASIBLE -> 0 exceptional N, Stage2/3 not called;
2. one N necessary -> exactly 1 + exact warning;
3. two necessary -> exactly 2;
4. multiple authorized employees -> global min total exceptional N;
5. TARGET/fairness would improve with extra N -> no extra N;
6. effective dates before/start/end/after;
7. membership + availability + SICK/LEAVE + REST + LOAD + another SiteRule remain AND-gates;
8. Stage1 NO_ELIGIBLE_EMPLOYEE caused by DAY_ONLY reaches Stage2;
9. technical Stage1 -> no retry;
10. Stage2 failure reaches Stage3;
11. scenario where day_only fallback alone and emergency alone each rescue -> Stage2 wins; zero emergency pair;
12. Stage3 INFEASIBLE -> Stage4 has both flags true;
13. REPLAN lexical order: reshuffle before exceptional N before ordinary soft;
14. persisted round-trip provenance reconstructible after select/restart/finalize;
15. current validator catches unauthorized day_only N independently;
16. T012 emergency same/cross-month regressions unchanged;
17. owner March 2027 scenario: 62/62, A.N=0, HARD PASS.

### GATE B / FINAL T018

Codex audytuje exact PRODUCT SHA B oraz pełny diff BASE_SHA -> HEAD.

Wymagane:
- Checkpoint A pozostaje PASS;
- wszystkie B classes PASS;
- `tasks/ROTA-T012/scenarios/t012_owner_march_2027_probe.py` PASS bez zmiany oracle;
- ROTA-REG-001 PASS;
- pełna suita PASS;
- Ruff PASS;
- `python guard.py check arch/spec.md` PASS (spec/lock niezmienione);
- `git diff --check` PASS;
- backend.py na `tasks/ROTA-T018/brief.md` z literalnym TASK_SCOPE;
- każde SIZE_FILE/RATIO/TOTAL_LINES `WYMAGA_DECYZJI` wraca do architekta z exact value i exact PRODUCT SHA.

Dopiero finalny `ARCHITECT FINAL GATE ACCEPTANCE — ROTA-T018: PASS` oznacza READY FOR MERGE.

## PREIMPLEMENTATION AUDIT — REQUIRED BEFORE CC

Codex ma przed implementacją sprawdzić:

1. oba frozen addenda są zgodne z owner brief i nie rozszerzają produktu;
2. absence addendum nie zmienia 8h, solverowego LEAVE_GRANTED ownership ani HARD availability;
3. day-only addendum zachowuje persisted rule shape i nie otwiera generic SOFT SiteRule execution;
4. retry order jest literalnie NORMAL -> DAY_ONLY -> DAY_ONLY+EMERGENCY -> UNCAPPED diagnosis;
5. NO_ELIGIBLE_EMPLOYEE/unassignable nie zamyka planu przed dozwolonym fallbackiem;
6. REPLAN-MIN-01 pozostaje przed exceptional_n_count;
7. warning/provenance nie wymaga nowej persistence;
8. TASK_SCOPE obejmuje dokładnie istniejących ownerów logiki i jeden nowy test file;
9. arch/spec.md i arch/FROZEN.lock pozostają niezmienione, a supersession jest jawnie ograniczony w addenda;
10. brak implementacji produktu w contract commit.

Wymagany wynik:
`PASS — READY_FOR_IMPLEMENTATION_A`.

CC NIE zaczyna implementacji przed tym PASS.

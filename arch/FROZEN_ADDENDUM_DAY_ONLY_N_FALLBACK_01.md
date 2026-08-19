# FROZEN PRODUCT CONTRACT ADDENDUM — DAY-ONLY-N-FALLBACK-01

ADDENDUM_ID: DAY-ONLY-N-FALLBACK-01
DATE: 2026-08-19
STATUS: FROZEN_PRODUCT_CONTRACT_ADDENDUM
BASE_SHA: c55722dfa689baa2ae39ba51a0c290f35d7f2112
OWNER_DECISION_SOURCE: arch/ARCHITECT_BRIEF_WORKDAY_ABSENCE_AND_DAY_ONLY_FALLBACK_2026-08-19.md

## SUPERSESSION — EXACT SCOPE

To addendum superseduje aktywne execution semantics `arch/FROZEN_ADDENDUM_DAY_ONLY_TEMP_N_EXCEPTION_01.md` wyłącznie w punkcie, w którym obowiązująca `EMPLOYEE_DAY_ONLY_N_EXCEPTION` natychmiast zwalniała zwykły PLAN z `DAY_ONLY-01`.

Od 2026-08-19 ta zgoda NIE jest zwykłą kwalifikacją do N. Jest datowaną autoryzacją, którą solver może wykorzystać dopiero w awaryjnym fallbacku po braku kompletnego grafiku z normalnym `DAY_ONLY-01` HARD.

To addendum superseduje także wyłącznie kolejność retry z `arch/spec.md` / T012, w której emergency 24 h było pierwszym fallbackiem po normalnym niepowodzeniu. Nowa kolejność ryzyka jest:
1. normalny PLAN bez obu fallbacków;
2. DAY_ONLY N fallback, emergency 24 h OFF;
3. DAY_ONLY N fallback + T012 emergency 24 h ON;
4. dopiero potem istniejąca diagnoza LOAD / DECISION_REQUIRED.

Pozostałe T012 semantics emergency 24 h — pairing, work-period provenance, REST, cross-month, qualification 24 h, brak chain >2, techniczne statusy — pozostają bez zmian.

## PERSISTED RULE SHAPE REMAINS NARROW

Nie migrować istniejącego rule kind ani całego SiteRule SOFT frameworku.

`EMPLOYEE_DAY_ONLY_N_EXCEPTION` nadal jest persisted jako:
- category=`CONFIRMED_EXCEPTION`;
- enforcement=`HARD`;
- resolution_status=`RESOLVED`;
- structured_parameters dokładnie `{employee_id}`;
- existing effective_from/effective_to + monthly applicability semantics.

`enforcement=HARD` oznacza tu trwałą, jawną granicę autoryzacji koordynatora: bez takiej obowiązującej zgody solver nigdy nie może użyć day_only employee na N. Nie oznacza już natychmiastowego bypassu w normalnym pass.

Faktyczne UŻYCIE tej zgody jest fallbackiem SOFT/rankingowym. Nie otwiera to generic RESOLVED SOFT SiteRule execution i nie zmienia `SITE-RULE-EXEC-01` dla innych rule kinds.

## NORMAL PASS — DAY_ONLY REMAINS HARD

Normalny pass MUST uruchamiać eligibility tak, jakby `EMPLOYEE_DAY_ONLY_N_EXCEPTION` nie zdejmowała `DAY_ONLY-01`.

Jeżeli:
- profile.day_only_blocks_n=true;
- employee.day_only=true;
- demand jest N;

to normalny pass odrzuca slot przez `DAY_ONLY-01` nawet wtedy, gdy na tej dacie istnieje aktywna zgoda fallback.

Jeżeli normalny pass daje kompletny candidate i independent validator potwierdza HARD PASS, plan kończy się natychmiast. Żaden fallback nie może zostać uruchomiony dla poprawy TARGET, fairness, LEAVE_PLAN, DAY_SHIFT_OFF ani innego SOFT.

## NARROW INTERNAL SWITCH

Dozwolony jest wyłącznie wewnętrzny parametr solver/eligibility w rodzaju:

`allow_day_only_n_fallback: bool = False`

Nie jest to publiczne `ignore_hard`, nie trafia do PlanningState ani domeny persistent i nie może wyłączać żadnego innego HARD.

Gdy `False`: obowiązująca zgoda nie zwalnia DAY_ONLY-01.
Gdy `True`: N dla day_only może przejść tylko wtedy, gdy na demand start date istnieje applicable `EMPLOYEE_DAY_ONLY_N_EXCEPTION` dla tego employee.

Membership, SICK_LEAVE, LEAVE_GRANTED, UNAVAILABLE, DAY_SHIFT_OFF, REST, LOAD, executable SiteRules, EXTERNAL, coverage i SHIFT-24 qualification nadal muszą przejść niezależnie.

## COMPLETE-GRAPH FAILURE INCLUDES PRE-MODEL SHORTAGE

„Brak kompletnego grafiku” obejmuje zarówno:
- CP-SAT status `INFEASIBLE`, jak i
- solver outcome `NO_ELIGIBLE_EMPLOYEE` / `unassignable_demand_ids` powstały przed zbudowaniem pełnego modelu.

Normalne `unassignable` NIE może od razu zakończyć PLAN jako DECISION_REQUIRED, jeżeli pozostają jeszcze dozwolone fallback passes.

UNKNOWN, MODEL_INVALID, nieudowodnione minimum w lexicographic phase albo inny status techniczny NIE jest dowodem niewykonalności i kończy się TECHNICAL_ERROR bez dalszego retry.

## RETRY ORDER — LITERAL

Stage 1 — NORMAL CAPPED
`solve(state, enforce_load_cap=True, allow_day_only_n_fallback=False, allow_emergency_24h=False)`

- candidate + independent HARD PASS => FEASIBLE; STOP;
- technical status => TECHNICAL_ERROR; STOP;
- INFEASIBLE albo unassignable => Stage 2.

Stage 2 — DAY_ONLY FALLBACK CAPPED, NO EMERGENCY 24h
`solve(state, enforce_load_cap=True, allow_day_only_n_fallback=True, allow_emergency_24h=False)`

- candidate + independent HARD PASS => FEASIBLE; STOP;
- technical status => TECHNICAL_ERROR; STOP;
- INFEASIBLE albo unassignable => Stage 3.

Stage 3 — DAY_ONLY FALLBACK + T012 EMERGENCY 24h, CAPPED
`solve(state, enforce_load_cap=True, allow_day_only_n_fallback=True, allow_emergency_24h=True)`

- candidate + independent HARD PASS => FEASIBLE; STOP;
- technical status => TECHNICAL_ERROR; STOP;
- unassignable => final existing DECISION_REQUIRED for shortage; no uncapped solve can repair missing eligible slots;
- INFEASIBLE => Stage 4.

Stage 4 — LOAD DIAGNOSIS, SAME FALLBACK CAPABILITIES
`solve(state, enforce_load_cap=False, allow_day_only_n_fallback=True, allow_emergency_24h=True)`

- candidate => existing LOAD diagnosis path after full independent validation;
- conflicting demand set => existing DECISION_REQUIRED conflict path;
- unassignable => existing DECISION_REQUIRED shortage path;
- technical status => TECHNICAL_ERROR.

Nie istnieje uncapped normal-only ani uncapped day-only-without-emergency pass po wejściu w fallback sequence. Nie dodawać dalszych retry.

## LEXICOGRAPHIC MINIMUM OF EXCEPTIONAL N

Każdy solver pass z `allow_day_only_n_fallback=True` rozpoznaje slot N, który:
- należy do employee.day_only=true;
- jest dopuszczony tylko dzięki applicable `EMPLOYEE_DAY_ONLY_N_EXCEPTION`.

`exceptional_n_count` = liczba wybranych Assignment N korzystających z tej zgody. Jedno Assignment liczy się raz niezależnie od liczby równoważnych zgód.

Dla initial PLAN:
1. znajdź PROVEN OPTIMAL minimum `exceptional_n_count` pod wszystkimi HARD danego passu;
2. zamroź to minimum jako constraint;
3. dopiero wtedy optymalizuj dotychczasowy TARGET/fairness/pozostałe SOFT.

FEASIBLE bez dowodu OPTIMAL w fazie minimum wyjątkowych N nie wystarcza — kontrakt wymaga prawdziwego minimum; taki nieudowodniony phase result jest TECHNICAL_ERROR.

Dla REPLAN zachować istniejący `REPLAN-MIN-01` bez zmiany jego pierwszeństwa:
1. minimum reshuffle — PROVEN OPTIMAL;
2. przy zamrożonym minimum reshuffle: minimum `exceptional_n_count` — PROVEN OPTIMAL;
3. przy obu zamrożonych minimach: dotychczasowy TARGET/fairness/pozostałe SOFT.

Nowe addendum nie pozwala zmienić więcej placements tylko po to, aby zmniejszyć wyjątkowe N; REPLAN-MIN-01 jest wcześniejszym frozen lexicographic contract i pozostaje outer priority.

Jeżeli dany fallback pass nie ma żadnego legalnego exceptional slotu, nie trzeba uruchamiać pustej dodatkowej fazy optymalizacji.

## DATE / AUTHORIZATION SEMANTICS

Authorization jest oceniana na `ShiftDemand.start_datetime.date()` przy użyciu istniejących `SiteRuleApplicability` inclusive slices.

Brak zgody, inny employee albo data poza obowiązywaniem = zwykły `DAY_ONLY-01` HARD.

Zgoda zwalnia wyłącznie DAY_ONLY-01 dla konkretnego N w fallback-enabled pass. Nie jest ogólnym SiteRule allow i nie ma wpływu na D.

## INDEPENDENT VALIDATOR

Validator nie ufa solverowym flagom.

Dla każdego finalnego Assignment N employee.day_only=true przy profile.day_only_blocks_n=true:
- znajduje covering ShiftDemand i jego start date;
- niezależnie sprawdza applicable `EMPLOYEE_DAY_ONLY_N_EXCEPTION` dla tego employee/date;
- bez zgody emituje `DAY_ONLY-01` HARD;
- z legalną zgodą nie emituje DAY_ONLY-01, ale emituje coordinator-facing SOFT provenance warning.

Validator nie próbuje ponownie rozwiązywać problemu kombinatorycznego i nie dowodzi minimalności liczby wyjątkowych N. Minimalność jest gwarancją konstrukcyjną solvera przez lexicographic phases; validator niezależnie potwierdza legalność każdego faktycznie użytego wyjątku.

## WARNING / PROVENANCE CONTRACT

Każde faktycznie użyte exceptional N musi wygenerować dokładnie jeden stabilny warning dla tego Assignment w finalnym PlanningResult.

Warning musi nieść co najmniej:
- stable code `DAY_ONLY-N-FALLBACK-01`;
- `employee_id`;
- `demand_id`;
- demand start date;
- exact authorizing `rule_version_id`.

Przykładowy kształt tekstowy (format separators techniczny, pola obowiązkowe):
`DAY_ONLY-N-FALLBACK-01 SOFT: employee=A demand=2027-03-17-N date=2027-03-17 rule_version_id=RV-...`

Warning jest generowany z finalnego candidate przez independent validator albo jeden współdzielony pure provenance helper; nie duplikować go równolegle w solverze i validatorze.

## DURABLE PROVENANCE WITHOUT NEW PERSISTED ENTITY

Nie dodawać nowej tabeli, Assignment field, DecisionRecord ani Deviation dla automatycznego fallbacku.

Trwałe fakty już wystarczają do odtworzenia użycia po restart/select/finalize:
- persisted Assignment + covers_demand_id;
- persisted ShiftDemand z shift_kind/start date;
- ScheduleVersion.applied_rule_version_ids;
- immutable SiteRuleVersion history z employee_id i effective dates.

Actual usage jest pochodną: persisted N Assignment day_only employee + applicable authorizing rule_version_id w applied rule provenance. Sam fakt, że rule_version_id jest w applied_rule_version_ids, nie oznacza użycia; użycie istnieje dopiero gdy odpowiada mu faktyczny N Assignment.

`select_candidate` / restart / finalize nie muszą zapisywać osobnego warning row. Muszą zachować powyższe fakty tak, aby ten sam warning/provenance można było deterministycznie odtworzyć z persisted schedule. Nie zamieniać SOFT warningu w Deviation wymagającą acknowledgement.

## T012 EMERGENCY 24h PROVENANCE

Nowa kolejność retry nie zmienia persisted provenance emergency 24 h:
- same-month pair: dwa Assignments dzielą work_period_id i emergency rest snapshot;
- cross-month: later Assignment reuse boundary work_period_id i persisted boundary-demand rest provenance.

To jest strukturalna provenance emergency fallbacku. Ten task nie dodaje osobnego „emergency-used” warningu ani nowego persistent event; przyszłe human-communication taski mogą ją prezentować na podstawie istniejących danych.

Gdy Stage 3 używa jednocześnie day_only fallback i emergency 24 h, final candidate musi zachować oba rodzaje provenance: mandatory DAY_ONLY warning + istniejące T012 work-period provenance.

## MARCH 2027 OWNER ORACLE

Dla scenariusza `tasks/ROTA-T012/scenarios/t012_owner_march_2027_probe.py`:
- Stage 1 jest FEASIBLE;
- Stage 2/3/4 nie są uruchamiane;
- employee A dostaje dokładnie 0 N;
- wszystkie 62 demandy są pokryte;
- independent validator HARD PASS.

Nie zamrażać konkretnej dystrybucji D/N pozostałych employees.

## REQUIRED ORACLES

1. normalny FEASIBLE mimo aktywnej zgody -> 0 exceptional N, no fallback call;
2. dokładnie jedna exceptional N konieczna -> dokładnie 1 + warning z rule_version_id;
3. dokładnie dwie konieczne -> 2, nie więcej;
4. wiele authorized day_only employees -> global minimum liczby exceptional N;
5. lepszy TARGET/fairness wymagałby dodatkowej exceptional N -> dodatkowa N niedozwolona;
6. effective_from/effective_to: before/boundaries/after;
7. availability/REST/LOAD/membership/other SiteRule nie są bypassowane;
8. Stage 1 NO_ELIGIBLE_EMPLOYEE przez DAY_ONLY osiąga Stage 2;
9. UNKNOWN/MODEL_INVALID/non-optimal lexical phase -> TECHNICAL_ERROR bez retry;
10. Stage 2 nie pomaga -> Stage 3;
11. zarówno jedna exceptional N, jak i emergency 24 h osobno mogą uratować grafik -> Stage 2 wygrywa, zero emergency pair;
12. Stage 3 capped INFEASIBLE -> Stage 4 z oboma fallback capabilities ON;
13. REPLAN: reshuffle minimum pozostaje przed exceptional N minimum;
14. restart/select/finalize: provenance może być odtworzona z persisted schedule bez nowego bytu;
15. marzec 2027: 62/62, A.N=0, HARD PASS.

## NON-GOALS

- brak generic override HARD;
- brak publicznej flagi ignore_hard;
- brak generic SOFT SiteRule weighting;
- brak zmiany persistence shape EMPLOYEE_DAY_ONLY_N_EXCEPTION;
- brak nowego statusu PlanningResult;
- brak nowego DTO/event/audit store;
- brak zmiany T012 pair/work-period semantics;
- brak T013 dynamic DecisionRequired communication;
- brak T017 multi-candidate diversity;
- brak własnego search/backtracking poza CP-SAT.

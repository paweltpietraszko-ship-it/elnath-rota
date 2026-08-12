# TASK_CONTRACT

TASK_ID: ROTA-T006
TITLE: REPLAN minimal reshuffle
STATUS: ARCHITECTURE_APPROVED_FOR_IMPLEMENTATION
DATE: 2026-08-12
ARCHITECT_ROLE: ChatGPT architect
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: ChatGPT architect
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: yes
FROZEN_RULE: REPLAN-MIN-01
FROZEN_ADDENDUM: arch/FROZEN_ADDENDUM_REPLAN_MIN_01.md
SOURCE_CONTRACT_GAP_SHA: 7ac0fd634ee59ed6d0a3d2f1dab2169519fe094e

## OBJECTIVE

Zmienić zachowanie REPLAN tak, aby każdy replan istniejącego grafiku zachowywał możliwie największą część dotychczasowych przydziałów.

Każdy REPLAN ma kończyć się najmniejszą liczbą zmian istniejących, redystrybuowalnych przydziałów, przy której da się uzyskać kompletny wynik zgodny z HARD.

Dopiero wśród rozwiązań z taką samą minimalną liczbą roszad wolno stosować istniejący TARGET-01 i pozostały SOFT ranking.

## SOURCE OF PRODUCT AUTHORITY

Jawna decyzja właściciela z 2026-08-12:

`Każdy replan musi kończyć sie minimalnymi zmianami grafiku przy jakich uda sie go ustalić.`

Ta decyzja została zamrożona jako `REPLAN-MIN-01` w `arch/FROZEN_ADDENDUM_REPLAN_MIN_01.md`.

CC nie interpretuje jej przez własny system wag i nie ogranicza jej tylko do absencji.

## PRODUCT PRIORITY ORDER

Dla każdego REPLAN obowiązuje kolejność leksykograficzna:

1. wszystkie HARD + istniejące bezwzględne zasady zachowania Assignment;
2. minimalna liczba roszad istniejących baseline placements;
3. TARGET-01 i wszystkie istniejące ordinary SOFT factors.

Konsekwencja:

Jeżeli istnieje HARD-valid rozwiązanie z 1 roszadą, rozwiązanie z 2 roszadami nie może wygrać tylko dlatego, że lepiej wyrównuje target_hours, weekendy, święta, preferencje D/N, DAY_SHIFT_OFF albo LEAVE_PLAN.

Minimal reshuffle nie jest HARD: jeżeli jedna zmiana nie wystarcza, ale dwie pozwalają uzyskać poprawny grafik, REPLAN ma prawo wykonać dwie.

## ARCHITECTURE DECISION — LEXICOGRAPHIC SOLVE

Nie implementować minimalnej roszady przez arbitralną stałą wagową typu `RESHUFFLE_WEIGHT = 101`, `1000` ani inną wartość dobraną względem `TARGET_DEVIATION_WEIGHT`.

Wymagany efekt jest leksykograficzny i ma być zagwarantowany konstrukcyjnie.

Preferowany wzorzec implementacyjny:

PHASE 1:
- zbudować normalny HARD-valid model REPLAN;
- zminimalizować `reshuffle_count`;
- uzyskać minimalną osiągalną wartość `min_reshuffle_count`.

PHASE 2:
- zachować ten sam model kontraktu HARD;
- wymusić `reshuffle_count == min_reshuffle_count`;
- zastosować istniejący TARGET/SOFT objective;
- zwrócić najlepszy wynik w tej minimalnej klasie roszad.

CC może technicznie zrealizować równoważną optymalizację wieloetapową, jeżeli matematycznie gwarantuje dokładnie tę samą kolejność priorytetów. Nie wolno zastąpić jej heurystyką lub nieudowodnioną wagą dominującą.

OR-Tools CP-SAT pozostaje solverem. Nie implementować własnego search/backtrackingu.

## BASELINE / UNIT OF RESHUFFLE

Roszada liczona jest per baseline demand placement, nie per pracownik i nie per database row id.

Baseline placement to istniejący Assignment, który:
- ma `role == PRIMARY`;
- ma `state == PLANNED`;
- ma `frozen == false`;
- ma `covers_demand_id`;
- należy do zestawu, który obecny kontrakt REPLAN pozwala redystrybuować.

Dla jednego baseline placement:

UNCHANGED:
- finalny kandydat ma tego samego `employee_id` na tym samym `covers_demand_id`.

CHANGED:
- ten sam demand w finalnym kandydacie pokrywa inny `employee_id`, albo baseline placement nie może pozostać i jest zastąpiony.

Zmiana `assignment_id` sama w sobie nie jest roszadą, jeżeli człowiek nadal pracuje na tym samym demandzie.

Baseline placement, który musi się zmienić z powodu nowego HARD blocker, liczy się jako roszada, ale taka roszada jest dozwolona.

Nowy/uncovered ShiftDemand bez baseline placement nie liczy się sam w sobie jako roszada. Jeżeli jego pokrycie wymaga przesunięcia istniejących baseline placements, te przesunięcia liczą się normalnie.

## SCOPE — EVERY REPLAN

REPLAN-MIN-01 obowiązuje przy każdym REPLAN istniejącego grafiku, niezależnie od triggera.

Dotyczy m.in.:
- absencji/choroby;
- nowej niedostępności;
- zmiany koordynatora wymagającej ponownego ułożenia;
- każdego innego wspieranego wywołania REPLAN.

Nie dotyczy pierwszego planowania, gdy nie istnieją baseline placements do zachowania.

## RELATION TO EXISTING RULES

Bez zmian pozostają:
- ASSIGN-03: REALIZED work MUST NOT be changed by REPLAN;
- ASSIGN-04: future frozen Assignment MUST NOT be changed by REPLAN;
- pozostałe HARD;
- TARGET-01 jako SOFT;
- weekend fairness;
- holiday fairness;
- D/N preferences;
- DAY_SHIFT_OFF SOFT quality;
- LEAVE_PLAN SOFT quality;
- obecne statusy FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR.

REPLAN-MIN-01 nie może zmienić DECISION_REQUIRED w FEASIBLE ani obchodzić żadnego HARD/decision gate.

## EXISTING SOFT OBJECTIVE

T006 nie przeprojektowuje wewnętrznych relacji między istniejącymi ordinary SOFT factors.

Ich aktualna semantyka pozostaje taka jak przed T006.

Jedyna zmiana to nowy wyższy poziom rankingu REPLAN:

`minimum reshuffle count` BEFORE `ordinary SOFT objective`.

## IMPLEMENTATION BOUNDARY

Dozwolone obszary produkcyjne:
- `rota/planning/solver.py`;
- ewentualny nowy mały moduł w `rota/planning/` wyłącznie jeśli potrzebny do zachowania SIZE_FILE/SIZE_FUNC lub czytelnego wydzielenia REPLAN objective;
- `rota/planning/engine.py` tylko jeżeli jest to konieczne do sterowania wieloetapowym solve bez zmiany publicznego kontraktu PlanningResult.

Dozwolone testy:
- nowy dedykowany plik testowy T006;
- minimalne aktualizacje istniejących testów REPLAN wyłącznie tam, gdzie obecne oczekiwanie było sprzeczne z nowym Frozen Product Contract.

## OUT OF SCOPE

Nie implementować:
- UI;
- persistence;
- T005 SiteMemory/Decision Ledger;
- nowych rule_kind;
- zmian SiteRule;
- nowych triggerów REPLAN;
- user-configurable reshuffle weight;
- formularza "jak bardzo chronić grafik";
- własnego solvera poza OR-Tools;
- zmiany semantyki HARD;
- zmiany regression oracle ROTA-REG-001 dla initial planning, chyba że audyt wykaże bezpośredni i nieunikniony konflikt z nowym jawnie zamrożonym kontraktem — wtedy STOP i CONTRACT_GAP zamiast samodzielnej zmiany oracle.

## REQUIRED TEST MATRIX

### A. ONE CHANGE BEATS BETTER SOFT

Zbudować REPLAN, w którym:
- istnieje rozwiązanie HARD-valid zmieniające dokładnie 1 baseline placement;
- istnieje rozwiązanie zmieniające >=2 placements z lepszym ordinary SOFT/target score.

Wynik musi mieć 1 roszadę.

### B. ESCALATE ONLY WHEN NECESSARY

Zbudować REPLAN, w którym:
- 1 roszada nie może dać kompletnego HARD-valid grafiku;
- 2 roszady mogą.

Wynik musi mieć dokładnie 2 roszady.

### C. SOFT BREAKS TIE

Zbudować dwa lub więcej HARD-valid rozwiązań z takim samym minimalnym reshuffle_count.

W tej klasie istniejący TARGET/SOFT ranking nadal ma wpływać na wybór.

### D. ABSENCE IS NOT SPECIAL

Potwierdzić minimal reshuffle dla absencji oraz co najmniej jednego innego wspieranego triggera REPLAN.

### E. REALIZED / FROZEN

Potwierdzić, że T006 nie osłabia ASSIGN-03 ani ASSIGN-04.

### F. SAME PERSON / SAME DEMAND

Jeżeli finalnie ten sam employee pokrywa ten sam demand, nie liczyć roszady wyłącznie dlatego, że techniczny Assignment object/id został odtworzony.

### G. NEW DEMAND

Nowy demand bez baseline placement nie dodaje reshuffle_count sam z siebie.

### H. INITIAL PLAN UNAFFECTED

Planowanie bez istniejących baseline placements zachowuje dotychczasowe zachowanie SOFT i nie otrzymuje sztucznej kary reshuffle.

### I. STATUS BOUNDARIES

T006 nie może zmieniać normalnego DECISION_REQUIRED/TECHNICAL_ERROR w FEASIBLE tylko po to, by znaleźć mniejszą roszadę.

## ACCEPTANCE CONTRACT

PASS wymaga łącznie:
1. Każdy REPLAN minimalizuje liczbę changed baseline placements przed ordinary SOFT.
2. Minimalizacja jest gwarantowana leksykograficznie, nie arbitralną wagą.
3. Roszada jest liczona per baseline demand placement.
4. Ten sam employee + ten sam demand = brak roszady niezależnie od technicznego Assignment id.
5. HARD ma pierwszeństwo przed minimal reshuffle.
6. ASSIGN-03 i ASSIGN-04 pozostają bez zmian.
7. TARGET-01 i ordinary SOFT działają dopiero w klasie minimalnego reshuffle_count.
8. Lepszy SOFT nie może uzasadnić dodatkowej roszady.
9. Jeżeli minimum N roszad jest infeasible, a N+1 jest feasible, N+1 jest dozwolone.
10. Reguła działa dla każdego REPLAN triggera, nie tylko absencji.
11. Initial planning bez baseline pozostaje niezmienione semantycznie.
12. Nowy demand bez baseline nie jest sam liczony jako roszada.
13. Existing PlanningResult status contract pozostaje bez zmian.
14. OR-Tools pozostaje jedynym silnikiem kombinatorycznego search.
15. Niezależny validator nadal sprawdza wszystkie HARD po wygenerowaniu kandydata.
16. Pełna istniejąca suita poza jawnie zmienioną semantyką REPLAN pozostaje zielona.
17. Ruff, SIZE_FILE, SIZE_FUNC i `git diff --check` PASS.
18. Brak nowych decyzji produktowych w kodzie/testach.

## AUDIT INSTRUCTIONS FOR CODEX

Audyt nie może ograniczyć się do sprawdzenia, że istnieje penalty/zmienna `reshuffle`.

Musi wykazać, że rozwiązanie z większą liczbą roszad nie może wygrać nad rozwiązaniem z mniejszą liczbą roszad z powodu ordinary SOFT.

Wymagana jest niezależna adversarial test matrix dla co najmniej przypadków A, B, C, D, E i H.

Jeżeli implementacja używa jednej ważonej funkcji celu zamiast konstrukcyjnej optymalizacji leksykograficznej, audyt ma oznaczyć to jako FAIL kontraktu, chyba że architekt wcześniej jawnie zmieni ten Task Contract.

## PROCESS

CC zaczyna T006 dopiero z base, w którym `REPLAN-MIN-01` jest obecne jako Frozen Product Contract addendum.

Przed pracą uruchamia standardowy `task_init.py ROTA-T006` na wybranym base SHA.

CC implementuje; nie zatwierdza własnej architektury.

Codex audytuje dokładny implementation SHA.

Po audycie implementacja wraca do architekta do finalnego architectural PASS/FAIL.

Merge do `main` pozostaje wyłącznie decyzją właściciela.

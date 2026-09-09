# ROTA-T058 — HARD zakaz trzeciej kolejnej służby

STATUS: ARCHITECT_SCOPE_SPLIT — HARD PART ONLY

BASE_MAIN_SHA: `298ddb9557455a574959876c38be1ebd7493319a`
SOURCE_FINDING: `arch/FINDING_2026-09-05_SOLVER_RHYTHM_VS_TARGET_PRECISION.md` @ `c174c2e`
OWNER_CORRECTION: main@`500b337dd86f43c7d978c9afc2b4a7ccabd13249`
PREIMPLEMENTATION_AUDIT_R1: `tasks/ROTA-T058/round_01/tests/tests_r1.txt` @ `c21e80f`
PREIMPLEMENTATION_AUDIT_R2: `tasks/ROTA-T058/round_01/tests/tests_r2.txt` @ `3e49b1a`
ARCHITECT_SPLIT_EVIDENCE: `arch/FINDING_2026-09-08_T058_EQUITY_DEADBAND_CPSAT_PERFORMANCE.md`
R6_EVIDENCE: `tasks/ROTA-T058/round_01/tests/tests_r6.txt` @ `2466f4e`

## 1. Cel

T058 implementuje wyłącznie nowy HARD dla automatycznego planowania:

1. PLAN/REPLAN/Przelicz Plan nigdy sam nie tworzy trzeciej kolejnej PRIMARY służby tego samego pracownika na trzech kolejnych datach rozpoczęcia;
2. ręczna korekta koordynatora może świadomie utworzyć taki układ, ale program musi go oflagować jako Deviation i zapisać ślad decyzji człowieka;
3. fixed/boundary/rozpoczęte fakty są zachowywane, lecz blokują dołożenie nowej trzeciej służby;
4. NIGHT-STREAK-01, TARGET-01 i ogólny rytm D/N/W/W nie zmieniają semantyki.

OWNEROWE wymaganie 24h tolerancji equity NIE JEST ODRZUCONE. Zostało wydzielone do osobnego zadania solver-engineering, ponieważ realny pomiar wykazał, że zarówno deadband, jak i samo podbicie istniejącej wagi destabilizują dowodzenie optymalności przez kaskadę wag w `_add_combined_objective`. T058 nie może ryzykować regresji całego planera.

## 2. Zamrożony kontrakt OWNERA

### 2.1 HARD wiąże automat

Dla jednego pracownika każda NOWA automatyczna sekwencja PRIMARY służb rozpoczynających się na trzech kolejnych datach kalendarzowych jest zabroniona.

Jedna data rozpoczęcia liczy się raz także dla pracy 24h D+N. Nie liczyć TRAINEE ani PERIODIC_TRAINING. Nie budować reguły z surowego `any_term`, który obejmuje te role.

PLAN/REPLAN/Przelicz Plan nie dostaje wyjątku przez `DECISION_REQUIRED`. Jeżeli solver musiałby dołożyć trzecią kolejną służbę, nie zwraca takiego kandydata jako FEASIBLE. UI/API pokazuje czytelny komunikat.

### 2.2 HARD nie odbiera władzy koordynatorowi

Ręczna korekta pozostaje ścieżką świadomej decyzji człowieka. Może zapisać naruszenie nowego HARD.

Wtedy istniejący pion `validate -> materialize_deviations -> coordinator action`:
- wykrywa nazwane naruszenie,
- zapisuje Deviation,
- zapisuje ślad decyzji koordynatora,
- pokazuje czytelną polską etykietę zamiast technicznego kodu.

Nie tworzyć nowej tabeli, DTO, systemu wyjątków ani osobnego `DECISION_REQUIRED`.

T058 nie dodaje własnej blokady PDF/eksportu.

### 2.2A ARCHITECT_RULING 2026-09-09 — trwałość świadomej przyszłej korekty

R6-01 potwierdził lukę T58-06: przyszła PRIMARY ręcznie zmieniona przez koordynatora pozostaje `PLANNED` i `frozen=False`, więc późniejszy Przelicz Plan traktuje ją jak zwykły redistributable Assignment i może cicho cofnąć dokładnie tę decyzję człowieka.

W T058 obowiązuje następujące rozwiązanie:

1. W `apply_manual_correction`, po walidacji skorygowanego stanu i PRZED utworzeniem wersji potomnej, należy wykorzystać pełne `ViolationDetail.assignment_ids` dostępne w `report.violation_details`.
2. Dla `ViolationDetail.rule == "THIRD-CONSECUTIVE-SHIFT-01"` należy wyznaczyć przecięcie `assignment_ids` z Assignmentami faktycznie przekazanymi w `upsert_assignments` tej korekty.
3. Wyłącznie te faktycznie edytowane Assignmenty, które należą do naruszenia utworzonego/utrzymanego przez świadomą korektę, mają zostać zapisane z `frozen=True` w wersji potomnej.
4. Nie wolno automatycznie zamrażać pozostałych Assignmentów z trzydniowego okna. W szczególności nie zamrażać pierwszego elementu okna tylko dlatego, że `Deviation.affected_assignment_or_employee` na niego wskazuje.
5. Nie wolno definiować ochrony przez ogólne „Assignment ma powiązany Deviation”, bo zmieniłoby to redistributability dla innych reguł (np. REST-01/LOAD-01) poza T058.
6. `frozen=True` jest tutaj istniejącym markerem „automat nie redystrybuuje tego Assignmentu”; nie tworzymy nowego statusu, tabeli ani równoległej pamięci decyzji.
7. Późniejsza jawna ręczna korekta koordynatora nadal może zmienić/unfreeze taki Assignment zgodnie z istniejącymi prawami ręcznej korekty. T058 blokuje tylko ciche cofnięcie przez automat.
8. Action trail i after-state muszą odzwierciedlać rzeczywiście zapisany `frozen=True`, a nie pierwotny obiekt z `upsert_assignments` przed tą transformacją.

Ta zmiana jest ograniczona wyłącznie do ochrony jawnej ręcznej decyzji, która uczestniczy w `THIRD-CONSECUTIVE-SHIFT-01`. Nie rozszerza praw koordynatora ani semantyki innych Deviation.

### 2.3 Fixed facts i granice miesiąca

Służby rozpoczęte/odbyte oraz inne jawnie zapisane fakty nie mogą być cofane przez automat.

W pełni fixed historyczne okno trzech kolejnych służb samo w sobie nie blokuje niezwiązanej przyszłości. Jednak fixed/boundary facts uczestniczą w ocenie nowej decyzji solvera: dwa wcześniejsze dni + nowa trzecia służba = nowa służba zablokowana.

Reguła działa przez granicę miesiąca.

### 2.3A ARCHITECT_RULING 2026-09-08 — diagnostyka fixed/mixed boundary

To rozstrzygnięcie jest wiążące dla implementacji T058:

1. **W pełni istniejące/fixed/historyczne okno** trzech kolejnych służb nie jest nową decyzją solvera. Nie wolno mapować go wyłącznie z powodu nowego T058 na `TECHNICAL_ERROR` ani na nowe `DECISION_REQUIRED`, które zatrzymuje niezwiązaną przyszłość. Fakt pozostaje zachowany i może pozostać widoczny jako istniejące odchylenie/ślad decyzji człowieka, ale automat ma móc planować późniejsze, niezwiązane dni.
2. **Okno mieszane przez granicę miesiąca**, w którym część dni jest już accepted/fixed/boundary, a co najmniej jedna NOWA decyzja solvera domyka zabronione trzy kolejne daty, jest zwykłym przypadkiem nowego HARD. Kandydat ma zostać zablokowany i zdiagnozowany jako truthful non-decision `THIRD_CONSECUTIVE_SHIFT_BLOCKED` (lub dokładnie ten sam publiczny status/komunikat, którego T058 używa dla nowego HARD), nigdy generyczny `TECHNICAL_ERROR` i bez coordinator override.
3. Jeśli dwa fixed dni leżą w miesiącu N+1, a REPLAN/Przelicz miesiąca N próbowałby dołożyć służbę tworzącą okno przez granicę, accepted miesiąc N+1 pozostaje faktem; solver ma zmienić własną nową propozycję w N, nie przepisywać N+1.
4. Samo dopisanie `THIRD-CONSECUTIVE-SHIFT-01` do mechanizmu przeznaczonego dla „frozen boundary requires decision” nie jest poprawnym rozwiązaniem, jeżeli skutkiem jest blokowanie w pełni historycznego okna wbrew punktowi 1.

### 2.4 Bez zmian w pozostałych priorytetach

- NIGHT-STREAK-01 pozostaje własnym HARD i zachowuje dotychczasowy lifecycle.
- D/N/W/W pozostaje SOFT.
- TARGET-01 pozostaje bez zmian.
- T058 NIE zmienia equity, equal-split ani wag objective.

### 2.5 ARCHITECT_RULING 2026-09-08 — wiele prawdziwych HARD naraz

T058 nie wprowadza hierarchii diagnostycznej między niezależnymi regułami HARD tylko po to, aby zachować stare testy.

Jeżeli stan rzeczywiście narusza równocześnie np. LOAD-01/SiteRule i `THIRD-CONSECUTIVE-SHIFT-01`, oba fakty są prawdziwe. Kod nie może uciszać nowego HARD ani sztucznie nadawać starszej regule pierwszeństwa wyłącznie dla stabilności fixture/testu.

Test, którego celem jest izolacja jednej reguły/provenance, ma skonstruować stan, w którym pozostałe niezależne HARD nie są przypadkowo naruszone. Wolno zmienić wyłącznie fixture/setup konieczny do zachowania pierwotnego celu testu; nie wolno osłabiać assertion dotyczącej badanej reguły ani zmieniać kontraktu produktu, żeby test stał się zielony.

## 3. Acceptance

T58-01: automatyczny PLAN/REPLAN/Przelicz Plan nie proponuje nowej trzeciej kolejnej PRIMARY służby tego samego pracownika na trzech kolejnych datach rozpoczęcia.

T58-02: jedna data liczy się raz; TRAINEE/S1 nie liczą się do nowego HARD; 24h D+N nie liczy się podwójnie.

T58-03: zakaz działa przez granicę miesiąca i wobec fixed/boundary facts przy dokładaniu nowej służby.

T58-04: brak legalnej automatycznej obsady nie prowadzi do coordinator override; brak FEASIBLE kandydata łamiącego HARD i jest czytelny komunikat.

T58-05: ręczna korekta może świadomie zapisać naruszenie; validator materializuje nazwane Deviation, action trail zapisuje decyzję, API/UI pokazuje polską etykietę.

T58-06: późniejszy automat nie cofa ręcznie zaakceptowanej/odbytej decyzji; jeśli przyszły ręcznie edytowany Assignment uczestniczy w świadomie zapisanym `THIRD-CONSECUTIVE-SHIFT-01`, dokładnie ten edytowany Assignment jest chroniony przed późniejszą automatyczną redystrybucją.

T58-07: NIGHT-STREAK-01 nie jest osłabione.

T58-08: D/N/W/W pozostaje SOFT.

T58-09: TARGET-01 pozostaje bez zmian.

T58-10: solver i validator zgadzają się co do reprezentatywnych scenariuszy nowego HARD przy zachowaniu niezależności walidacji.

T58-11: T058 nie dodaje blokady PDF/eksportu ani nowego subsystemu wyjątków.

T58-12: T058 nie zmienia `add_target_equity_fairness`, `add_equal_split_fairness`, ich semantyki, wag ani deadbandu; ten temat należy do osobnego tasku solver-engineering.

T58-13: mieszane okno boundary, w którym nowa decyzja solvera domyka trzecie kolejne rozpoczęcie, kończy się czytelnym `THIRD_CONSECUTIVE_SHIFT_BLOCKED`, nie `TECHNICAL_ERROR`.

T58-14: w pełni fixed/historyczne trzydniowe okno nie powoduje samo z siebie nowego `DECISION_REQUIRED` i nie blokuje planowania niezwiązanej przyszłości.

T58-15: R6 repro: ręczna przyszła zmiana Assignmentu, która świadomie domyka `THIRD-CONSECUTIVE-SHIFT-01`, pozostaje na tym Assignmentie po późniejszym Przelicz Plan; ochrona nie przenosi się na inne Assignmenty z okna i nie opiera się na skróconym `Deviation.affected_assignment_or_employee`.

## 4. Zakaz rozszerzania zakresu

Poza T058:
- 24h equity deadband;
- zmiana `DN_RHYTHM_REWARD_WEIGHT`, `TARGET_EQUITY_WEIGHT`, `TARGET_DEVIATION_WEIGHT`, `EQUAL_SPLIT_FAIRNESS_WEIGHT` lub kaskady `target_weight/equal_split_weight/prefer_local_weight`;
- przebudowa `_add_combined_objective`;
- zmiana REST-01, LOAD-01, MEMBERSHIP-01;
- zmiana NIGHT-STREAK-01 poza współistnieniem;
- nowe ustawienia i wyjątki;
- refaktoryzacje przy okazji.

## 5. EXACT TASK_SCOPE — FROZEN

READ_ONLY_EVIDENCE:
- arch/FINDING_2026-09-05_SOLVER_RHYTHM_VS_TARGET_PRECISION.md
- arch/FINDING_2026-09-08_T058_EQUITY_DEADBAND_CPSAT_PERFORMANCE.md
- BOARD.md
- tasks/ROTA-T058/round_01/tests/tests_r1.txt
- tasks/ROTA-T058/round_01/tests/tests_r2.txt
- tasks/ROTA-T058/round_01/tests/tests_r6.txt

TASK_SCOPE:
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/fairness.py
- rota/planning/validator.py
- rota/planning/engine.py
- rota/planning/engine_types.py
- rota/application/plan_ops.py
- rota/application/manual_edit.py
- rota/application/deviation_mapping.py
- api/routers/schedule.py
- frontend/src/api/client.ts
- frontend/src/screens/MonthlyPlanning.tsx
- tests/test_t034_third_consecutive_shift_soft.py
- tests/test_t058.py
- tests/test_t019b.py
- tests/test_t011_b_context_discovery.py
- tests/test_t011_c_site_coordinator_lifecycle.py
- tests/test_t011_d_quarter_balance.py
- tests/test_t011_e_pipeline_e2e_hard_stop.py
- tests/test_t041_checkpoint_b.py
- tests/test_audit_r13_findings.py
- tests/test_audit_t007_r3.py
- tests/test_audit_t007_r4.py
- tests/test_audit_t007_r5.py

`fairness.py` i `solver.py` wolno zmieniać tylko w zakresie usunięcia starego T034 third-shift SOFT i wpięcia nowego HARD; nie wolno zmieniać equity/equal-split/łańcucha wag.

`engine_types.py`, `plan_ops.py`, `frontend/src/api/client.ts` i `MonthlyPlanning.tsx` wolno zmieniać wyłącznie dla truthful non-decision statusu i jego czytelnej prezentacji.

`manual_edit.py` wolno zmienić wyłącznie w celu T58-06/T58-15: po `validate()` użyć pełnych `ViolationDetail.assignment_ids` nowej reguły i zapisać `frozen=True` tylko na faktycznie edytowanych Assignmentach z `upsert_assignments`, które należą do tego naruszenia; nie zmieniać ogólnej semantyki manual correction, REALIZED ani innych Deviation.

`deviation_mapping.py` wyłącznie o mapowanie nowej reguły do istniejącej kategorii; `api/routers/schedule.py` wyłącznie o polską etykietę nowego Deviation.

Dodatkowe pliki testowe powyżej wolno zmieniać wyłącznie w setup/fixture koniecznym do zachowania ich pierwotnej izolacji po wejściu nowego HARD. Nie wolno zmieniać oczekiwanego zachowania reguły, którą dany test faktycznie audytuje.

Jeżeli implementacja wymaga innego istniejącego pliku, STOP i powrót do Architekta przed edycją.

## 6. Handoff po rozdzieleniu

CC ma zachować działającą część HARD, wycofać z worktree wszystkie eksperymenty deadband/reweight/objective-chain i przygotować czysty delivery T058 tylko dla acceptance T58-01..T58-15.

Po delivery: targetowane testy + realny pion PLAN/Przelicz Plan, w tym R6 repro, + przekazanie Codexowi exact SHA. Pełny redesign objective nie jest warunkiem ukończenia T058.
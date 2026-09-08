# ROTA-T058 — HARD zakaz trzeciej kolejnej służby

STATUS: ARCHITECT_SCOPE_SPLIT — HARD PART ONLY

BASE_MAIN_SHA: `298ddb9557455a574959876c38be1ebd7493319a`
SOURCE_FINDING: `arch/FINDING_2026-09-05_SOLVER_RHYTHM_VS_TARGET_PRECISION.md` @ `c174c2e`
OWNER_CORRECTION: main@`500b337dd86f43c7d978c9afc2b4a7ccabd13249`
PREIMPLEMENTATION_AUDIT_R1: `tasks/ROTA-T058/round_01/tests/tests_r1.txt` @ `c21e80f`
PREIMPLEMENTATION_AUDIT_R2: `tasks/ROTA-T058/round_01/tests/tests_r2.txt` @ `3e49b1a`
ARCHITECT_SPLIT_EVIDENCE: `arch/FINDING_2026-09-08_T058_EQUITY_DEADBAND_CPSAT_PERFORMANCE.md`

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

### 2.3 Fixed facts i granice miesiąca

Służby rozpoczęte/odbyte oraz inne jawnie zapisane fakty nie mogą być cofane przez automat.

W pełni fixed historyczne okno trzech kolejnych służb samo w sobie nie blokuje niezwiązanej przyszłości. Jednak fixed/boundary facts uczestniczą w ocenie nowej decyzji solvera: dwa wcześniejsze dni + nowa trzecia służba = nowa służba zablokowana.

Reguła działa przez granicę miesiąca.

### 2.4 Bez zmian w pozostałych priorytetach

- NIGHT-STREAK-01 pozostaje własnym HARD i zachowuje dotychczasowy lifecycle.
- D/N/W/W pozostaje SOFT.
- TARGET-01 pozostaje bez zmian.
- T058 NIE zmienia equity, equal-split ani wag objective.

## 3. Acceptance

T58-01: automatyczny PLAN/REPLAN/Przelicz Plan nie proponuje nowej trzeciej kolejnej PRIMARY służby tego samego pracownika na trzech kolejnych datach rozpoczęcia.

T58-02: jedna data liczy się raz; TRAINEE/S1 nie liczą się do nowego HARD; 24h D+N nie liczy się podwójnie.

T58-03: zakaz działa przez granicę miesiąca i wobec fixed/boundary facts przy dokładaniu nowej służby.

T58-04: brak legalnej automatycznej obsady nie prowadzi do coordinator override; brak FEASIBLE kandydata łamiącego HARD i jest czytelny komunikat.

T58-05: ręczna korekta może świadomie zapisać naruszenie; validator materializuje nazwane Deviation, action trail zapisuje decyzję, API/UI pokazuje polską etykietę.

T58-06: późniejszy automat nie cofa ręcznie zaakceptowanej/odbytej decyzji; historyczne fixed okno nie blokuje niezwiązanej przyszłości.

T58-07: NIGHT-STREAK-01 nie jest osłabione.

T58-08: D/N/W/W pozostaje SOFT.

T58-09: TARGET-01 pozostaje bez zmian.

T58-10: solver i validator zgadzają się co do reprezentatywnych scenariuszy nowego HARD przy zachowaniu niezależności walidacji.

T58-11: T058 nie dodaje blokady PDF/eksportu ani nowego subsystemu wyjątków.

T58-12: T058 nie zmienia `add_target_equity_fairness`, `add_equal_split_fairness`, ich semantyki, wag ani deadbandu; ten temat należy do osobnego tasku solver-engineering.

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
- rota/application/manual_edit.py

TASK_SCOPE:
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/fairness.py
- rota/planning/validator.py
- rota/planning/engine.py
- rota/planning/engine_types.py
- rota/application/plan_ops.py
- rota/application/deviation_mapping.py
- api/routers/schedule.py
- frontend/src/api/client.ts
- frontend/src/screens/MonthlyPlanning.tsx
- tests/test_t034_third_consecutive_shift_soft.py
- tests/test_t058.py

`fairness.py` i `solver.py` wolno zmieniać tylko w zakresie usunięcia starego T034 third-shift SOFT i wpięcia nowego HARD; nie wolno zmieniać equity/equal-split/łańcucha wag.

`engine_types.py`, `plan_ops.py`, `frontend/src/api/client.ts` i `MonthlyPlanning.tsx` wolno zmieniać wyłącznie dla truthful non-decision statusu i jego czytelnej prezentacji.

`deviation_mapping.py` wyłącznie o mapowanie nowej reguły do istniejącej kategorii; `api/routers/schedule.py` wyłącznie o polską etykietę nowego Deviation.

Jeżeli implementacja wymaga innego istniejącego pliku, STOP i powrót do Architekta przed edycją.

## 6. Handoff po rozdzieleniu

CC ma zachować działającą część HARD, wycofać z worktree wszystkie eksperymenty deadband/reweight/objective-chain i przygotować czysty delivery T058 tylko dla acceptance T58-01..T58-12.

Po delivery: targetowane testy + realny pion PLAN + przekazanie Codexowi exact SHA. Pełny redesign objective nie jest warunkiem ukończenia T058.

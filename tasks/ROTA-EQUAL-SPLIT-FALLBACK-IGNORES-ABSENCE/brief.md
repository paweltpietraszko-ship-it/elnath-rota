# ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE — komplet celów godzinowych i DEL w pozostałym celu

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS AND CC MERIT PASS

BASE_MAIN_SHA: `c4fad96788bf13f14b1a63e0dc9e6071d17e4355`
SOURCE_REQUEST: `BOARD.md` / `ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE`

## 1. Decyzje OWNERA

1. PLAN nie może rozpocząć się, dopóki każdy aktywny pracownik LOCAL danego
   Site nie ma celu godzinowego na wybrany miesiąc.
2. Po zapisaniu celu jednej osobie koordynator może wybrać automatyczne
   ustawienie tej samej wartości wszystkim aktywnym pracownikom LOCAL tego
   Site. Wybór nadpisuje również ich wcześniejsze, odmienne cele.
3. Pracownicy z Urlopem, L4 albo DELEGACJĄ nie są pomijani w operacji zbiorczej.
4. Godziny DELEGACJI realizują część celu. Przykład: cel `168 h` i `35 h DEL`
   oznaczają cel około `133 h` zwykłych Assignmentów.
5. DELEGACJA jest bieżącym, edytowalnym AvailabilityRecord. Po jej zmianie lub
   anulowaniu REPLAN używa aktualnego rekordu: usunięte godziny DEL przestają
   realizować cel, a solver może uzupełnić powstałą różnicę zwykłą pracą.

## 2. Zachowanie koordynatora

### Brak celu

Przed PLAN, REPLAN, ponowieniem i szerszym wyszukiwaniem backend sprawdza
kompletność celów dla wszystkich `enabled` memberships `LOCAL` danego Site i
miesiąca. Brak choć jednego celu zatrzymuje operację przed uruchomieniem solvera
i przed utworzeniem lub zastąpieniem wersji/podglądu.

Ekran pokazuje po polsku listę brakujących osób oraz instrukcję ustawienia
celów. To kontrolowany blocker danych wejściowych, nie `DECISION_REQUIRED` i nie
`TECHNICAL_ERROR`. Po uzupełnieniu celów koordynator ponawia tę samą operację.
EXTERNAL_SUPPORT nie otrzymuje celu i nie uczestniczy w gate.

### Wspólny kontrakt blockera

Jeden owner blockera znajduje się w `rota/application/plan_ops.py`:
`require_complete_target_hours(conn, site_id, month)` odczytuje istniejącym
batchem cele aktywnych `LOCAL` i albo kończy bez wyniku, albo zgłasza
`TargetHoursRequired` z deterministyczną listą brakujących `employee_id`.
PLAN oraz wszystkie wejścia rodziny REPLAN/retry/wider-search wywołują ten sam
gate przed solverem i przed zapisem wersji/podglądu.

`api/routers/schedule.py` jest jedynym ownerem serializacji tego blockera do UI.
Dodaje małe DTO:

- `MissingTargetHoursEmployeeOut`: `employee_id`, `employee_display_name`.

Istniejące `PrecheckOut` i `PlanningResultOut` dostają to samo pole:

- `missing_target_hours: list[MissingTargetHoursEmployeeOut]`, domyślnie `[]`.

Gdy gate zgłosi brak celu, oba kontrakty używają dokładnie:

- `status="TARGET_HOURS_REQUIRED"`;
- `missing_target_hours` z tymi samymi brakującymi `employee_id` i polskimi
  nazwami użytkowymi, w deterministycznej kolejności `employee_display_name`,
  następnie `employee_id`;
- brak `DECISION_REQUIRED` i brak `TECHNICAL_ERROR`.

Dla `PlanningResultOut` blocker ma `candidates=[]`, `decision_payload=None`,
`error_message=None`, `optimization_complete=False`; istniejące `warnings`
pozostaje zwykłym polem ostrzeżeń i nie przenosi listy brakujących osób.
Dla `PrecheckOut` dotychczasowe `under_covered_demand_ids` pozostaje `[]` w tym
statusie. Po przejściu gate dotychczasowy heurystyczny precheck niedoboru
pokrycia działa bez zmian.

`rota/application/precheck.py` nie jest ownerem celów godzinowych i nie jest
zmieniany przez ten Task. Endpoint prechecku używa najpierw wspólnego gate z
`plan_ops.py`, a dopiero po jego przejściu wywołuje istniejący `precheck(state)`.

### Ustawienie wszystkim

Po poprawnym zapisaniu celu jednej osobie `TargetHoursEditor` pokazuje jedną
propozycję: `Ustawić {N} h wszystkim pracownikom tego obiektu na {miesiąc}?`.

- `Tak` wywołuje jedną atomową operację backendu dla wszystkich aktywnych LOCAL
  memberships Site, łącznie z osobami nieobecnymi/delegowanymi i łącznie z
  osobami mającymi wcześniej inny cel.
- `Nie` pozostawia zapis tylko dla bieżącej osoby; pozostałe braki nadal blokują
  planowanie.
- Awaria operacji zbiorczej nie może pozostawić części pracowników z nową
  wartością. UI pokazuje błąd i pozwala ponowić zapis.

## 3. Bilans i DELEGACJA

Nie zmieniać `WorkBalance`: `rota/balance.py` nadal dolicza DEL do
`planned_hours`, a `realized_hours` pozostaje bez zmian.

W `rota/planning/solver.py::_effective_targets` cel zwykłych Assignmentów dla
pracownika wynosi:

`max(0, target_hours - absence_hours - delegation_hours_in_month)`

`absence_hours` zachowuje obecną semantykę Urlopu/L4. Godziny DEL są liczone
wyłącznie przez istniejący
`rota/planning/absence.py::delegation_hours_in_range` na bieżących, aktywnych
rekordach z `PlanningState.availability_records`. Solver nie odtwarza tej
arytmetyki i nie odejmuje całego `WorkBalance.planned_hours`, ponieważ zawiera
ono również Assignmenty liczone już przez `_fixed_hours_by_employee`.

Zmiana/supersede/deaktywacja DELEGACJI korzysta z istniejącego unieważnienia
miesiąca. Następny REPLAN składa świeży `PlanningState`, więc nie używa starej
wartości DEL.

## 4. Usunięcie fallbacku

Po skutecznym gate wektor celów jest zawsze kompletny. Usunąć produkcyjną
ścieżkę `target_vector_complete == False`, wywołanie
`add_equal_split_fairness` oraz martwy helper z `rota/planning/fairness.py`.
TARGET-01 i target equity pozostają jedyną ścieżką sprawiedliwości godzinowej.
Nie zmieniać weekend/holiday/rhythm ani wag dla kompletnego wektora.

## 5. Minimalne szwy

- `rota/application/plan_ops.py`: jeden wspólny gate
  `require_complete_target_hours` i kontrolowany `TargetHoursRequired`, używane
  przez PLAN oraz wszystkie wejścia REPLAN/retry/wider-search przed solverem i
  zapisem; bez drugiej walidacji kompletności celów.
- `rota/persistence/work_balance_repository.py`: istniejący batch odczytu celów;
  bez nowej tabeli i bez drugiej księgi.
- `rota/application/durable_inputs.py`: nowa atomowa operacja
  `set_target_hours_for_site_roster`, korzystająca z
  `write_work_balance_target_in_open_transaction` i istniejącego zapisu działań.
- `api/routers/durable_inputs.py`: `POST
  /workspace/sites/{site_id}/target-hours/{month}/apply-to-all` z jednym
  `target_hours`, walidowanym identycznie jak obecny zapis jednostkowy.
- `api/routers/schedule.py`: jedna serializacja `TARGET_HOURS_REQUIRED` do
  wspólnego `MissingTargetHoursEmployeeOut` dla precheck oraz całej rodziny
  PLAN/REPLAN; nazwy pracowników pobiera istniejącym batchem.
- `frontend/src/screens/EmployeeDetail.tsx`: propozycja po zapisie jednostkowym.
- `frontend/src/screens/MonthlyPlanning.tsx`: renderuje wspólny blocker i nie
  uruchamia planowania do czasu uzupełnienia celów.

## 6. Acceptance

- `TH-01`: brak celu jednej aktywnej osoby LOCAL zatrzymuje PLAN przed solverem
  i przed zapisem wersji/podglądu; odpowiedź ma status
  `TARGET_HOURS_REQUIRED` i podaje jej `employee_id` oraz polską nazwę.
- `TH-02`: ten sam gate i ten sam payload `missing_target_hours` obejmują
  REPLAN, retry, wider-search oraz endpoint prechecku; brak celu nie jest
  `DECISION_REQUIRED` ani `TECHNICAL_ERROR`.
- `TH-03`: EXTERNAL_SUPPORT i wyłączona membership nie blokują.
- `TH-04`: wybór automatyczny zapisuje tę samą wartość wszystkim aktywnym LOCAL,
  także Urlop/L4/DEL, i nadpisuje wcześniejsze cele atomowo.
- `TH-05`: odmowa automatycznego ustawienia zachowuje tylko zapis bieżącej osoby.
- `TH-06`: przy celu 168 i 35 h aktywnej DEL solver liczy cel zwykłych zmian jako
  133 h; DEL nie jest jednocześnie liczone jako Assignment.
- `TH-07`: po anulowaniu tej DEL i REPLAN cel zwykłych zmian wraca do 168 h;
  stare DEL nie pozostaje w solverze.
- `TH-08`: Urlop/L4 nadal pomniejszają cel dotychczasową ścieżką, a brak
  DELEGACJI nie zmienia wyników kompletnego TARGET-01.
- `TH-09`: produkcja nie wywołuje `add_equal_split_fairness`; helper zostaje
  usunięty z `rota/planning/fairness.py` wraz z jedynym produkcyjnym call site
  i importem w `rota/planning/solver.py`.
- `TH-10`: przy `TARGET_HOURS_REQUIRED` `PlanningResultOut` ma `candidates=[]`,
  `decision_payload=None`, `error_message=None`, `optimization_complete=False`,
  a `PrecheckOut.under_covered_demand_ids=[]`; lista osób nie jest kodowana w
  `warnings` ani w komunikacie błędu.

## 7. OUT_OF_SCOPE

- zmiana sposobu wyliczania ustawowej/miesięcznej normy;
- automatyczne proponowanie różnej wartości per pracownik;
- cele dla EXTERNAL_SUPPORT;
- zmiana semantyki Urlopu/L4/DEL albo Availability lifecycle;
- nowy typ DecisionRequired;
- druga implementacja gate w `precheck.py` lub routerze;
- zmiana pozostałych funkcji fairness.

## 8. TASK_SCOPE

TASK_SCOPE:
- `tasks/ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE/**`
- `rota/planning/solver.py`
- `rota/planning/fairness.py`
- `rota/application/plan_ops.py`
- `rota/application/durable_inputs.py`
- `rota/persistence/work_balance_repository.py`
- `api/routers/durable_inputs.py`
- `api/routers/schedule.py`
- `frontend/src/api/client.ts`
- `frontend/src/screens/EmployeeDetail.tsx`
- `frontend/src/screens/MonthlyPlanning.tsx`
- `tests/test_target_hours_required.py` (nowy)
- `tests/test_t041_checkpoint_a.py`
- `tests/test_t009_open_and_assembler.py`
- `tests/test_replan_minimal_reshuffle.py`
- `frontend/e2e/target-hours-required.spec.ts` (nowy)
- `frontend/e2e/t041-daily-workflow.spec.ts`

`rota/application/precheck.py` pozostaje istniejącym ownerem heurystycznego
prechecku pokrycia i jest używany bez zmian, dlatego nie należy do TASK_SCOPE.
Każdy inny plik produkcyjny wymaga STOP i korekty briefu. Testy historyczne
fallbacku należy zastąpić testami gate, nie utrzymywać dwóch sprzecznych
kontraktów.

## 9. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS:
  - `rota/application/plan_ops.py --symbol require_complete_target_hours`
  - `rota/planning/solver.py --symbol add_equal_split_fairness`
  - `rota/planning/solver.py --symbol _effective_targets`
  - `rota/planning/fairness.py --symbol add_equal_split_fairness`
  - `api/routers/schedule.py --symbol PrecheckOut`
  - `api/routers/schedule.py --symbol PlanningResultOut`
  - `frontend/src/screens/MonthlyPlanning.tsx`
  - `frontend/src/screens/EmployeeDetail.tsx`
- REASON: Task dodaje wspólny gate, usuwa produkcyjny fallback/helper i zmienia szwy API/UI blockera; mapa ma potwierdzić call site i ownership bez poszerzania zakresu.

Jeżeli nowy symbol `require_complete_target_hours` nie istnieje jeszcze na bazie,
przed implementacją uruchomić `where.py` dla samego `rota/application/plan_ops.py`,
a po dodaniu symbolu używać wariantu `--symbol`. Dla pozostałych TARGETS
uruchomić dokładnie wskazane celowane mapy. Wynik `where.py` jest wyłącznie
dowodem wyszukania i nie rozszerza TASK_SCOPE.

## 10. Weryfikacja

Wąska macierz:
1. jeden gate i jeden payload blockera bez zapisu ubocznego dla precheck, PLAN i
   całej rodziny REPLAN;
2. atomowy bulk overwrite + odmowa propozycji;
3. solver target z częściowym DEL i po anulowaniu DEL;
4. zachowanie kompletnego TARGET-01 oraz Urlopu/L4;
5. jeden pion API/UI: zapis celu -> wybór „wszyscy” -> PLAN odblokowany.

Nie uruchamiać pełnej regresji bez odrębnej zgody OWNERA. Implementacja zaczyna
się dopiero po `PASS PREIMPLEMENTATION` Codexa i osobnym PASS merytorycznym CC.

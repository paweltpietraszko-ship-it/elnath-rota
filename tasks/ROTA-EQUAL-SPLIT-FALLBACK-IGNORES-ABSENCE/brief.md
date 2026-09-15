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

- `rota/application/plan_ops.py`: jeden wspólny gate wywoływany przez PLAN oraz
  wszystkie wejścia REPLAN/retry/wider-search przed solverem i zapisem.
- `rota/persistence/work_balance_repository.py`: istniejący batch odczytu celów;
  bez nowej tabeli i bez drugiej księgi.
- `rota/application/durable_inputs.py`: nowa atomowa operacja
  `set_target_hours_for_site_roster`, korzystająca z
  `write_work_balance_target_in_open_transaction` i istniejącego zapisu działań.
- `api/routers/durable_inputs.py`: `POST
  /workspace/sites/{site_id}/target-hours/{month}/apply-to-all` z jednym
  `target_hours`, walidowanym identycznie jak obecny zapis jednostkowy.
- `api/routers/schedule.py`: kontrolowana odpowiedź blockera z identyfikatorami
  i polskimi nazwami brakujących osób dla precheck/PLAN/REPLAN.
- `frontend/src/screens/EmployeeDetail.tsx`: propozycja po zapisie jednostkowym.
- `frontend/src/screens/MonthlyPlanning.tsx`: widoczny blocker i brak startu
  planowania do czasu uzupełnienia celów.

## 6. Acceptance

- `TH-01`: brak celu jednej aktywnej osoby LOCAL zatrzymuje PLAN przed solverem
  i przed zapisem wersji/podglądu; komunikat podaje jej polską nazwę.
- `TH-02`: ten sam gate obejmuje REPLAN, retry i wider-search.
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

## 7. OUT_OF_SCOPE

- zmiana sposobu wyliczania ustawowej/miesięcznej normy;
- automatyczne proponowanie różnej wartości per pracownik;
- cele dla EXTERNAL_SUPPORT;
- zmiana semantyki Urlopu/L4/DEL albo Availability lifecycle;
- nowy typ DecisionRequired;
- zmiana pozostałych funkcji fairness.

## 8. TASK_SCOPE

TASK_SCOPE:
- `tasks/ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE/**`
- `rota/planning/solver.py`
- `rota/planning/fairness.py`
- `rota/application/plan_ops.py`
- `rota/application/precheck.py`
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

Każdy inny plik produkcyjny wymaga STOP i korekty briefu. Testy historyczne
fallbacku należy zastąpić testami gate, nie utrzymywać dwóch sprzecznych
kontraktów.

## 9. Weryfikacja

Wąska macierz:
1. gate bez zapisu ubocznego dla PLAN i całej rodziny REPLAN;
2. atomowy bulk overwrite + odmowa propozycji;
3. solver target z częściowym DEL i po anulowaniu DEL;
4. zachowanie kompletnego TARGET-01 oraz Urlopu/L4;
5. jeden pion API/UI: zapis celu -> wybór „wszyscy” -> PLAN odblokowany.

Nie uruchamiać pełnej regresji bez odrębnej zgody OWNERA. Implementacja zaczyna
się dopiero po `PASS PREIMPLEMENTATION` Codexa i osobnym PASS merytorycznym CC.

# ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID — bieżące DEL w siatce miesiąca

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS AND CC MERIT PASS

BASE_MAIN_SHA: `c4fad96788bf13f14b1a63e0dc9e6071d17e4355`
SOURCE_REQUEST: `BOARD.md` / `ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID`

## 1. Cel i decyzje OWNERA

Pracownik LOCAL z aktywną DELEGACJĄ ma pozostać widoczny w siatce „Planowanie
miesiąca”, nawet gdy nie ma żadnego Assignmentu. Dzień delegacji pokazuje
`DEL`, tak samo jak zaakceptowany wydruk.

DELEGACJA nie jest utrwalonym elementem wersji grafiku. Może nie dojść do
skutku: koordynator zmienia, przesuwa albo anuluje rekord, a następnie wykonuje
REPLAN. Siatka i solver mają wtedy użyć bieżącej wersji AvailabilityRecord;
stare `DEL` nie może pozostać w podglądzie ani w zaakceptowanym widoku.

## 2. Źródło danych i granica

Nie tworzyć sztucznego Assignmentu, ShiftDemandu ani kopii DEL w snapshotach
ScheduleVersion/PlanPreview.

`api/routers/schedule.py` składa prezentacyjną projekcję na każdym odczycie lub
wyniku operacji z:

- aktywnych `enabled` memberships `LOCAL` danego Site;
- pracowników obecnych w Assignmentach danego snapshotu/kandydata;
- bieżących aktywnych rekordów `AvailabilityKind.DELEGACJA` przecinających
  wybrany miesiąc.

Rekordy DELEGACJA ładować istniejącym batchem
`rota.persistence.work_balance_repository.delegation_records_for_employees`.
Godziny sumować wyłącznie przez
`rota.planning.absence.delegation_hours_in_range`; router może jedynie rozwinąć
zakres dat rekordu do prezentacyjnych komórek `DEL`.

## 3. Kontrakt odpowiedzi API

W `api/routers/schedule.py` dodać dwa małe DTO:

- `ScheduleEmployeeOut`: `employee_id`, `employee_display_name`;
- `DelegationDayOut`: `employee_id`, `date`, `code="DEL"`, `hours`.

Pola `employees: list[ScheduleEmployeeOut]` oraz
`delegation_days: list[DelegationDayOut]` mają wystąpić w:

- `PlanPreviewOut` — zapisany podgląd po ponownym otwarciu ekranu;
- `PlanningResultOut` — wynik PLAN/REPLAN widoczny natychmiast;
- `MonthViewOut` — bieżąca zaakceptowana/robocza wersja.

`_plan_preview_out`, `_planning_result_out` i `get_month` otrzymują jawne
`site_id` i `month` potrzebne do tej projekcji. Kolejność employees i
delegation_days jest deterministyczna: nazwa/employee_id oraz data.

## 4. Zachowanie siatki

`frontend/src/screens/MonthlyPlanning.tsx::ScheduleGrid` nie wyprowadza już
listy wierszy wyłącznie z Assignmentów. Używa `employees`, Assignmentów i
`delegation_days` z odpowiedzi.

- pracownik z całomiesięczną DEL i bez Assignmentów ma wiersz z `DEL` w każdym
  objętym dniu;
- suma końcowa wiersza obejmuje godziny zwykłych Assignmentów oraz godziny
  bieżących dni DEL;
- jeśli ręczna decyzja pozostawi Assignment w dniu aktywnej DELEGACJI, zachować
  istniejącą precedencję wydruku: komórka pokazuje Assignment, nie drugi symbol;
  istniejące `DELEGACJA-01` nadal komunikuje odchylenie, a suma obejmuje zapisane
  godziny obu faktów;
- pozostali aktywni LOCAL mogą mieć pusty wiersz, jeżeli nie mają Assignmentu
  ani DEL; ten Task nie dodaje etykiet Urlop/L4 do siatki.

## 5. Zmiana i anulowanie DEL

Po edycji, przesunięciu, supersede albo deaktywacji DELEGACJI:

1. istniejący write path Availability i mechanizm unieważnienia miesięcy
   pozostają jedynym ownerem lifecycle;
2. stary PlanPreview nie może być prezentowany jako aktualny;
3. następny `get_month`/PLAN/REPLAN składa `delegation_days` z aktualnego
   chain-end rekordu;
4. anulowany dzień nie pokazuje `DEL` i nie wnosi godzin do sumy;
5. REPLAN może ponownie przydzielić zwykłą pracę zgodnie z dostępnością i
   pozostałym celem godzinowym.

Router nie implementuje własnego cache ani wersjonowania Availability.

## 6. Acceptance

- `DG-01`: bieżący MonthView pokazuje aktywnego LOCAL z całomiesięczną DEL mimo
  zera Assignmentów.
- `DG-02`: natychmiastowy wynik PLAN i zapisany PlanPreview po reloadzie pokazują
  ten sam wiersz i te same dni DEL.
- `DG-03`: każdy objęty dzień ma `DEL`; dni poza zakresem rekordu go nie mają.
- `DG-04`: suma wiersza zawiera `delegation_hours` za każdy objęty dzień dokładnie
  raz i używa canonical helpera.
- `DG-05`: po anulowaniu/przesunięciu rekordu oraz REPLAN stare dni DEL znikają,
  nowe odpowiadają wyłącznie aktywnemu chain-end rekordowi.
- `DG-06`: nie powstaje Assignment, demand ani zapis DEL w ScheduleVersion lub
  PlanPreview persistence.
- `DG-07`: Assignment w dniu DEL zachowuje dotychczasową precedencję wydruku i
  istniejące odchylenie; Task nie wprowadza twardej blokady ręcznej decyzji.
- `DG-08`: employee_display_name jest polską nazwą użytkową; UUID nie zastępuje
  nazwy w siatce.
- `DG-09`: OCHRONA i ORDINARY korzystają z jednego kontraktu odpowiedzi.

## 7. OUT_OF_SCOPE

- utrwalanie DEL w snapshotach grafiku lub podglądu;
- nowy Availability lifecycle albo nowe unieważnianie;
- etykiety Urlop/L4 dla pustych dni siatki;
- zmiana PDF/eksportu;
- zmiana walidatora, solvera lub Deviation lifecycle;
- osobny endpoint tylko dla delegacji.

## 8. TASK_SCOPE

TASK_SCOPE:
- `tasks/ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID/**`
- `api/routers/schedule.py`
- `frontend/src/api/client.ts`
- `frontend/src/screens/MonthlyPlanning.tsx`
- `tests/test_delegation_schedule_grid.py` (nowy)
- `tests/test_t031_schedule_api.py`
- `tests/test_t009_plan_select_replan.py`
- `frontend/e2e/delegation-schedule-grid.spec.ts` (nowy)
- `frontend/e2e/monthly-planning.spec.ts`

`rota/persistence/work_balance_repository.py`, `rota/planning/absence.py`,
`rota/application/schedule_export.py`, persistence PlanPreview/ScheduleVersion,
solver i validator są istniejącymi ownerami używanymi bez zmian i pozostają
poza TASK_SCOPE. Każdy inny plik produkcyjny wymaga STOP i korekty briefu.

## 9. Weryfikacja

Wąska macierz:
1. DTO/helper routera dla current snapshot, świeżego result i persisted preview;
2. jeden pion: aktywna DEL cały miesiąc -> PLAN -> podgląd -> reload -> siatka;
3. drugi pion: anulowanie/przesunięcie DEL -> REPLAN -> brak starego symbolu;
4. UI dla ORDINARY i OCHRONA oraz zgodność sumy godzin;
5. regresja zwykłego pracownika z Assignmentami.

Nie uruchamiać pełnej regresji bez odrębnej zgody OWNERA. Implementacja zaczyna
się dopiero po `PASS PREIMPLEMENTATION` Codexa i osobnym PASS merytorycznym CC.

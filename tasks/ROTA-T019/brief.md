# ROTA-T019 — coordinator analytics read model

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — NOT READY FOR CC
DATE: 2026-08-20
TASK_ID: ROTA-T019
BASE_SHA: 9618477f6014fad63699a154b04730e2b8ff1db2
BASE_BRANCH: main
TASK_BRANCH: task/ROTA-T019
OWNER_SOURCE: arch/T019_coordinator_analytics_architect_brief.md
DEPENDS_ON: T011-D + T014 + T016 + T017 + T018 merged on main
FOLLOWED_BY: T020 print/export; T021 UI

## 1. CEL

Dostarczyć jeden read-only application-level odczyt dla przyszłego ekranu „Analityka”.

Dla wybranego `site_id` i miesiąca odczyt pokazuje wyłącznie członków aktualnej obsady tego Site, ale ich godziny i saldo są globalne — z CURRENT ScheduleVersion wszystkich Site — zgodnie z istniejącą semantyką WorkBalance/EMP-03.

T019 nie tworzy nowego subsystemu analitycznego. Nie dodaje nowych wskaźników, payrollu, formalnej kwalifikacji nadgodzin, UI, wykresów ani eksportu.

## 2. BASELINE / ISTNIEJĄCY KANON

Na exact BASE_SHA `9618477f6014fad63699a154b04730e2b8ff1db2`:

- `WorkBalance` jest pochodnym read modelem: `target_hours`, `planned_hours`, `realized_hours`, `month_balance`, `unresolved_carryover`, `quarter_balance`;
- tylko `target_hours` jest persistowanym wejściem koordynatora;
- WorkBalance liczy wyłącznie Assignment z CURRENT ScheduleVersion każdego relewantnego Site;
- Employee nie należy strukturalnie do jednego Site;
- `planned_hours` i `realized_hours` są rozłączne i pozostają osobnymi wartościami;
- CANCELLED/NN nie są pracą;
- `rota.balance.compute_month_balance()` i `compute_quarter_balance()` są kanonicznym ownerem rachunku godzin i salda;
- T018 `SICK_LEAVE` + `LEAVE_GRANTED` zmniejszają normę WorkBalance tylko za kwalifikujące się dni robocze przy użyciu istniejącego `CalendarDay`;
- brak wymaganej normy nie oznacza zera;
- `balance_read.quarter_balance()` jest fail-closed dla brakującego `target_hours` w którymkolwiek miesiącu kwartału;
- T016 wycofał EMP-02: `Employee.active_from/active_to` są legacy metadata i nie decydują o aktualnej obsadzie; dla planowania źródłem roster authorization jest `SiteMembership.enabled`.

T019 musi zachować wszystkie te znaczenia bez redefinicji.

## 3. ARCHITECTURE DECISION — JEDEN NOWY APPLICATION READ

Dodać dokładnie jeden nowy moduł produkcyjny application-level:

`rota/application/analytics_read.py`

Nie rozszerzać `balance_read.py` do ogólnego agregatora. `balance_read.py` pozostaje małym, istniejącym ownerem jawnego odczytu jednego employee/quarter.

Nowy moduł:

- jest jedynym publicznym entry point T019;
- składa dane roster + target + CURRENT assignments + current availability + CalendarDay;
- nie wykonuje SQL bezpośrednio;
- nie importuje solvera ani PlanningEngine;
- deleguje rachunek wyłącznie do istniejących pure funkcji `rota.balance`;
- nie zapisuje niczego;
- zwraca jeden deterministyczny read model całej obsady.

Publiczny entry point:

`analytics_for_site_month(conn, *, site_id: str, month: date) -> CoordinatorAnalyticsView`

`month` musi być pierwszym dniem miesiąca; nie normalizować cicho dowolnej daty. Nie dodawać coordinator-context guard do tego odczytu — istniejące application reads `open_month()` / `quarter_balance()` są read-only i nie wymagają write authorization.

## 4. MINIMALNY APPLICATION DTO

DTO są lokalne dla `rota/application/analytics_read.py`. Nie dodawać ich do `rota/domain.py`.

### 4.1 AnalyticsDataStatus

Frozen semantic values:

- `AVAILABLE`
- `MONTH_AVAILABLE_QUARTER_UNAVAILABLE`
- `UNAVAILABLE`

Może to być lokalny `str, Enum`.

### 4.2 AnalyticsHoursScope

Jedyna dozwolona wartość T019:

- `ALL_SITES`

Pole jest obowiązkowe na top-level view i jest jawnym kontraktem dla T021: liczby godzin nie są site-local.

Nie dodawać trybu `CURRENT_SITE`, filtra Site ani alternatywnej kalkulacji lokalnej.

### 4.3 AnalyticsMonthData

Frozen fields:

- `month: date`
- `target_hours: int`
- `effective_target_hours: int`
- `planned_hours: int`
- `realized_hours: int`
- `month_balance: int`
- `quarter_balance: int | None`
- `unresolved_carryover: int | None`

`quarter_balance` i `unresolved_carryover` są `None`, gdy pełne narastanie kwartału nie jest wiarygodnie dostępne. Brak danych nie może być reprezentowany przez `0`.

### 4.4 EmployeeAnalyticsRow

Frozen fields:

- `employee_id: str`
- `display_name: str`
- `status: AnalyticsDataStatus`
- `month_data: AnalyticsMonthData | None`
- `quarter_months: tuple[AnalyticsMonthData, ...]`
- `warnings: tuple[str, ...]`

`quarter_months`:

- `AVAILABLE` -> dokładnie 3 miesiące, chronologicznie;
- pozostałe statusy -> `()`.

### 4.5 CoordinatorAnalyticsView

Frozen fields:

- `site_id: str`
- `month: date`
- `quarter_first_month: date`
- `hours_scope: AnalyticsHoursScope`
- `rows: tuple[EmployeeAnalyticsRow, ...]`

Nie dodawać top-level KPI, sum obiektu, średnich, trendów ani osobnej sekcji „nadgodziny”.

## 5. ROSTER FILTER — T016 MUST NOT REGRESS

„Aktywny członek obsady Site” w T019 oznacza:

`SiteMembership.site_id == requested site_id AND SiteMembership.enabled == True`.

Wchodzą oba istniejące membership kinds, jeżeli membership jest enabled:

- LOCAL;
- EXTERNAL_SUPPORT.

T019 NIE używa `Employee.active_from/active_to` do filtrowania. T016 wycofał EMP-02 i analytics nie może go bocznymi drzwiami przywrócić.

Disabled membership nie daje wiersza.

Employee istniejący globalnie, ale bez enabled membership na otwartym Site, nie daje wiersza nawet wtedy, gdy ma godziny na innym Site.

Kolejność `rows`: rosnąco po `employee_id`. Nie polegać na przypadkowej kolejności SQL.

## 6. HOURS SCOPE — GLOBAL ACROSS SITES

Dla roster employee IDs Assignment do WorkBalance pobierać jednym istniejącym batchem:

`get_current_assignments_for_employees(conn, employee_ids, quarter_start_dt, quarter_end_dt)`

bez `exclude_site_id` i bez site-local filtra.

To zachowuje:

- CURRENT-version-only;
- cross-Site sumę;
- CANCELLED exclusion istniejącego repo;
- brak historycznego double count.

T019 nie może rekonstruować site_id z Assignment i odejmować pracy innych Site.

`hours_scope == ALL_SITES` jest zawsze prawdą dla całego wyniku.

## 7. EFFECTIVE TARGET — ZERO DUPLICATION OF T018

T019 ujawnia pole `effective_target_hours`, ale NIE dodaje nowej funkcji liczącej nieobecności i NIE powiela weekend/holiday filtering.

Po kanonicznym `WorkBalance wb = compute_month_balance(...)`:

`effective_target_hours = wb.planned_hours + wb.realized_hours - wb.month_balance`

To jest algebraicznie dokładnie wartość użyta przez istniejący `rota.balance` w równaniu:

`month_balance = planned_hours + realized_hours - effective_target`.

Warunki:

- nie wywoływać `excused_absence_days_in_month()` drugi raz tylko na potrzeby analytics;
- nie dodawać pola do `WorkBalance` ani `domain.py`;
- nie persistować effective target;
- nie dodawać słów sugerujących świadczenie, wynagrodzenie lub ZUS;
- test musi dowodzić zgodności z T018 dla SICK_LEAVE/LEAVE_GRANTED obejmujących weekend/święto.

## 8. BATCH READS — NO N+1

T019 nie może implementować całej obsady przez pętlę `open_month(employee)` / `quarter_balance(employee)` / `reconstruct_month_balance(employee)`.

Application-level odczyt używa stałej liczby batched persistence reads niezależnej od liczby pracowników.

### 8.1 Existing reads reused

Bez zmian publicznej semantyki użyć istniejących:

- `list_memberships_for_site(conn, site_id)`;
- `list_employees(conn)` i mapowanie po `employee_id`;
- `get_current_assignments_for_employees(...)`;
- `list_calendar_days(...)`.

### 8.2 Additive target batch

W `rota/persistence/work_balance_repository.py` dodać jeden minimalny read, np.:

`list_work_balance_targets_for_employees(conn, employee_ids, range_start_month, range_end_month_exclusive) -> dict[str, dict[date, int]]`

Wymagania:

- jeden SELECT dla całej obsady/kwartału;
- tylko podane employee IDs;
- miesiące w `[start, end)`;
- brak wpisu pozostaje brakiem, nigdy zerem;
- deterministyczny rezultat;
- istniejące single-employee API zachowuje publiczną semantykę.

Nazwa może być równoważna, semantyka powyżej jest frozen.

### 8.3 Additive availability batch

W `rota/persistence/availability_repository.py` dodać minimalny batched odpowiednik current+active+overlap dla wielu employees, np.:

`list_active_overlapping_for_employees(conn, employee_ids, range_start, range_end) -> list[AvailabilityRecord]`

Wymagania:

- jeden SELECT dla całej obsady/kwartału;
- dokładnie obecna semantyka current chain-end per `availability_id`;
- active only;
- inclusive date overlap jak `list_active_overlapping`;
- tylko wskazani employees;
- deterministyczne sortowanie co najmniej `(employee_id, availability_id)`;
- nie zmieniać append-only availability history.

Można bezpiecznie współdzielić prywatny row mapper/helper, ale nie przepisywać repozytorium.

### 8.4 N+1 oracle

`tests/test_t019.py` ma użyć `sqlite3.Connection.set_trace_callback` albo równoważnego mechanicznego licznika SELECT i dowieść, że zwiększenie rosteru z 1 do wielu employees nie zwiększa liczby SELECT proporcjonalnie do liczby employees.

Nie zamrażać kruchej dokładnej liczby wszystkich SELECT, jeżeli nie jest to potrzebne; zamrozić brak zależności liniowej od rozmiaru rosteru.

## 9. ONE-SNAPSHOT COMPUTATION

`analytics_for_site_month()` pobiera potrzebne dane przed złożeniem wierszy i następnie liczy w pamięci.

Minimalny przepływ:

1. zwaliduj first-day `month`;
2. wyznacz `quarter_first_month = rota.balance.quarter_start(month)` i 3 miesiące kwartału;
3. pobierz memberships Site i wybierz tylko enabled;
4. pobierz employees jednym existing read, zbuduj mapę i rozwiąż roster names;
5. dla roster IDs pobierz jednym batchem targets całego kwartału;
6. jednym batchem pobierz CURRENT assignments całego kwartału ze wszystkich Site;
7. jednym batchem pobierz current active overlapping availability całego kwartału;
8. jednym read pobierz CalendarDay dla całego kwartału;
9. pogrupuj w pamięci per employee;
10. zbuduj wiersze deterministycznie.

Brak roster members -> poprawny `CoordinatorAnalyticsView(..., rows=())`; nie jest błędem i nie wymaga fikcyjnego KPI.

T019 nie otwiera transakcji write i nie materializuje cache.

## 10. MONTH VS QUARTER AVAILABILITY

Każdy employee row jest oceniany niezależnie. Brak danych jednego pracownika nie blokuje poprawnych wierszy pozostałych.

### 10.1 Requested month target missing -> UNAVAILABLE

Jeżeli `target_hours` dla żądanego miesiąca nie istnieje:

- `status = UNAVAILABLE`;
- `month_data = None`;
- `quarter_months = ()`;
- brak wartości zastępczej `0`;
- deterministic warning z employee + brakującym miesiącem.

Nie próbować przedstawiać quarter balance jako liczby.

### 10.2 Requested month canonical computation fails -> UNAVAILABLE

Jeżeli `compute_month_balance()` dla żądanego miesiąca fail-closed przez `IncompleteAbsenceCalendarError`:

- `UNAVAILABLE`;
- `month_data = None`;
- `quarter_months = ()`;
- warning zawiera employee, miesiąc i dokładny canonical error message;
- brak fallbacku weekday-only.

Nie ustanawiać nowej zasady „każdy miesiąc zawsze wymaga pełnego CalendarDay”: zachować dokładną semantykę `rota.balance`/T018 — fail closed jest wymagany wtedy, kiedy canonical absence accounting rzeczywiście potrzebuje kompletnego kalendarza.

### 10.3 Requested month computes, but full quarter cannot -> MONTH_AVAILABLE_QUARTER_UNAVAILABLE

Najpierw policzyć żądany miesiąc samodzielnie kanonicznym `compute_month_balance(..., quarter_balance_before=0)` tylko po to, by uzyskać month-specific truth:

- target;
- effective target;
- planned;
- realized;
- month_balance.

W tym tymczasowym month-only wyniku NIE publikować jego sztucznego running balance od zera:

- `month_data.quarter_balance = None`;
- `month_data.unresolved_carryover = None`.

Następnie spróbować pełnego kwartału.

Jeżeli dowolny inny miesiąc kwartału ma brak `target_hours` albo full-quarter canonical computation fail-closed z powodu danych kalendarza:

- `status = MONTH_AVAILABLE_QUARTER_UNAVAILABLE`;
- zachować poprawne `month_data` żądanego miesiąca;
- `quarter_months = ()`;
- quarter/carryover w `month_data` pozostają `None`;
- warning wskazuje pierwszy blokujący miesiąc/dane deterministycznie.

Nie zerować carry-in i nie udawać pełnego salda kwartału.

### 10.4 Full quarter succeeds -> AVAILABLE

Jeżeli wszystkie 3 targety istnieją i `compute_quarter_balance()` kończy się poprawnie:

- `status = AVAILABLE`;
- `quarter_months` = dokładnie 3 `AnalyticsMonthData` w kolejności chronologicznej;
- każdy miesiąc bierze wszystkie istniejące pola swojego `WorkBalance`;
- `effective_target_hours` każdego miesiąca pochodzi z algebraicznej relacji sekcji 7;
- `month_data` jest dokładnie pozycją odpowiadającą requested month z `quarter_months`, z prawdziwym `quarter_balance` i `unresolved_carryover`.

Nie liczyć requested month drugi raz do finalnego output, jeśli full quarter już dał canonical row.

## 11. WARNING CONTRACT

Warnings są per employee row i są deterministyczne.

Frozen coordinator-facing technical texts T019:

Requested target missing:

`analytics unavailable for employee '<EMPLOYEE_ID>', month <YYYY-MM-01>: missing target_hours`

Quarter target missing:

`quarter analytics unavailable for employee '<EMPLOYEE_ID>': missing target_hours for <YYYY-MM-01>`

Requested month calendar/absence failure:

`analytics unavailable for employee '<EMPLOYEE_ID>', month <YYYY-MM-01>: <CANONICAL_ERROR>`

Quarter-only calendar/absence failure:

`quarter analytics unavailable for employee '<EMPLOYEE_ID>', month <YYYY-MM-01>: <CANONICAL_ERROR>`

`<CANONICAL_ERROR>` to `str(IncompleteAbsenceCalendarError)` bez przepisywania jego semantyki.

Przy wielu brakujących targetach quarter warning wskazuje pierwszy brakujący miesiąc chronologicznie. Nie emitować trzech duplikatów, jeżeli pierwszy gap już czyni cały quarter unavailable.

T019 nie emituje tekstu `nadgodziny`, `overtime`, `wynagrodzenie`, `payroll`, `ZUS` ani kwalifikacji prawnej salda.

## 12. OPEN_MONTH / QUARTER_BALANCE — NO SEMANTIC CHANGE

Nie zmieniać publicznego shape ani zachowania:

- `rota.application.open_month.open_month()`;
- `rota.application.balance_read.quarter_balance()`;
- `rota.application.assembler`.

T019 może współdzielić niższe canonical owners (`rota.balance`, persistence reads), ale nie przepakowuje istniejących API i nie wymusza ich migracji.

Nowe batch repo functions są additive. Existing tests dla single-employee reconstruction mają pozostać zielone bez mechanicznych zmian, o ile preimplementation audit nie wykaże konkretnej konieczności.

## 13. READ-ONLY / NO SECOND TRUTH

T019 MUST NOT:

- INSERT/UPDATE/DELETE żadnej tabeli;
- tworzyć tabeli analytics/work_balance cache;
- persistować `effective_target_hours`;
- zmieniać target_hours;
- zmieniać ScheduleVersion/current pointer/Assignment/Availability/CalendarDay;
- uruchamiać PLAN/REPLAN;
- tworzyć Deviation/DecisionRecord;
- zapisywać niewybrane dane dla T020/T021.

Dedicated test porównuje business-table snapshot przed i po wywołaniu analytics i wymaga bit-for-bit identycznych danych.

## 14. TASK_SCOPE

TASK_SCOPE:
- arch/T019_coordinator_analytics_architect_brief.md
- tasks/ROTA-T019/brief.md
- rota/application/analytics_read.py
- rota/persistence/work_balance_repository.py
- rota/persistence/availability_repository.py
- tests/test_t019.py

Żaden inny plik bez STOP + architect amendment.

## 15. EXPLICITLY OUT OF SCOPE

Bez osobnego amendmentu NIE zmieniać:

- arch/spec.md;
- arch/FROZEN.lock;
- rota/domain.py;
- rota/balance.py;
- rota/application/balance_read.py;
- rota/application/open_month.py;
- rota/application/assembler.py;
- rota/application/plan_ops.py;
- rota/persistence/schema / migrations;
- rota/persistence/schedule_repository.py;
- rota/persistence/employee_repository.py;
- rota/persistence/calendar_repository.py;
- rota/planning/*;
- solver/engine/validator;
- T020/T021 UI/export files.

Jeżeli implementacja wymaga zmiany któregokolwiek z tych plików, STOP przed edycją i wrócić do architekta z exact blockerem.

## 16. NEW_FILES

Dozwolone nowe pliki po contract stage:

- `tasks/ROTA-T019/brief.md`;
- `rota/application/analytics_read.py`;
- `tests/test_t019.py`.

Owner brief już istnieje na branchu i nie jest implementacyjnym new file.

Nie tworzyć `analytics_repository.py`, query bus, dashboard framework, report engine ani generic DTO package.

## 17. MINIMUM TEST MATRIX — tests/test_t019.py

Dedykowana macierz musi zawierać co najmniej:

1. complete one-employee month: id/name + wszystkie existing WorkBalance month fields + effective target;
2. complete quarter: dokładnie 3 chronologiczne month rows i poprawne running `quarter_balance`/`unresolved_carryover`;
3. planned i realized są osobne i sumują się tylko w istniejącym month_balance — bez double count;
4. CANCELLED z operational_code NN nie zwiększa planned/realized;
5. historyczna nie-current ScheduleVersion nie zwiększa godzin;
6. zmiana current pointer przez istniejący restore/select lifecycle zmienia analytics zgodnie z nowym current snapshot;
7. reopen/restart DB zwraca identyczny read model;
8. requested month missing target -> UNAVAILABLE, `month_data=None`, brak zera, exact warning;
9. inny quarter month missing target -> MONTH_AVAILABLE_QUARTER_UNAVAILABLE, requested month zachowany, quarter/carry `None`, exact warning;
10. requested month qualifying SICK_LEAVE/LEAVE_GRANTED + incomplete calendar -> UNAVAILABLE i canonical fail-closed message;
11. brak kalendarza w innym quarter month potrzebnym przez qualifying absence -> requested month available, quarter unavailable;
12. SICK_LEAVE obejmujące weekend/holiday -> effective target obniżony wyłącznie o canonical qualified workdays;
13. LEAVE_GRANTED obejmujące weekend/holiday -> ta sama WorkBalance/T018 workday accounting semantics;
14. `effective_target_hours == planned + realized - month_balance` dla każdego dostępnego month row; test nie rekonstruuje własnej alternate absence rule;
15. jeden employee ma CURRENT work na dwóch Site -> jedna globalna suma, bez duplikacji, `hours_scope=ALL_SITES`;
16. employee pracujący globalnie, ale bez enabled membership otwartego Site -> brak wiersza;
17. disabled membership otwartego Site -> brak wiersza;
18. enabled EXTERNAL_SUPPORT membership -> wiersz jest obecny; analytics nie wymaga ExternalSupportWindow do samego roster read;
19. T016 regression: active_from w przyszłości / active_to w przeszłości nie usuwa enabled roster member z analytics;
20. employee rows deterministycznie po employee_id, quarter months chronologicznie;
21. empty enabled roster -> poprawny view z `rows=()`;
22. read-only: business-table snapshots przed/po identyczne;
23. N+1 oracle: SELECT count/query pattern nie rośnie liniowo wraz z liczbą roster employees;
24. nie ma field/message nazywającego saldo „nadgodziny”/`overtime` ani żadnej kwoty wynagrodzenia/payroll;
25. existing `open_month()` behavior regression PASS na tych samych danych;
26. existing `quarter_balance()` behavior regression PASS, w tym empty+warning przy missing target;
27. zero planned/realized przy istniejącym target jest legalnym zerem i nie jest mylone z missing data;
28. brak qualifying SICK/LEAVE nie tworzy nowego blanket calendar requirement ponad istniejącą semantykę `rota.balance`.

## 18. LEGACY TEST ENUMERATION — PREIMPLEMENTATION REQUIRED

T019 dodaje API i batch reads, więc istniejące testy powinny co do zasady pozostać bez zmian. Nie zakładać tego bez audytu.

Przed CC Codex ma mechanicznie przeskanować existing `tests/*.py` i wskazać każdy plik wymagający edycji wyłącznie dlatego, że:

- additive batch helper zmienia prywatny/helper shape używany przez test monkeypatch/fake;
- test zamraża dokładną liczbę SQL queries w repozytorium, które teraz może współdzielić helper;
- test importuje `__all__`/public module list, jeśli taka istnieje;
- test ma expectation sprzeczne z nowym, ale już owner-frozen analytics read contract.

Required output:

- exact file list;
- exact tests/assertions;
- classification: mechanical compatibility vs semantic conflict.

Jeżeli choć jeden legacy test file wymaga edit, architect dopisuje go literalnie do TASK_SCOPE przed CC.

Nie autoryzować broad rewrites `test_balance.py`, T011-D, T016 ani T018 tylko dlatego, że są regression gates.

## 19. CODEX PREIMPLEMENTATION AUDIT

Codex audytuje exact contract SHA i odpowiada:

1. Czy T019 pozostaje read-only projection istniejącej prawdy, bez nowych KPI/payroll/UI/export?
2. Czy enabled SiteMembership jest jedynym roster filtrem i nie wraca EMP-02?
3. Czy godziny są jawnie ALL_SITES i current-version-only?
4. Czy `effective_target_hours = planned + realized - month_balance` ujawnia dokładnie canonical effective target bez duplikowania T018?
5. Czy month-vs-quarter status semantics rozróżniają missing month truth od missing quarter truth i nigdy nie używają zera jako missing?
6. Czy calendar failure zachowuje dokładne fail-closed `IncompleteAbsenceCalendarError` bez blanket nowej reguły kalendarza?
7. Czy batch architecture ma query count niezależny od roster size i nie potrzebuje nowego cache/table?
8. Czy application module nie wykonuje SQL bezpośrednio i nie importuje UI/persistence internals poza jawne repo APIs?
9. Czy istniejące `open_month()` i `quarter_balance()` public semantics pozostają bez zmian?
10. Czy domain/balance/assembler/schedule repo/planning pozostają poza scope?
11. Czy test matrix dowodzi CURRENT pointer, cross-Site, restart, read-only i T018 adjustment?
12. Jakie dokładnie legacy test files, jeśli jakiekolwiek, potrzebują mechanical scope amendment?
13. Czy którykolwiek clause wymaga nowej decyzji produktowej właściciela? Jeśli tak: FAIL z exact clause, bez zgadywania.

Required verdict:

`PASS — READY_FOR_IMPLEMENTATION`

Do tego PASS:

**CC MUST NOT START T019 IMPLEMENTATION.**

## 20. IMPLEMENTATION RULES FOR CC

Po preimplementation PASS:

- implementować wyłącznie literalny TASK_SCOPE po ewentualnym narrow amendment;
- żadnego SQL w `analytics_read.py`;
- żadnej zmiany `rota.balance` ani `domain.WorkBalance`;
- żadnego per-employee repository call w pętli dla target/availability/assignments;
- nie wywoływać `open_month()` per employee ani `quarter_balance()` per employee;
- zachować istniejące single-employee repository APIs;
- nie refaktoryzować unrelated code przy okazji;
- każdy scope blocker -> STOP do architekta.

## 21. FINAL IMPLEMENTATION GATE

Po implementacji Codex audytuje exact PRODUCT SHA i pełny `BASE_SHA -> HEAD` diff.

Wymagane:

- `tests/test_t019.py` full dedicated matrix PASS;
- wszystkie ewentualnie autoryzowane legacy adaptations PASS;
- full `tests/` PASS;
- `tests/test_balance.py` PASS;
- `tests/test_t011_d_quarter_balance.py` PASS;
- T016 EMP-02 retirement regressions PASS;
- T010 NN/CANCELLED regression PASS;
- T018 absence-workday accounting regressions PASS;
- ROTA-REG-001 PASS;
- Ruff PASS;
- `python guard.py check arch/spec.md` PASS;
- `git diff --check` PASS;
- `arch/spec.md` i `arch/FROZEN.lock` unchanged;
- backend.py literal TASK_SCOPE / NEW_FILES / DIFF_SCOPE PASS albo każdy mechanical `WYMAGA_DECYZJI` wraca do architekta z exact PRODUCT SHA;
- brak schema migration/new table/cache;
- brak nowych writes z analytics path;
- query-count oracle PASS.

Dopiero po Codex implementation PASS i finalnej akceptacji architekta:

`ARCHITECT FINAL GATE ACCEPTANCE — ROTA-T019: PASS — READY FOR MERGE`

# ROTA-T019 — coordinator analytics read model

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — ROUND 2 — NOT READY FOR CC
DATE: 2026-08-20
TASK_ID: ROTA-T019
BASE_SHA: 9618477f6014fad63699a154b04730e2b8ff1db2
BASE_BRANCH: main
TASK_BRANCH: task/ROTA-T019
OWNER_SOURCE: arch/T019_coordinator_analytics_architect_brief.md
DEPENDS_ON: T011-D + T014 + T016 + T017 + T018 merged on main
FOLLOWED_BY: T020 print/export; T021 UI

PREIMPLEMENTATION_ROUND_1: FAIL — T019-R1-1 EXTERNAL_SUPPORT / WINDOW-03; all other Round 1 sections CLOSED/PASS

## 1. CEL

Dostarczyć jeden read-only application-level odczyt dla przyszłego ekranu „Analityka”.

Dla wybranego `site_id` i miesiąca odczyt pokazuje wyłącznie **enabled LOCAL members** żądanego Site. Dla tych modelowanych pracowników LOCAL godziny i saldo są globalne — z CURRENT ScheduleVersion wszystkich modelowanych Site — zgodnie z istniejącą semantyką WorkBalance/EMP-03.

`EXTERNAL_SUPPORT` / X-Y nie tworzy wiersza WorkBalance analytics T019, zgodnie z frozen `WINDOW-03: Pilot does NOT model X/Y home-site HR, balances, or schedule.`

T019 nie tworzy nowego subsystemu analitycznego. Nie dodaje nowych wskaźników, payrollu, formalnej kwalifikacji nadgodzin, UI, wykresów ani eksportu.

## 2. BASELINE / ISTNIEJĄCY KANON

Na exact BASE_SHA `9618477f6014fad63699a154b04730e2b8ff1db2`:

- `WorkBalance` jest pochodnym read modelem: `target_hours`, `planned_hours`, `realized_hours`, `month_balance`, `unresolved_carryover`, `quarter_balance`;
- tylko `target_hours` jest persistowanym wejściem koordynatora;
- WorkBalance liczy wyłącznie Assignment z CURRENT ScheduleVersion każdego relewantnego modelowanego Site;
- Employee nie należy strukturalnie do jednego Site;
- `planned_hours` i `realized_hours` są rozłączne i pozostają osobnymi wartościami;
- CANCELLED/NN nie są pracą;
- `rota.balance.compute_month_balance()` i `compute_quarter_balance()` są kanonicznym ownerem rachunku godzin i salda;
- T018 `SICK_LEAVE` + `LEAVE_GRANTED` zmniejszają normę WorkBalance tylko za kwalifikujące się dni robocze przy użyciu istniejącego `CalendarDay`;
- brak wymaganej normy nie oznacza zera;
- `balance_read.quarter_balance()` jest fail-closed dla brakującego `target_hours` w którymkolwiek miesiącu kwartału;
- T016 wycofał EMP-02: `Employee.active_from/active_to` są legacy metadata i nie decydują o rosterze;
- WINDOW-03 wyłącza X/Y / EXTERNAL_SUPPORT z modelowania home-site HR, balances i schedule.

T019 musi zachować wszystkie te znaczenia bez redefinicji.

## 3. ARCHITECTURE DECISION — JEDEN NOWY APPLICATION READ

Dodać dokładnie jeden nowy moduł produkcyjny application-level:

`rota/application/analytics_read.py`

Nie rozszerzać `balance_read.py` do ogólnego agregatora. `balance_read.py` pozostaje małym, istniejącym ownerem jawnego odczytu jednego employee/quarter.

Nowy moduł:

- jest jedynym publicznym entry point T019;
- składa LOCAL roster + target + CURRENT assignments + current availability + CalendarDay;
- nie wykonuje SQL bezpośrednio;
- nie importuje solvera ani PlanningEngine;
- deleguje rachunek wyłącznie do istniejących pure funkcji `rota.balance`;
- nie zapisuje niczego;
- zwraca jeden deterministyczny read model całego eligible LOCAL rosteru.

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

Pole jest obowiązkowe na top-level view i jest jawnym kontraktem dla T021: dla wierszy LOCAL liczby godzin nie są site-local.

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

## 5. ROSTER FILTER — T016 + WINDOW-03 MUST NOT REGRESS

Wiersz WorkBalance analytics T019 powstaje wyłącznie, gdy dla żądanego Site istnieje:

`SiteMembership.site_id == requested site_id`

AND

`SiteMembership.enabled == True`

AND

`SiteMembership.membership_kind == LOCAL`.

Frozen consequences:

- enabled LOCAL -> może dać jeden wiersz analytics;
- disabled LOCAL -> brak wiersza;
- EXTERNAL_SUPPORT -> brak wiersza niezależnie od `enabled`;
- ExternalSupportWindow nie zmienia tej reguły; okno jest eligibility do pracy X/Y, nie źródłem WorkBalance analytics;
- lokalne Assignment wykonane przez X/Y nie ustanawiają kompletnego `ALL_SITES` WorkBalance dla X/Y i nie tworzą wiersza;
- Employee globalnie istniejący, ale bez enabled LOCAL membership na żądanym Site, nie daje wiersza nawet jeśli ma godziny gdzie indziej;
- jeżeli ten sam Employee ma enabled LOCAL na żądanym Site i EXTERNAL_SUPPORT na innym Site, ma dokładnie jeden wiersz z powodu LOCAL membership na żądanym Site; EXTERNAL membership nie dodaje drugiego wiersza i nie jest osobnym uprawnieniem do analytics.

T019 NIE używa `Employee.active_from/active_to` do filtrowania. T016 wycofał EMP-02 i analytics nie może go bocznymi drzwiami przywrócić.

Kolejność `rows`: rosnąco po `employee_id`. Nie polegać na przypadkowej kolejności SQL.

## 6. HOURS SCOPE — GLOBAL ACROSS MODELED SITES FOR LOCAL ROWS

Dla employee IDs wybranych przez sekcję 5 Assignment do WorkBalance pobierać jednym istniejącym batchem:

`get_current_assignments_for_employees(conn, employee_ids, quarter_start_dt, quarter_end_dt)`

bez `exclude_site_id` i bez site-local filtra.

To zachowuje:

- CURRENT-version-only;
- cross-Site sumę dla modelowanego Employee LOCAL;
- CANCELLED exclusion istniejącego repo;
- brak historycznego double count.

T019 nie może rekonstruować site_id z Assignment i odejmować pracy innych Site.

`hours_scope == ALL_SITES` oznacza wszystkie Site modelowane przez Rotę dla pracownika, który wszedł do T019 przez enabled LOCAL membership. Nie wolno używać tego pola do twierdzenia o kompletności home-site danych X/Y; X/Y nie ma wiersza T019.

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

T019 nie może implementować całej LOCAL obsady przez pętlę `open_month(employee)` / `quarter_balance(employee)` / `reconstruct_month_balance(employee)`.

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

- jeden SELECT dla całego LOCAL rosteru/kwartału;
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

- jeden SELECT dla całego LOCAL rosteru/kwartału;
- dokładnie obecna semantyka current chain-end per `availability_id`;
- active only;
- inclusive date overlap jak `list_active_overlapping`;
- tylko wskazani employees;
- deterministyczne sortowanie co najmniej `(employee_id, availability_id)`;
- nie zmieniać append-only availability history.

Można bezpiecznie współdzielić prywatny row mapper/helper, ale nie przepisywać repozytorium.

### 8.4 N+1 oracle

`tests/test_t019.py` ma użyć `sqlite3.Connection.set_trace_callback` albo równoważnego mechanicznego licznika SELECT i dowieść, że zwiększenie LOCAL rosteru z 1 do wielu employees nie zwiększa liczby SELECT proporcjonalnie do liczby employees.

Nie zamrażać kruchej dokładnej liczby wszystkich SELECT, jeżeli nie jest to potrzebne; zamrozić brak zależności liniowej od rozmiaru rosteru.

## 9. ONE-SNAPSHOT COMPUTATION

`analytics_for_site_month()` pobiera potrzebne dane przed złożeniem wierszy i następnie liczy w pamięci.

Minimalny przepływ:

1. zwaliduj first-day `month`;
2. wyznacz `quarter_first_month = rota.balance.quarter_start(month)` i 3 miesiące kwartału;
3. pobierz memberships Site i wybierz wyłącznie `enabled=True AND membership_kind=LOCAL`;
4. pobierz employees jednym existing read, zbuduj mapę i rozwiąż roster names;
5. dla LOCAL roster IDs pobierz jednym batchem targets całego kwartału;
6. jednym batchem pobierz CURRENT assignments całego kwartału ze wszystkich modelowanych Site;
7. jednym batchem pobierz current active overlapping availability całego kwartału;
8. jednym read pobierz CalendarDay dla całego kwartału;
9. pogrupuj w pamięci per employee;
10. zbuduj wiersze deterministycznie.

Brak enabled LOCAL roster members -> poprawny `CoordinatorAnalyticsView(..., rows=())`; nie jest błędem i nie wymaga fikcyjnego KPI.

T019 nie otwiera transakcji write i nie materializuje cache.

## 10. MONTH VS QUARTER AVAILABILITY

Każdy LOCAL employee row jest oceniany niezależnie. Brak danych jednego pracownika nie blokuje poprawnych wierszy pozostałych.

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

EXTERNAL_SUPPORT nie dostaje warningu „analytics unavailable”; nie ma wiersza T019, więc brak WorkBalance analytics X/Y jest filtrem scope, nie stanem `UNAVAILABLE`.

## 12. OPEN_MONTH / QUARTER_BALANCE — NO SEMANTIC CHANGE

Nie zmieniać publicznego shape ani zachowania:

- `rota.application.open_month.open_month()`;
- `rota.application.balance_read.quarter_balance()`;
- `rota.application.assembler`.

T019 może współdzielić niższe canonical owners (`rota.balance`, persistence reads), ale nie przepakowuje istniejących API i nie wymusza ich migracji.

Nowe batch repo functions są additive. Existing tests dla single-employee reconstruction pozostają zielone bez mechanicznych zmian; Round 1 legacy enumeration wykazała ZERO plików wymagających adaptacji.

## 13. READ-ONLY / NO SECOND TRUTH

T019 MUST NOT:

- INSERT/UPDATE/DELETE żadnej tabeli;
- tworzyć tabeli analytics/work_balance cache;
- persistować `effective_target_hours`;
- zmieniać target_hours;
- zmieniać ScheduleVersion/current pointer/Assignment/Availability/CalendarDay;
- uruchamiać PLAN/REPLAN;
- tworzyć Deviation/DecisionRecord;
- tworzyć WorkBalance analytics dla EXTERNAL_SUPPORT/X-Y;
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

Round 1 audit artifact `tasks/ROTA-T019/round_01/tests/tests_r1.txt` jest evidence sprzed implementation stage; nie otwiera implementation TASK_SCOPE i nie jest plikiem do edycji przez CC.

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

- `rota/application/analytics_read.py`;
- `tests/test_t019.py`.

Owner brief i task brief już istnieją na branchu. Nie tworzyć `analytics_repository.py`, query bus, dashboard framework, report engine ani generic DTO package.

## 17. MINIMUM TEST MATRIX — tests/test_t019.py

Dedykowana macierz musi zawierać co najmniej:

1. complete one-employee enabled LOCAL month: id/name + wszystkie existing WorkBalance month fields + effective target;
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
15. jeden enabled LOCAL employee ma CURRENT work na dwóch modelowanych Site -> jedna globalna suma, bez duplikacji, `hours_scope=ALL_SITES`;
16. employee pracujący globalnie, ale bez enabled LOCAL membership otwartego Site -> brak wiersza;
17. disabled LOCAL membership otwartego Site -> brak wiersza;
18. enabled EXTERNAL_SUPPORT membership -> **brak wiersza WorkBalance analytics**, zarówno bez ExternalSupportWindow, jak i z oknem; lokalne Assignment X/Y nie zmieniają tej reguły. Jeżeli ten sam Employee ma enabled LOCAL membership na żądanym Site, pojawia się dokładnie jeden LOCAL row — z powodu LOCAL membership, nie EXTERNAL;
19. T016 regression: active_from w przyszłości / active_to w przeszłości nie usuwa enabled LOCAL roster member z analytics;
20. employee rows deterministycznie po employee_id, quarter months chronologicznie;
21. empty enabled LOCAL roster -> poprawny view z `rows=()`;
22. read-only: business-table snapshots przed/po identyczne;
23. N+1 oracle: SELECT count/query pattern nie rośnie liniowo wraz z liczbą LOCAL roster employees;
24. nie ma field/message nazywającego saldo „nadgodziny”/`overtime` ani żadnej kwoty wynagrodzenia/payroll;
25. existing `open_month()` behavior regression PASS na tych samych danych;
26. existing `quarter_balance()` behavior regression PASS, w tym empty+warning przy missing target;
27. zero planned/realized przy istniejącym target jest legalnym zerem i nie jest mylone z missing data;
28. brak qualifying SICK/LEAVE nie tworzy nowego blanket calendar requirement ponad istniejącą semantykę `rota.balance`.

Pozostałych 27 oracles Round 1 nie otwiera się przez T019-R1-1.

## 18. LEGACY TEST ENUMERATION — ROUND 1 CLOSED

Round 1 wykonał obowiązkową mechaniczną enumerację existing `tests/*.py` dla:

- availability single/batch helper compatibility;
- target read compatibility;
- `get_current_assignments_for_employees` monkeypatch/imports;
- exact SQL query count expectations;
- `__all__` / public module-list expectations.

Wynik frozen dla contract stage:

`LEGACY_TEST_ADAPTATIONS: NONE`

Żaden istniejący test file nie jest dopisywany do TASK_SCOPE. Jeśli implementer zdecyduje się zmienić istniejącą publiczną sygnaturę/semantykę zamiast dodać additive batch helper, jest to scope drift i musi STOP — nie jest to powód do mechanicznej adaptacji legacy testu.

## 19. ROUND 1 AMENDMENT — T019-R1-1

Audyt exact contract SHA `c0f5d2759a9ca232a6263a0c1ffa7ee478481db2` wykazał dokładnie jeden blocker:

`T019-R1-1 — EXTERNAL_SUPPORT NIE MOŻE DOSTAĆ WORKBALANCE ANALYTICS`.

Zamknięcie jest wyłącznie kontraktowe:

- sekcja 5 została zawężona do enabled LOCAL;
- EXTERNAL_SUPPORT/X-Y nie tworzy wiersza niezależnie od enabled/window/Assignment;
- `ALL_SITES` dotyczy tylko modelowanego Employee, który wszedł do widoku przez enabled LOCAL membership;
- owner source został znormalizowany do WINDOW-03;
- test 18 został odwrócony na obowiązkowy brak wiersza X/Y;
- pozostałe 27 testów i wszystkie inne Round 1 SECTION_CHECK pozostają CLOSED/PASS;
- brak legacy adaptations pozostaje CLOSED/PASS;
- nie ma nowej decyzji produktowej.

## 20. CODEX PREIMPLEMENTATION AUDIT — ROUND 2 NARROW ONLY

Round 2 audytuje exact amendment SHA i sprawdza wyłącznie T019-R1-1:

1. Czy roster WorkBalance T019 jest dokładnie `enabled=True AND membership_kind=LOCAL` na żądanym Site?
2. Czy EXTERNAL_SUPPORT/X-Y nie tworzy wiersza niezależnie od ExternalSupportWindow i lokalnych Assignment?
3. Czy przypadek mixed membership jest jednoznaczny: LOCAL na żądanym Site może utworzyć jeden row; EXTERNAL gdzie indziej nie tworzy drugiego row ani osobnego uprawnienia?
4. Czy `hours_scope=ALL_SITES` nie jest już używane jako twierdzenie o kompletności home-site X/Y?
5. Czy test 18 dowodzi nowej frozen reguły bez zmiany pozostałych 27 oracles?
6. Czy owner source jest spójny z WINDOW-03?
7. Czy amendment nie zmienił DTO, effective target, missing-data semantics, batch architecture, TASK_SCOPE implementacji ani read-only granic?
8. Czy między `8e34530477c78d4b53694e7b86a4dcbcbbca0a3e` a amendment HEAD nie ma kodu ani testów implementacyjnych?

Wymagany werdykt:

`PASS — READY_FOR_IMPLEMENTATION`

Pozostałych Round 1 SECTION_CHECK nie otwierać ponownie bez nowej, konkretnej sprzeczności wprowadzonej przez amendment.

Do tego PASS:

**CC MUST NOT START T019 IMPLEMENTATION.**

## 21. IMPLEMENTATION RULES FOR CC

Po preimplementation PASS:

- implementować wyłącznie literalny TASK_SCOPE;
- analytics roster filter = enabled LOCAL only;
- EXTERNAL_SUPPORT nie tworzy row ani `UNAVAILABLE` warning;
- żadnego SQL w `analytics_read.py`;
- żadnej zmiany `rota.balance` ani `domain.WorkBalance`;
- żadnego per-employee repository call w pętli dla target/availability/assignments;
- nie wywoływać `open_month()` per employee ani `quarter_balance()` per employee;
- zachować istniejące single-employee repository APIs;
- nie refaktoryzować unrelated code przy okazji;
- każdy scope blocker -> STOP do architekta.

## 22. FINAL IMPLEMENTATION GATE

Po implementacji Codex audytuje exact PRODUCT SHA i pełny `BASE_SHA -> HEAD` diff.

Wymagane:

- `tests/test_t019.py` full dedicated matrix PASS;
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
- query-count oracle PASS;
- EXTERNAL_SUPPORT/X-Y exclusion oracle PASS.

Dopiero po Codex implementation PASS i finalnej akceptacji architekta:

`ARCHITECT FINAL GATE ACCEPTANCE — ROTA-T019: PASS — READY FOR MERGE`

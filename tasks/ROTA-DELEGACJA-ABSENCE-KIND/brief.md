# ROTA-DELEGACJA-ABSENCE-KIND — delegacja jako blokada dostępności i godziny zaliczane do planu

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS

BASE_MAIN_SHA: `91907bc39c0b6f8d83b5e05b724e8eac36e24067`
SOURCE_REQUEST: `BOARD.md` / `ROTA-DELEGACJA-ABSENCE-KIND`
CORRECTION_R1_SOURCE: audit `641727d552d22ef5f8a73b80f618fb2cf89648c6`
OWNER_RULING: nowy rodzaj DELEGACJA dla obu regime'ów; blokuje automatyczne przydzielenie pracy jak pełnodniowa nieobecność, ale jej godziny liczą się od razu do `WorkBalance.planned_hours`, bez przejścia do `realized_hours` opartego na zegarze; każdy Site ma własny default godzin, a konkretna delegacja może ten default nadpisać.

## 1. Cel

Dodać jeden nowy `AvailabilityKind.DELEGACJA`, bez tworzenia równoległego systemu pracy delegowanej.

DELEGACJA jest jednocześnie:
1. whole-day informacją o niedostępności do zwykłego automatycznego Assignmentu;
2. faktem godzinowym do rozliczenia czasu pracy;
3. faktem prezentacyjnym na grafiku/PDF.

Nie jest `Assignment`, `ShiftDemand`, `StandardShift`, external support ani S1.

## 2. Zakres reżimowy

DELEGACJA obowiązuje w obu `SitePlanningRegime`:
- ORDINARY;
- OCHRONA.

Nie dodawać osobnej semantyki per regime poza prezentacją PDF, jeśli istniejące layouty wymagają różnych rendererów.

## 3. Model domenowy

### 3.1 Nowy kind

Do `AvailabilityKind` dochodzi:

`DELEGACJA = "DELEGACJA"`

Pozostaje whole-day kind. `start_time/end_time` pozostają `None`, tak jak dla innych pełnodniowych AvailabilityKinds.

### 3.2 Godziny konkretnej delegacji

`AvailabilityRecord` dostaje jedno opcjonalne pole:

`delegation_hours: Optional[int]`

Invariant:
- dla `DELEGACJA` wartość MUSI być dodatnią liczbą całkowitych godzin;
- dla wszystkich pozostałych kinds MUSI być `None`;
- wartość zapisana na rekordzie jest historycznym snapshotem konkretnej delegacji i nie zmienia się po późniejszej zmianie Site defaultu.

Nie wyliczać godzin delegacji z długości zmiany, target_hours ani grafiku.

## 4. Site default godzin delegacji

Każdy Site ma własne bieżące ustawienie `delegation_default_hours`.

Jedyny dozwolony model:
- `Site.delegation_default_hours` w `rota/domain.py`;
- kolumna `sites.delegation_default_hours` dodana przez następną migrację w
  `rota/persistence/db.py` i odczytywana/zapisywana przez
  `rota/persistence/site_repository.py`;
- zapis przez istniejącą operację `rota/application/durable_inputs.py::update_site`;
- integer > 0;
- istniejące Site po migracji mogą mieć `NULL` wyłącznie jako stan legacy wymagający konfiguracji przed utworzeniem pierwszej DELEGACJI;
- NIE wprowadzać globalnego ukrytego defaultu 7h/8h, którego OWNER nie ustalił.

UI podczas tworzenia DELEGACJI:
- wstępnie podpowiada `delegation_default_hours` bieżącego Site;
- koordynator może zmienić wartość dla konkretnego rekordu;
- zapisana wartość trafia do `AvailabilityRecord.delegation_hours`.

Późniejsza zmiana defaultu nie przepisuje wcześniejszych rekordów.

API ustawienia ma być jednym wąskim zasobem
`GET/PUT /workspace/sites/{site_id}/delegation-default-hours` dodanym do
istniejącego `api/routers/site_profile.py`. Nie rozszerzać pełnego zapisu
katalogu zmian i nie tworzyć nowego routera. UI ma być małą sekcją
`frontend/src/screens/SiteDelegationSettings.tsx`, osadzoną w istniejącym
`frontend/src/screens/ControlPanel.tsx`; klient pozostaje w
`frontend/src/api/client.ts`. Zmiana defaultu jest tylko prefillem dla nowych
lub edytowanych delegacji: nie przepisuje snapshotów, nie unieważnia istniejącego
grafiku i nie uruchamia REPLAN.

## 5. Blokada automatycznego planowania

DELEGACJA blokuje automatyczne przypisanie pracy na każdy dzień objęty rekordem dokładnie jak istniejące whole-day kinds, które dziś blokują Assignment automatyczny.

Wymagania:
- wspólny istniejący eligibility/validator path;
- brak lokalnej kopii overlap logic;
- brak osobnego solver passu;
- brak szczególnego wyjątku dla OCHRONA/ORDINARY.

Nie zmieniać ogólnej semantyki manual correction. W
`rota/planning/validator_checks_availability.py::_check_leave_and_unavailable`
DELEGACJA wchodzi do istniejącej listy całodniowych niedostępności i zgłasza
`ViolationDetail` o nowym kodzie `DELEGACJA-01`. Automatyczny eligibility nadal
odrzuca taki przydział, natomiast `rota/application/manual_edit.py` zachowuje
obecny przepływ: ręczna korekta nie jest blokowana, a wynik walidatora jest
materializowany jako `Deviation`. `rota/application/deviation_mapping.py`
mapuje `DELEGACJA-01` na istniejącą kategorię
`DeviationCategory.LEAVE_OR_TIME_OFF`, a `api/routers/schedule.py` mapuje kod na
polską etykietę `delegacja`. Nie dodawać nowego cyklu życia, nowego typu
override ani drugiego validatora.

## 6. Godziny delegacji NIE są excused absence

DELEGACJA nie należy do `EXCUSED_ABSENCE_KINDS`.

W szczególności:
- nie zmniejsza targetu tak jak `SICK_LEAVE`/`LEAVE_GRANTED`;
- nie korzysta z `EXCUSED_ABSENCE_HOURS_PER_DAY`;
- nie dziedziczy PRE_PLAN_LEAVE/POST_PLAN_REFERENCE semantyki nieobecności usprawiedliwionej.

Jej `delegation_hours` są godzinami realnie zaliczanymi do pracy.

## 7. Jeden owner rozliczania godzin delegacji

Należy dodać jeden czysty helper
`rota/planning/absence.py::delegation_hours_in_range`, używany przez wszystkie
miejsca sumujące czas pracy.

Minimalny kontrakt:
- bierze bieżące, aktywne rekordy DELEGACJA oraz `employee_id` i zamknięty
  zakres dat;
- dla każdego dnia rekordu dodaje zapisane `delegation_hours`;
- clipping do żądanego zakresu dat;
- nie zgaduje godzin przy brakującej wartości — fail closed;
- nie miesza się z excused-absence precedence;
- nie implementuje żadnej specjalnej semantyki nakładających się delegacji.

`rota/planning/absence.py` jest jedynym ownerem arytmetyki godzin DELEGACJI.
`rota/balance.py` i `rota/application/schedule_export.py` mogą wywołać ten
helper, ale nie mogą powtarzać jego arytmetyki. Warstwa persistence tylko ładuje
rekordy i przekazuje je do obliczenia.

Zakazane:
- osobne obliczenie w PDF i osobne w balance;
- odtwarzanie godzin z Site defaultu podczas historycznego odczytu;
- traktowanie DELEGACJI jako sztucznego Assignmentu tylko po to, by podbić sumę godzin.

## 8. WorkBalance / kwartalne rozliczenie

`rota/balance.py` ma doliczać godziny DELEGACJI do istniejącego
`WorkBalance.planned_hours` pracownika w odpowiednim zakresie.

Semantyka:

`planned_hours = planned_assignment_hours + delegation_hours`

z zachowaniem wszystkich istniejących zasad dla Assignmentów i innych absences.

`realized_hours` nadal zawiera wyłącznie zrealizowane Assignmenty. DELEGACJA nie
odejmuje expected/target hours; od chwili zapisu zwiększa `planned_hours`, sumę
miesięczną oraz narastające saldo kwartału. Nie istnieje automatyczne przejście
z `planned_hours` do `realized_hours` oparte na zegarze lub dacie.

Rzeczywiste call sites są zamknięte następująco:
- `rota/persistence/work_balance_repository.py::reconstruct_month_balance` i
  `reconstruct_quarter_balance` ładują bieżące aktywne rekordy DELEGACJA i
  przekazują je do `rota.balance.compute_month_balance` /
  `compute_quarter_balance`;
- batch read dla analityki w tym samym repozytorium ładuje te rekordy jednym
  zapytaniem dla pracowników i zakresu;
- `rota/application/analytics_read.py::_row_for_employee` oraz
  `_quarter_row` przekazują batch do tych samych funkcji `rota.balance`, bez
  własnego sumowania;
- `rota/application/assembler.py` i `rota/application/balance_read.py` pozostają
  bez zmian, ponieważ już korzystają z rekonstrukcji w
  `work_balance_repository.py`.

Projekcja DELEGACJI jest wykonywana raz przez
`delegation_hours_in_range` dla danego obliczanego miesiąca. Repozytorium,
analityka i eksport nie mogą mieć drugiej definicji tej sumy.

## 9. Solver / target

Automatyczny solver:
- nie może przydzielić Assignmentu w dniu DELEGACJI;
- DELEGACJA nie jest mechanizmem obniżania target_hours;
- konsumuje zmieniony `WorkBalance.planned_hours` z istniejącego assemblera;
  `rota/planning/solver.py` nie otrzymuje osobnego przeliczenia delegacji i nie
  należy go zmieniać w tym Tasku.

Nie dodawać bezpośredniego call site DELEGACJI w solverze; jedynym wejściem
godzinowym solvera pozostaje zrekonstruowany `WorkBalance`.

## 10. PDF / prezentacja

DELEGACJA ma być widoczna na wydruku dla obu regime'ów i jej godziny wchodzą do sumy `Godz.`.

Nie używać symbolu `D`, ponieważ w OCHRONA `D` jest już istniejącym kodem zmiany dziennej i byłby semantycznie dwuznaczny.

Zamrożone oznaczenie dla DELEGACJI: `DEL`.

ORDINARY:
- dzień delegacji pokazuje `DEL` w komórce;
- godziny z delegacji są doliczone do miesięcznej sumy `Godz.`;
- nie prezentować `DEL` jako zwykłego przedziału Assignmentu.

OCHRONA:
- `DEL` nie może zostać pomylone z D/N;
- istniejący układ PLAN/WYK i legenda mogą dostać jeden nowy jawny symbol, bez reinterpretacji D/N;
- godziny delegacji wchodzą do właściwej miesięcznej sumy godzin.

Jeżeli obecny renderer ma rozdzielone źródła nieobecności i realnych godzin, implementacja ma złożyć wynik na poziomie modelu eksportu, nie przez sztuczny Assignment.

## 11. UI/API

Istniejący blok Availability zostaje mechanicznie wydzielony z
`frontend/src/screens/EmployeeDetail.tsx` do jednego pliku
`frontend/src/screens/EmployeeAvailability.tsx`. Ten plik zawiera przeniesione
bez zmiany zachowania `AbsenceLog`, `AbsenceEditRow`, `AddAbsenceForm` oraz nową
obsługę DELEGACJI. `EmployeeDetail.tsx` jedynie importuje i osadza komponent.
Nie dzielić przy okazji pozostałej części ekranu.

W formularzu nieobecności:
- dostępny nowy kind `DELEGACJA`;
- po wyborze DELEGACJA pokazuje się pole `Godziny delegacji`;
- pole jest wstępnie wypełnione Site defaultem;
- koordynator może je nadpisać przed zapisem;
- dla innych kinds pole jest ukryte/nieużywane.

W ustawieniach Site trzeba umożliwić ustawienie/zmianę `delegation_default_hours`.

Nie tworzyć osobnego ekranu delegacji ani osobnego CRUD subsystemu.

## 12. Persistence / migracja

Wymagane:
- enum/value persistence dla `AvailabilityKind.DELEGACJA` zgodnie z bieżącym schematem DB;
- persistence `AvailabilityRecord.delegation_hours`;
- persistence `Site.delegation_default_hours` lub równoważnego pola na istniejącym ownerze Site;
- migracja `23` w `rota/persistence/db.py`: nullable
  `availability_versions.delegation_hours` i nullable
  `sites.delegation_default_hours`, bez przepisywania historycznych
  AvailabilityRecordów; `LATEST_SCHEMA_VERSION` i `MIGRATIONS` zostają
  podniesione wyłącznie o tę jedną migrację.

Dla legacy Site brak defaultu ma być jawny (`NULL`) i ma blokować stworzenie DELEGACJI przez UI/API do czasu konfiguracji; nie zgadywać 7/8h.

## 13. Relacja do multi-Site

DELEGACJA pozostaje istniejącym employee-level `AvailabilityRecord`, tak jak inne kinds. Ten Task NIE projektuje nowej site-scoped availability ani Assignmentu na „obiekcie docelowym delegacji”.

Site służy wyłącznie jako źródło defaultu przy tworzeniu rekordu. Zapisane `delegation_hours` są samowystarczalnym historycznym faktem do późniejszego rozliczenia.

## 14. Acceptance

DEL-01 — można utworzyć DELEGACJĘ dla pracownika w OCHRONA i ORDINARY.

DEL-02 — aktywna DELEGACJA whole-day blokuje automatyczne Assignmenty na objętym dniu tym samym gate'em co inne whole-day niedostępności.

DEL-03 — Site default jest podpowiedzią; pojedynczy rekord może zapisać inną dodatnią liczbę godzin.

DEL-04 — późniejsza zmiana Site defaultu nie zmienia `delegation_hours` starego rekordu.

DEL-05 — rekord DELEGACJA bez `delegation_hours` failuje kontrolowanie; inne kinds z nie-None `delegation_hours` również failują.

DEL-06 — DELEGACJA nie należy do excused absence i nie obniża targetu/expected hours.

DEL-07 — miesięczny i kwartalny WorkBalance doliczają delegację do
`planned_hours` dokładnie raz i nie zmieniają `realized_hours`.

DEL-08 — PDF ORDINARY pokazuje `DEL` i dolicza godziny do `Godz.`.

DEL-09 — PDF OCHRONA pokazuje jednoznaczne `DEL`, bez kolizji z D/N, i dolicza godziny do sumy.

DEL-10 — wielodniowa DELEGACJA rozlicza zapisane godziny za każdy objęty dzień
dokładnie raz; test nie konstruuje nakładających się delegacji.

DEL-11 — anulowany/superseded record nie wnosi blokady ani godzin zgodnie z istniejącym Availability lifecycle.

DEL-12 — LEAVE_GRANTED, SICK_LEAVE, DAY_SHIFT_OFF, UNAVAILABLE_24H i UNAVAILABLE_TIME_WINDOW zachowują dotychczasową semantykę.

DEL-13 — brak configured Site defaultu blokuje utworzenie DELEGACJI przez normalny UI/API z czytelnym komunikatem, ale nie wpływa na PLAN bez DELEGACJI.

## 15. Minimalne testy

Backend/domain:
- invariants nowego kind i delegation_hours;
- Site default persistence/readback;
- create availability z defaultem i z override;
- automatic eligibility blocker dla obu regime'ów;
- delegation-hours projection: single day, multi-day, clipping, inactive/superseded;
- bilans miesiąca/kwartału dodaje godziny do `planned_hours` dokładnie raz i nie
  zmienia `realized_hours`;
- excused absence target reduction unchanged.

Export:
- ORDINARY `DEL` + suma;
- OCHRONA `DEL` bez kolizji D/N + suma;
- brak regresji Urlop/L4/D/N.

Frontend/API:
- kind DELEGACJA widoczny;
- pole godzin tylko dla DELEGACJA;
- prefill Site default + override;
- brak defaultu = kontrolowany blocker.

## 16. WHERE_MAP

WHERE_MAP: REQUIRED
- `rota/domain.py` :: `AvailabilityKind`, `AvailabilityRecord`, `Site`.
- `rota/persistence/db.py` :: migracja 23, `LATEST_SCHEMA_VERSION`, `MIGRATIONS`.
- `rota/persistence/availability_repository.py` :: round-trip rekordu.
- `rota/persistence/site_repository.py` :: Site default persistence.
- `rota/application/durable_inputs.py` :: write path Availability i
  `update_site` dla Site defaultu.
- `rota/planning/eligibility.py` :: automatic whole-day blocker.
- `rota/planning/validator_checks_availability.py` ::
  `_check_leave_and_unavailable`, `DELEGACJA-01`.
- `rota/application/deviation_mapping.py` :: mapowanie `DELEGACJA-01` na
  istniejącą kategorię odchylenia.
- `api/routers/schedule.py` :: polska etykieta `delegacja`.
- `rota/planning/absence.py` :: canonical delegation-hours projection, osobno od excused absence.
- `rota/balance.py` :: `planned_hours` miesiąca i narastający bilans kwartału.
- `rota/persistence/work_balance_repository.py` :: month/quarter reconstruction
  i batch Availability dla analytics.
- `rota/application/analytics_read.py` :: bezpośrednie call sites
  `compute_month_balance` / `compute_quarter_balance`.
- `rota/application/schedule_export.py` :: export model + monthly sums.
- `api/routers/durable_inputs.py` :: istniejące create/update Availability.
- `api/routers/site_profile.py` :: wąski GET/PUT Site delegation default.
- `frontend/src/screens/EmployeeDetail.tsx` :: tylko zastąpienie inline bloku
  importowanym komponentem Availability.
- `frontend/src/screens/EmployeeAvailability.tsx` :: przeniesiony form/log i
  pole godzin DELEGACJI.
- `frontend/src/screens/ControlPanel.tsx` :: osadzenie ustawienia Site.
- `frontend/src/screens/SiteDelegationSettings.tsx` :: mała sekcja defaultu.
- `frontend/src/api/client.ts`.

## 17. TASK_SCOPE

TASK_SCOPE:
- `tasks/ROTA-DELEGACJA-ABSENCE-KIND/**`
- `rota/domain.py`
- `rota/persistence/db.py`
- `rota/persistence/availability_repository.py`
- `rota/persistence/site_repository.py`
- `rota/persistence/work_balance_repository.py`
- `rota/application/durable_inputs.py`
- `rota/application/analytics_read.py`
- `rota/application/deviation_mapping.py`
- `rota/planning/eligibility.py`
- `rota/planning/validator_checks_availability.py`
- `rota/planning/absence.py`
- `rota/balance.py`
- `rota/application/schedule_export.py`
- `api/routers/durable_inputs.py`
- `api/routers/site_profile.py`
- `api/routers/schedule.py`
- `frontend/src/api/client.ts`
- `frontend/src/screens/ControlPanel.tsx`
- `frontend/src/screens/SiteDelegationSettings.tsx` (nowy)
- `frontend/src/screens/EmployeeDetail.tsx`
- `frontend/src/screens/EmployeeAvailability.tsx` (nowy)
- `tests/test_delegation_absence.py` (nowy)
- `tests/test_balance.py`
- `tests/test_eligibility_matrix.py`
- `tests/test_local_store_schema_migration.py`
- `tests/test_site_profile_persistence.py`
- `tests/test_t037_manual_edit_api.py`
- `tests/test_t047_print_export.py`
- `frontend/e2e/delegation-absence.spec.ts` (nowy)

Każda nowa produkcyjna ścieżka poza tym zakresem wymaga STOP + pytanie do architekta.

## 18. Preimplementation audit Codexa

Codex ma przed implementacją sfalsyfikować:
1. czy `AvailabilityRecord` jest właściwym jedynym ownerem faktu DELEGACJA;
2. czy `delegation_hours` jako snapshot eliminuje potrzebę historycznego lookupu Site defaultu;
3. dokładne miejsca wspólnego whole-day blocker dla solvera i validatora;
4. czy `work_balance_repository.py`, bezpośrednie call sites w
   `analytics_read.py` i eksport konsumują `delegation_hours_in_range` bez
   drugiej arytmetyki; solver korzysta wyłącznie z gotowego WorkBalance;
5. czy `DEL` jest jednoznaczne w obu rendererach i nie koliduje z D/N/S1/Urlop/L4;
6. ścieżkę ustawienia Site: `Site` -> `site_repository.py` ->
   `durable_inputs.update_site` -> `site_profile.py` ->
   `SiteDelegationSettings.tsx`;
7. czy literalny TASK_SCOPE obejmuje migrację 23,
   `validator_checks_availability.py`,
   mapowanie odchylenia i oba małe komponenty UI bez niejawnego rozszerzania;
8. czy wydzielenie `EmployeeAvailability.tsx` jest mechanicznym przeniesieniem
   istniejącego bloku, bez refaktoru pozostałej części `EmployeeDetail.tsx`.

IMPLEMENTATION HOLD do PASS preimplementation na dokładnym SHA tego briefu.

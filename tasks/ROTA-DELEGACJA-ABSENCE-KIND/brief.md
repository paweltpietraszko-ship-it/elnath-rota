# ROTA-DELEGACJA-ABSENCE-KIND — delegacja jako blokada dostępności i realne godziny pracy

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS

BASE_MAIN_SHA: `91907bc39c0b6f8d83b5e05b724e8eac36e24067`
SOURCE_REQUEST: `BOARD.md` / `ROTA-DELEGACJA-ABSENCE-KIND`
OWNER_RULING: nowy rodzaj DELEGACJA dla obu regime'ów; blokuje automatyczne przydzielenie pracy jak pełnodniowa nieobecność, ale jej godziny liczą się jako realnie przepracowane; każdy Site ma własny default godzin, a konkretna delegacja może ten default nadpisać.

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

Najprostszy dozwolony model:
- pole na istniejącym Site / istniejącym ownerze persistence Site;
- integer > 0;
- istniejące Site po migracji mogą mieć `NULL` wyłącznie jako stan legacy wymagający konfiguracji przed utworzeniem pierwszej DELEGACJI;
- NIE wprowadzać globalnego ukrytego defaultu 7h/8h, którego OWNER nie ustalił.

UI podczas tworzenia DELEGACJI:
- wstępnie podpowiada `delegation_default_hours` bieżącego Site;
- koordynator może zmienić wartość dla konkretnego rekordu;
- zapisana wartość trafia do `AvailabilityRecord.delegation_hours`.

Późniejsza zmiana defaultu nie przepisuje wcześniejszych rekordów.

## 5. Blokada automatycznego planowania

DELEGACJA blokuje automatyczne przypisanie pracy na każdy dzień objęty rekordem dokładnie jak istniejące whole-day kinds, które dziś blokują Assignment automatyczny.

Wymagania:
- wspólny istniejący eligibility/validator path;
- brak lokalnej kopii overlap logic;
- brak osobnego solver passu;
- brak szczególnego wyjątku dla OCHRONA/ORDINARY.

Nie zmieniać ogólnej semantyki manual correction. DELEGACJA ma wejść do tych samych istniejących validator gates, których używają inne whole-day niedostępności; ten Task nie tworzy nowego coordinator override ani nowego Deviation lifecycle.

## 6. Godziny delegacji NIE są excused absence

DELEGACJA nie należy do `EXCUSED_ABSENCE_KINDS`.

W szczególności:
- nie zmniejsza targetu tak jak `SICK_LEAVE`/`LEAVE_GRANTED`;
- nie korzysta z `EXCUSED_ABSENCE_HOURS_PER_DAY`;
- nie dziedziczy PRE_PLAN_LEAVE/POST_PLAN_REFERENCE semantyki nieobecności usprawiedliwionej.

Jej `delegation_hours` są godzinami realnie zaliczanymi do pracy.

## 7. Jeden owner rozliczania godzin delegacji

Należy dodać jeden czysty helper/projection dla godzin DELEGACJI, używany przez wszystkie miejsca sumujące czas pracy.

Minimalny kontrakt:
- bierze aktywne rekordy DELEGACJA;
- dla każdego dnia rekordu dodaje zapisane `delegation_hours`;
- clipping do żądanego zakresu dat;
- nie zgaduje godzin przy brakującej wartości — fail closed;
- nie miesza się z excused-absence precedence.

Preferowane miejsce: istniejący moduł `rota/planning/absence.py` jako wspólny owner obliczeń Availability-based hours, ale bez dokładania DELEGACJI do istniejących helperów `excused_*`.

Zakazane:
- osobne obliczenie w PDF i osobne w balance;
- odtwarzanie godzin z Site defaultu podczas historycznego odczytu;
- traktowanie DELEGACJI jako sztucznego Assignmentu tylko po to, by podbić sumę godzin.

## 8. WorkBalance / kwartalne rozliczenie

`rota/balance.py` ma doliczać godziny DELEGACJI do real worked hours pracownika w odpowiednim zakresie.

Semantyka:

`worked_hours_total = assignment_real_work_hours + delegation_hours`

z zachowaniem wszystkich istniejących zasad dla Assignmentów i innych absences.

DELEGACJA nie odejmuje expected/target hours; dodaje wykonane godziny.

## 9. Solver / target

Automatyczny solver:
- nie może przydzielić Assignmentu w dniu DELEGACJI;
- DELEGACJA nie jest mechanizmem obniżania target_hours;
- jeżeli live TARGET/WorkBalance objective korzysta z wykonanych/zaliczonych godzin, powinien konsumować ten sam canonical delegation-hours projection zamiast drugiej implementacji.

Codex ma w preimplementation audycie wskazać dokładne call sites, żeby nie powstały dwie różne definicje „worked hours”.

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

W istniejącym formularzu nieobecności:
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
- migration istniejących danych bez przepisywania historycznych AvailabilityRecordów.

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

DEL-07 — kwartalny WorkBalance dolicza delegację do real worked hours dokładnie raz.

DEL-08 — PDF ORDINARY pokazuje `DEL` i dolicza godziny do `Godz.`.

DEL-09 — PDF OCHRONA pokazuje jednoznaczne `DEL`, bez kolizji z D/N, i dolicza godziny do sumy.

DEL-10 — overlapping/multi-day DELEGACJA rozlicza zapisane godziny per objęty dzień dokładnie raz.

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
- balance quarterly adds hours exactly once;
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
- `rota/persistence/db.py` lub aktualny moduł migracji po refaktorze DB :: schema/migration.
- `rota/persistence/availability_repository.py` :: round-trip rekordu.
- `rota/persistence/site_repository.py` :: Site default persistence.
- `rota/application/durable_inputs.py` :: jedyny write path Availability/Site setting.
- `rota/planning/eligibility.py` :: automatic whole-day blocker.
- `rota/planning/validator.py` i aktualne helpery availability :: ten sam gate, bez kopii.
- `rota/planning/absence.py` :: canonical delegation-hours projection, osobno od excused absence.
- `rota/planning/solver.py` :: wyłącznie call site, jeśli target/worked-hours accounting konsumuje absence projection.
- `rota/balance.py` :: quarterly worked hours.
- `rota/application/schedule_export.py` :: export model + monthly sums.
- `api/routers/durable_inputs.py` / właściwy istniejący availability endpoint.
- właściwy istniejący Site settings endpoint; nie tworzyć nowego routera bez potrzeby.
- `frontend/src/screens/EmployeeDetail.tsx` :: istniejący absence form/log; uwzględnić osobny size-limit finding — preferować wydzielenie komponentu, jeśli implementacja miałaby dalej powiększać plik.
- właściwy istniejący ekran ustawień Site.
- `frontend/src/api/client.ts`.

## 17. TASK_SCOPE

TASK_SCOPE:
- `tasks/ROTA-DELEGACJA-ABSENCE-KIND/**`
- `rota/domain.py`
- aktualny moduł/mody migracji DB wymagane dla nowych pól
- `rota/persistence/availability_repository.py`
- `rota/persistence/site_repository.py`
- `rota/application/durable_inputs.py`
- `rota/planning/eligibility.py`
- `rota/planning/validator.py`
- istniejące helpery validatora availability, jeśli są faktycznym ownerem
- `rota/planning/absence.py`
- `rota/planning/solver.py`
- `rota/balance.py`
- `rota/application/schedule_export.py`
- `api/routers/durable_inputs.py`
- istniejący router Site settings wskazany przez WHERE_MAP
- `frontend/src/api/client.ts`
- istniejący ekran/formularz Site settings wskazany przez WHERE_MAP
- komponent formularza/logu Availability; jeśli dziś siedzi w `EmployeeDetail.tsx`, implementer ma najpierw respektować istniejący finding limitu pliku i nie dokładać kolejnego dużego bloku inline
- testy celowane utworzone/zmienione wyłącznie dla powyższych kontraktów

Każda nowa produkcyjna ścieżka poza tym zakresem wymaga STOP + pytanie do architekta.

## 18. Preimplementation audit Codexa

Codex ma przed implementacją sfalsyfikować:
1. czy `AvailabilityRecord` jest właściwym jedynym ownerem faktu DELEGACJA;
2. czy `delegation_hours` jako snapshot eliminuje potrzebę historycznego lookupu Site defaultu;
3. dokładne miejsca wspólnego whole-day blocker dla solvera i validatora;
4. czy WorkBalance/solver/export mają dziś różne owner-y sumy godzin i gdzie wpiąć jeden canonical projection bez duplikacji;
5. czy `DEL` jest jednoznaczne w obu rendererach i nie koliduje z D/N/S1/Urlop/L4;
6. dokładny istniejący owner ustawień Site dla `delegation_default_hours`;
7. czy TASK_SCOPE obejmuje realne pliki po refaktorze DB/validatora bez niejawnego rozszerzania;
8. jak wdrożyć frontend bez dalszego rozrostu `EmployeeDetail.tsx` powyżej zgłoszonego limitu.

IMPLEMENTATION HOLD do PASS preimplementation na dokładnym SHA tego briefu.

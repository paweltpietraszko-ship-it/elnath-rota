# ROTA-T065-MANUAL-MIDDLE-SHIFT — ręczna dodatkowa praca ORDINARY przez istniejącą korektę

STATUS: OWNER_CORRECTED — IMPLEMENTATION PASS R4 / MERGE READY

SOURCE:
- `ROTA-T065-PANEL-CLEANUP` finding B
- audit R1 `tasks/ROTA-T065-MANUAL-MIDDLE-SHIFT/round_01/tests/tests_r1.txt`
- OWNER: „zmiana ruchoma/środek” = sezonowa/eventowa dodatkowa praca dodawana ręcznie, nie zadanie solvera
- OWNER: wykonywanie innej pracy nie zmienia stanowiska organizacyjnego pracownika
- OWNER: solver nie robi automatycznej hierarchii ról; zastępstwo jest jawną decyzją koordynatora
- OWNER_CORRECTED 2026-09-14 po R3-01: wspieranym scenariuszem produktu są ścieżki solvera oraz normalne działania koordynatora przez interfejs programu; ręcznie preparowane techniczne żądania do ogólnego endpointu API poza tym interfejsem nie są scenariuszem pracy produktu ani acceptance tego Tasku
- istniejący `apply_manual_correction()` / child `ScheduleVersion` / validator / Deviation / site-memory audit

## 1. Cel

Dla `SitePlanningRegime.ORDINARY` umożliwić koordynatorowi dodanie do istniejącego grafiku konkretnej dodatkowej pracy, np. sezonowego/eventowego „środka” `10:00–16:00`.

To jest realna praca:
- konkretnego pracownika;
- w konkretnym realnym przedziale czasu;
- w konkretnej roli wykonywanej pracy;
- zapisana w historii grafiku.

Nie jest to nowy rodzaj pracy solvera ani nowy wpis `StandardShift`.

## 2. Twarde zależności

Implementacja tego Tasku NIE może ruszyć przed produkcyjnym domknięciem:

1. `ROTA-T065-CONFIGURABLE-ROLES` — dostarcza `position_role_id`, dynamiczne role oraz jedyny `RoleCoverageAuthorization`;
2. `ROTA-T065-ORDINARY-TIME-AVAILABILITY` — dostarcza jeden shared oracle i `UNAVAILABLE_TIME-01`.

Brief może przejść preimplementation review wcześniej, ale implementer nie może lokalnie kopiować brakujących mechanizmów z tych Tasków.

## 3. Jeden lifecycle — Manual Correction

„Środek” powstaje wyłącznie przez istniejący manual-correction lifecycle:

`CURRENT ScheduleVersion -> apply_manual_correction() -> validate() -> materialize deviations -> child ScheduleVersion -> CURRENT -> existing audit/action trail`.

Nie tworzyć:
- `middle_shift_repository`;
- drugiego endpointu historii grafiku;
- osobnej tabeli event work;
- osobnego validatora;
- solver passu;
- generatora demandów.

## 4. Nie używać S1

`AssignmentRole.PERIODIC_TRAINING` / S1 pozostaje szkoleniem okresowym i NIE może być markerem „środka”.

Manual middle:
- jest `AssignmentRole.PRIMARY`;
- liczy się jako normalna realna praca do overlap/LOAD/REST/WorkBalance zgodnie z istniejącym reżimem ORDINARY;
- nie dziedziczy żadnego zwolnienia S1 z REST/WEEKLY-REST ani presentation semantics S1.

## 5. Minimalny marker legalnego PRIMARY bez ShiftDemand

Dzisiejszy fail-closed invariant słusznie wymaga `covers_demand_id` dla PRIMARY. Nie wolno go po prostu poluzować.

Manual middle jest jedynym nowym, jawnie opisanym wyjątkiem i musi być strukturalnie rozpoznawalny.

Do `Assignment` dochodzą dwa opcjonalne historyczne pola:
- `manual_work_role_id`;
- `manual_work_role_name`.

Te pola są zarazem minimalnym markerem i snapshotem wykonywanej roli pracy.

Persistence invariant:

### 5.1 Zwykły PRIMARY z demandem
- `covers_demand_id` MUSI istnieć i rozwiązywać się w tej samej ScheduleVersion;
- `manual_work_role_id/manual_work_role_name` MUSZĄ być `None`.

### 5.2 Legalny manual middle PRIMARY
- `covers_demand_id is None`;
- `manual_work_role_id` i `manual_work_role_name` MUSZĄ być oba obecne;
- Assignment musi pochodzić z `apply_manual_correction()`, nie ze ścieżki solvera/PlanPreview;
- rola musi istnieć w katalogu tego Site w chwili zapisu;
- interval i employee muszą przejść normalne validation gates.

### 5.3 Każdy inny PRIMARY bez demandu
- fail closed jako `MalformedScheduleSnapshot` / istniejący odpowiednik;
- brak markerów nie może być interpretowany jako manual work „na wszelki wypadek”.

Nie dodawać ogólnego `covers_demand_id optional for PRIMARY` bez tego invariant.

`manual_work_role_name` jest snapshotem historycznym; późniejszy rename/retire roli nie zmienia starej pracy.

## 6. Rola wykonywanej pracy ≠ stanowisko

Pracownik zachowuje `SiteMembership.position_role_id` z `ROTA-T065-CONFIGURABLE-ROLES`.

Jeżeli `manual_work_role_id == position_role_id`, nie potrzeba zastępstwa.

Jeżeli role są różne, manual middle może zostać zapisany tylko wtedy, gdy istnieje aktywne `RoleCoverageAuthorization` tego samego Site/pracownika/roli pokrywające cały interval manual middle.

To jest JEDYNY mechanizm autoryzacji zastępstwa. `ROLE-01` Deviation nie jest alternatywną zgodą na zastępstwo i nie może tworzyć drugiej semantyki.

Brak wymaganej autoryzacji = operacja odrzucona przed utworzeniem child ScheduleVersion, a nie zapisana jako zwykłe odchylenie — dla wspieranej ścieżki produktu, czyli normalnej akcji `Dodaj pracę` w UI i odpowiadającego jej dedykowanego application/API path.

**OWNER_CORRECTED (2026-09-14, po R3-01):** powyższa gwarancja jest kontraktem wspieranej ścieżki produktu, nie ogólnym zabezpieczeniem każdego technicznie osiągalnego kształtu HTTP. Bezpośrednie spreparowanie żądania do generycznego endpointu `/manual-correction` z polami `manual_work_role_*`, którego normalny interfejs programu nie wysyła, jest poza scenariuszem pracy i acceptance tego Tasku. Znana możliwość takiego technicznego obejścia API pozostaje udokumentowaną właściwością techniczną, ale nie jest defektem produktu ani blockerem merge. Nie wolno z tego wnioskować, że UI lub solver mogą omijać `RoleCoverageAuthorization`.

Stanowisko pracownika nie zmienia się w UI, historii ani PDF.

## 7. Availability — obowiązkowo ten sam gate

Manual middle musi przejść `UNAVAILABLE_TIME-01` z `ROTA-T065-ORDINARY-TIME-AVAILABILITY` przy użyciu dokładnie tego samego shared overlap oracle co automatic eligibility.

Przykład:
- niedostępność `00:00–12:00`;
- manual middle `10:00–16:00`;
- validator MUSI wykryć `UNAVAILABLE_TIME-01`.

Nie wolno implementować lokalnego porównania godzin w `manual_edit.py`.

Zgodnie z istniejącą ogólną semantyką Manual Correction, wykryty HARD może przejść wyłącznie istniejącą ścieżką deviation/acknowledgement, jeżeli obecny lifecycle tę kategorię dopuszcza. Ten Task nie tworzy specjalnego bypassu availability i nie może przepuścić kolizji jako poprawnej bez deviation.

## 8. Walidacja pozostałych reguł

Manual middle uczestniczy w istniejących sprawdzeniach realnej pracy:
- overlap;
- REST;
- LOAD;
- cross-Site context;
- WorkBalance;
- history/final immutability;
- odpowiednie ogólne AvailabilityKinds.

Nie aktywuje ochroniarskich D/N/day_only/24h tylko dlatego, że godziny przypominają zmianę ochrony.

Nie dziedziczy zwolnień S1.

## 9. UI/API

W istniejącej sekcji `Ręczna korekta` dla ORDINARY dochodzi akcja `Dodaj pracę`/równoważna, która wymaga:
- pracownika;
- daty;
- godziny od;
- godziny do;
- roli wykonywanej pracy z katalogu Site;
- opcjonalnej notatki istniejącego manual-correction flow.

Pełnogodzinna precyzja pozostaje zgodna z aktualnym kontraktem grafiku. Nie otwieramy minut.

UI nie dodaje tej pracy do stałego katalogu zmian i nie oferuje „zapisz jako zmianę”.

Wspieranym entry pointem manual middle jest dedykowana akcja UI `Dodaj pracę` i odpowiadający jej endpoint/application wrapper `add_manual_middle_work()`. Generyczny endpoint manual correction pozostaje technicznym mechanizmem lifecycle i nie jest publicznym kontraktem do ręcznego konstruowania manual middle poza UI.

## 10. Historia i PDF

Historia ScheduleVersion zachowuje `manual_work_role_id/manual_work_role_name` jako fakt wykonywanej pracy.

Zaakceptowany kontrakt `ROTA-T065-PRINT-GAP` NIE zmienia się:
- w komórce ORDINARY drukowane są wyłącznie realne godziny;
- rola wykonywanej pracy NIE jest dopisywana przy godzinach;
- pod nazwiskiem widnieje jedno historyczne stanowisko pracownika z configurable-roles snapshotu.

Ten Task NIE zmienia `schedule_export.py`. Deklaruje integracyjną zależność: produkcyjny PRINT-GAP ma rozpoznawać legalny manual-middle PRIMARY jako realną pracę na podstawie powyższego invariant i drukować jego godziny, bez wymagania `ShiftDemand` i bez roli w komórce.

## 11. Acceptance

MM-01 — koordynator może dodać `10:00–16:00` jako PRIMARY manual middle do istniejącego ORDINARY ScheduleVersion; powstaje normalny child i action trail.

MM-02 — zapisany manual middle ma `covers_demand_id=None` oraz komplet `manual_work_role_id/manual_work_role_name`.

MM-03 — arbitralny PRIMARY bez demandu i bez obu markerów nadal failuje persistence validation; invariant nie został globalnie rozluźniony.

MM-04 — solver/PlanPreview nigdy nie generuje Assignment z `manual_work_role_*`.

MM-05 — przez wspieraną akcję produktu `Dodaj pracę` osoba na stanowisku `Kierownik`, bez RoleCoverageAuthorization na rolę `Sprzedawca`, nie może zapisać manual middle jako `Sprzedawca`. Bezpośrednio spreparowane żądanie do generycznego technicznego `/manual-correction` jest poza zakresem tego acceptance zgodnie z OWNER_CORRECTED powyżej.

MM-06 — po jawnej, aktywnej autoryzacji pokrywającej interval może wykonać tę pracę, ale jej stanowisko pozostaje `Kierownik`.

MM-07 — `00:00–12:00` hourly unavailability + manual middle `10:00–16:00` generuje `UNAVAILABLE_TIME-01` przez ten sam oracle co solver; nie przechodzi bez wykrytego deviation.

MM-08 — overlap/REST/LOAD dla manual middle zachowują zwykłą semantykę PRIMARY; brak exemption S1.

MM-09 — historyczny reload zachowuje snapshot wykonywanej roli po późniejszym rename/retire katalogu.

MM-10 — PRINT-GAP pokazuje godziny manual middle jako kolejny realny przedział, ale nie drukuje wykonywanej roli w komórce i nie zmienia stanowiska pod nazwiskiem.

MM-11 — OCHRONA i PERIODIC_TRAINING/S1 regression unchanged.

## 12. WHERE_MAP

WHERE_MAP: REQUIRED
- `rota/domain.py` :: `Assignment.manual_work_role_id/manual_work_role_name`; `AssignmentRole` bez nowej wartości dla middle.
- `rota/persistence/db.py` :: migracja kolumn Assignment; nie istnieje `schema.py`.
- `rota/persistence/schedule_validation.py` :: fail-closed invariant PRIMARY z demandem vs legalny manual middle bez demandu.
- `rota/persistence/schedule_repository.py` :: round-trip obu markerów/snapshotu.
- `rota/persistence/schedule_lifecycle.py` :: zapis markerów przez ten sam ScheduleVersion lifecycle.
- `rota/application/manual_edit.py` :: istniejący application lifecycle/deviation/audit owner, do którego deleguje manual middle.
- `rota/application/manual_middle_work.py` :: cienki wspierany entry point manual middle z precheckami ORDINARY/role/membership/RoleCoverageAuthorization; deleguje do istniejącego `apply_manual_correction()`.
- `rota/application/deviation_mapping.py` :: istniejące mapowanie `UNAVAILABLE_TIME-01` do zaakceptowanej kategorii Deviation; TECHNICAL_ONLY domknięcie istniejącej reguły.
- `rota/planning/validator.py` + `rota/planning/validator_shared.py` :: role/availability i wyłączenie manual middle z demand coverage w istniejącym validatorze; bez drugiego validatora.
- `api/routers/manual_edit.py` :: dedykowany endpoint akcji `Dodaj pracę` oraz istniejący generyczny manual-correction lifecycle; techniczne ręczne użycie generycznego endpointu poza UI jest poza kontraktem produktu.
- `api/routers/schedule.py` :: Assignment API round-trip nowych pól tam, gdzie istniejący model Assignment jest marshallowany.
- `frontend/src/screens/MonthlyPlanning.tsx` :: akcja `Dodaj pracę` wewnątrz istniejącej Manual Correction.
- `frontend/src/api/client.ts` :: kontrakt request/response.
- `ROTA-T065-CONFIGURABLE-ROLES` :: jedyny `RoleCoverageAuthorization`, bez lokalnej kopii.
- `ROTA-T065-ORDINARY-TIME-AVAILABILITY` :: jedyny `UNAVAILABLE_TIME-01` overlap oracle.
- `ROTA-T065-PRINT-GAP` :: późniejszy consumer legalnego manual-middle PRIMARY; poza zmianami tego Tasku.

## 13. TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T065-MANUAL-MIDDLE-SHIFT/**
- rota/domain.py
- rota/persistence/db.py
- rota/persistence/schedule_validation.py
- rota/persistence/schedule_repository.py
- rota/persistence/schedule_lifecycle.py
- rota/application/manual_edit.py
- rota/application/manual_middle_work.py
- rota/application/deviation_mapping.py
- rota/planning/validator.py
- rota/planning/validator_shared.py
- api/routers/manual_edit.py
- api/routers/schedule.py
- frontend/src/screens/MonthlyPlanning.tsx
- frontend/src/api/client.ts
- tests/test_t065_manual_middle_shift.py
- tests/test_t009_manual_edit.py
- tests/test_t037_manual_edit_api.py
- tests/test_local_store_schedule_content_rules.py
- tests/test_local_store_schedule_version_lifecycle.py

## 14. FINAL STATUS

Zależności są produkcyjnie dostępne, implementacja została ukończona i audyt R4 wydał PASS na dokładnym kodzie `597d4037e39d51bfd9d0fc4e176532db1acb6486`.

R3-01 pozostaje zachowany jako reproduktor technicznej właściwości generycznego API, ale po OWNER_CORRECTED nie jest findingiem produktowym ani blockerem merge. Nie wymaga zmiany produkcji.

Trzy pliki wcześniej poza literalnym TASK_SCOPE (`manual_middle_work.py`, `deviation_mapping.py`, `validator_shared.py`) są jawnie zaakceptowanymi TECHNICAL_ONLY lokalizacjami implementacji i zostały powyżej dopisane do WHERE_MAP/TASK_SCOPE bez zmiany zachowania produktu.

Werdykt kontraktowy: PASS — GOTOWE DO MERGE na dokładnym kodzie `597d4037e39d51bfd9d0fc4e176532db1acb6486`.
# ROTA-T065-CONFIGURABLE-ROLES — konfigurowalne role ORDINARY bez degradacji stanowiska

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS

SOURCE:
- BOARD finding `ROTA-T065-CONFIGURABLE-ROLES`
- audit R1 `tasks/ROTA-T065-CONFIGURABLE-ROLES/round_01/tests/tests_r1.txt`
- OWNER ruling `main@3836d5c` / `tests_r2.txt`
- OWNER: każda praca ORDINARY ma rolę; zestaw ról zależy od obiektu/branży
- OWNER: kierownik wykonujący zastępstwo sprzedawcy nadal jest kierownikiem; produkt nie może prezentować go jako `Kierownik/Sprzedawca`
- OWNER: solver nie może automatycznie użyć kierownika jako sprzedawcy; koordynator może wybrać external support albo jawne zastępstwo dla konkretnego przypadku/okresu
- istniejący T065 model `EmployeeRole`, `SiteMembership.allowed_roles`, `ShiftDemand.required_role`, ROLE-01

## 1. Cel

Naprawić zbyt wąski model T065 bez tworzenia drugiego solvera ani równoległej domeny grafiku.

ORDINARY ma obsługiwać dowolny Site z własnym katalogiem ról, np. sklep (`Kierownik`, `Sprzedawca`) albo hurtownię (`Kierownik`, `Magazynier`, `Wózkowy`, `Kasjer`). Role nie są globalnym Python `Enum` ograniczonym do dwóch wartości.

## 2. Dwie różne prawdy domenowe — NIE ŁĄCZYĆ

Produkt rozdziela:

1. **stanowisko organizacyjne pracownika na Site** — kim człowiek jest, np. `Kierownik`;
2. **rolę wymaganej/wykonywanej pracy** — jaki rodzaj obsady pokrywa konkretny demand albo ręcznie dodana praca, np. `Sprzedawca`.

Kierownik pokrywający jednorazowo pracę sprzedawcy nadal ma stanowisko `Kierownik`.

ZABRONIONE:
- prezentowanie stanowiska `Kierownik/Sprzedawca` tylko dlatego, że osoba może pokryć obcy slot;
- zmiana stanowiska wskutek Assignment;
- używanie jednego zbioru jako równocześnie tytułu człowieka i listy zastępstw;
- automatyczna hierarchia typu `Kierownik > Sprzedawca`.

## 3. Owner katalogu ról per Site

Powstaje jeden owner bieżącego katalogu ról ORDINARY: `rota/persistence/site_role_repository.py`.

Minimalny rekord katalogu:
- `role_id` — stabilny techniczny identyfikator;
- `site_id` — właściciel roli;
- `display_name` — dowolna nazwa prezentacyjna;
- `active` — czy rola jest dostępna dla nowych konfiguracji.

Nie tworzyć globalnego enuma branżowego. `EmployeeRole` przestaje być źródłem prawdy produkcyjnej dla ORDINARY.

Zmiana nazwy/wycofanie roli wpływa wyłącznie na stan bieżący i przyszłe nowe snapshoty. Nie może przepisywać zapisanych `ShiftDemand` ani stanowisk zapisanych przy historycznej `ScheduleVersion`.

## 4. Stanowisko bieżące — dokładnie jedno na membershipie

`SiteMembership` dla ORDINARY dostaje osobne `position_role_id` wskazujące dokładnie jedno aktywne stanowisko organizacyjne na tym Site.

To pole:
- jest bieżącym durable inputem koordynatora;
- nie jest listą zastępstw;
- nie jest wyprowadzane z historii pracy;
- dla OCHRONA pozostaje `None`/nieużywane;
- musi wskazywać rolę należącą do tego samego Site.

Dotychczasowe `allowed_roles` nie może pozostać równoległym źródłem prawdy. Implementacja ma usunąć jego biznesowe użycie w ORDINARY albo ograniczyć je wyłącznie do kompatybilności odczytu testowych danych, bez udziału w nowym ROLE-01.

## 5. Każdy nowy demand ORDINARY ma rolę

`StandardShift` dla ORDINARY wskazuje `required_role_id` z katalogu tego Site. Opcja biznesowa `— brak —` znika.

Przy generowaniu konkretnego `ShiftDemand` zapisywany jest historyczny snapshot:
- `required_role_id`;
- `required_role_name` z bieżącego katalogu w chwili generowania/akceptacji.

Snapshot przechodzi całą istniejącą drogę:

`StandardShift -> generator -> PlanPreview -> select_candidate -> ScheduleVersion/ShiftDemand persistence -> reload/history`.

Zmiana nazwy lub wycofanie roli później nie zmienia historycznego demandu.

OCHRONA zachowuje dotychczasowe zachowanie i nie wymaga ról ORDINARY.

## 6. Historyczne stanowisko pracownika dla ScheduleVersion

Bieżący `SiteMembership.position_role_id` jest mutowalny i NIE może być źródłem historycznego reprintu.

Dlatego zawartość zaakceptowanej `ScheduleVersion` ORDINARY dostaje minimalny snapshot stanowisk pracowników używany wyłącznie jako historyczna prawda prezentacyjna:

`schedule_version_employee_positions(version_id, employee_id, role_id, role_name)`.

Właścicielem odczytu tego snapshotu jest istniejąca warstwa `rota/persistence/schedule_repository.py`; zapis odbywa się w istniejącym transakcyjnym lifecycle ScheduleVersion (`schedule_lifecycle.py` / `plan_ops.select_candidate`), nie przez drugi lifecycle.

Zasady:
- snapshot jest materializowany w tej samej transakcji, w której kandydat staje się zaakceptowaną zawartością `ScheduleVersion`;
- nowy child ScheduleVersion tworzony przez późniejsze operacje zapisuje własny snapshot bieżących stanowisk dla osób obecnych w realnych `assignments` tej ScheduleVersion w chwili utworzenia childa;
- osoba bez żadnego realnego `Assignmentu` w tej ScheduleVersion może nie mieć wiersza w `schedule_version_employee_positions`;
- już istniejący snapshot wersji nigdy nie jest reinterpretowany z dzisiejszego membershipu;
- `role_name` w snapshotcie jest tekstem historycznym: późniejszy rename/retire katalogu nie zmienia starej wersji;
- nie snapshotujemy całego membershipu ani listy zastępstw — tylko minimalne `employee_id + role_id + role_name` potrzebne do historycznej prezentacji.

**OWNER_CORRECTED (2026-09-14, po ROTA-T065-PRINT-GAP R6-01):** wcześniejsze sformułowanie „dla osób należących do Site” zostaje superseded. Snapshot stanowisk obejmuje osoby obecne w realnych `assignments` danej ScheduleVersion. Pracownik bez żadnego przypisania w drukowanym miesiącu może nie mieć historycznego wiersza stanowiska i na wydruku może mieć pustą etykietę stanowiska. To jest świadomie zaakceptowane ograniczenie PRODUCT_TRUTH, zgodne z `ROTA-T065-PRINT-GAP` T65P-04 OWNER_CORRECTED; nie wolno z tego powodu odtwarzać stanowiska z bieżącego `SiteMembership` ani z roli demandu.

`ROTA-T065-PRINT-GAP` ma czytać jedną etykietę stanowiska spod nazwiska właśnie z tego snapshotu, nigdy z bieżącego `SiteMembership` i nigdy z roli demandu.

## 7. Jawne zastępstwo innej roli — osobny fakt, skończony w czasie

Brak właściwej obsady nie uruchamia żadnego fallbacku. Solver zwraca istniejący wynik niewykonalności/braku obsady. Koordynator wybiera remedium: np. external support albo jawne zastępstwo.

Jawne zastępstwo jest osobnym durable inputem obsługiwanym przez tego samego ownera katalogu ról (`site_role_repository.py`) jako `RoleCoverageAuthorization`:
- `authorization_id`;
- `site_id`;
- `employee_id`;
- `covered_role_id`;
- `start_datetime`;
- `end_datetime`;
- stan aktywny/anulowany zgodny z istniejącym audytowalnym durable-input lifecycle.

`start_datetime` i `end_datetime` są wymagane. Nie ma bezterminowego dopuszczenia ani stałej cechy pracownika.

Autoryzacja:
- nie zmienia `position_role_id`;
- nie tworzy drugiego stanowiska;
- nie wynika z nazwy/hierarchii roli;
- kwalifikuje pracownika wyłącznie do demandu, którego cały realny interval mieści się w aktywnym oknie autoryzacji i którego `required_role_id == covered_role_id`.

External support używa dokładnie tej samej zasady ROLE-01; nie ma osobnej hierarchii dla external.

## 8. ROLE-01 — jeden gate, jeden solver

ROLE-01 pozostaje jednym gate'em używanym przez istniejący planning/validator.

Dla ORDINARY demand może pokryć pracownik tylko wtedy, gdy:

`demand.required_role_id == membership.position_role_id`

LUB istnieje aktywne `RoleCoverageAuthorization` pokrywające dokładnie ten demand.

Brak obu warunków = `ROLE-01`.

Nie dodawać:
- drugiego solvera;
- passu per rola;
- role fallbacku;
- automatycznego szukania external;
- hierarchy engine.

## 9. UI/API

Konfiguracja ORDINARY musi pozwalać:
- utrzymywać katalog ról Site;
- przypisać pracownikowi jedno stanowisko;
- wybrać obowiązkową rolę dla każdego wiersza katalogu zmian;
- utworzyć/anulować jawne, datowane dopuszczenie zastępstwa bez zmiany stanowiska.

`SiteShiftCatalog.tsx` nie pokazuje `— brak —` dla roli ORDINARY.

`ControlPanel`/`EmployeeDetail` nie może prezentować zastępstw jako łączonego stanowiska.

## 10. Migracja

Dzisiejsze ORDINARY są testowe zgodnie z wcześniejszą decyzją OWNERA przy T065 R4-01. Nie projektować rozbudowanej migracji historycznych danych ORDINARY.

Migracja schematu może wyczyścić/pozostawić nieużywane testowe `allowed_roles` zgodnie z najprostszą bezpieczną ścieżką. OCHRONA i jej historia nie mogą się zmienić.

## 11. Acceptance

CR-01 — Site A może mieć `Kierownik`, `Sprzedawca`; Site B `Magazynier`, `Wózkowy`, `Kasjer` bez zmiany kodu domenowego.

CR-02 — każdy nowy demand ORDINARY ma `required_role_id` i historyczne `required_role_name`; brak roli jest odrzucany przed PLAN.

CR-03 — pracownik o stanowisku `Kierownik` nie kwalifikuje się automatycznie do demandu `Sprzedawca`.

CR-04 — brak sprzedawcy może zakończyć PLAN istniejącym wynikiem braku obsady; solver nie wybiera kierownika jako remedium.

CR-05 — po utworzeniu przez koordynatora autoryzacji `Kierownik -> Sprzedawca` na konkretny okres zwykły PLAN/REPLAN może użyć tej osoby wyłącznie w pokrytym przedziale; po końcu okresu autoryzacja nie działa.

CR-06 — UI i PDF nadal prezentują stanowisko tej osoby jako `Kierownik`.

CR-07 — rename/retire roli po zapisaniu ScheduleVersion nie zmienia `required_role_name` dawnych demandów ani `role_name` dawnego snapshotu stanowiska.

CR-08 — historyczny reprint starej ScheduleVersion nie czyta bieżącego membershipu.

CR-09 — PlanPreview round-trip zachowuje dynamiczne role bez globalnego `EmployeeRole` enuma.

CR-10 — OCHRONA regression unchanged.

## 12. WHERE_MAP

WHERE_MAP: REQUIRED
- `rota/domain.py` :: `EmployeeRole`, `StandardShift.required_role`, `SiteMembership.allowed_roles`, `ShiftDemand.required_role` — zastąpić dynamicznym `role_id`/snapshotami bez zmiany `AssignmentRole`.
- `rota/persistence/site_role_repository.py` :: NOWY pojedynczy owner katalogu Site + datowanych `RoleCoverageAuthorization`; żadnego drugiego repo ról.
- `rota/persistence/employee_repository.py` :: persistence `SiteMembership.position_role_id`; brak drugiego membershipu dla tej samej osoby/Site.
- `rota/persistence/site_profile_repository.py` :: persistence `StandardShift.required_role_id`.
- `rota/persistence/plan_preview_repository.py` :: round-trip `ShiftDemand.required_role_id/required_role_name`.
- `rota/persistence/schedule_repository.py` :: round-trip demand role + odczyt `schedule_version_employee_positions`.
- `rota/persistence/schedule_lifecycle.py` :: zapis historycznych snapshotów w tym samym transaction/lifecycle ScheduleVersion.
- `rota/persistence/db.py` :: migracja tabel/kolumn; nie istnieje `schema.py`.
- `rota/planning/shift_catalog.py` :: generator dynamicznego required role, bez drugiego generatora.
- `rota/planning/eligibility.py` + `rota/planning/validator.py` :: jeden ROLE-01 oparty na position lub datowanej autoryzacji.
- `rota/planning/state.py` :: niesie bieżące autoryzacje ról w istniejącym `PlanningState`; bez równoległego state/modelu planowania.
- `rota/planning/solver.py` :: wyłącznie adapter do istniejącego ROLE-01/zmienionego kształtu domeny; bez drugiego solvera ani nowej logiki zastępstw.
- `rota/application/assembler.py` :: dostarczenie katalogu/autoryzacji do istniejącego PlanningState.
- `rota/application/plan_ops.py` :: przy akceptacji kandydata materializacja snapshotu stanowisk w tej samej transakcji.
- `rota/application/durable_inputs.py` :: jedyny application write path bieżącego stanowiska/katalogu/autoryzacji.
- `rota/site_memory_types.py` :: kompatybilne DTO/readback dla dynamicznej roli; nie jest ownerem ról.
- `api/routers/site_profile.py` :: katalog zmian czyta role Site, nie globalny enum.
- `api/routers/roster.py` + `api/routers/durable_inputs.py` :: stanowisko pracownika i autoryzacja zastępstwa.
- `api/routers/schedule.py` :: marshalling historycznej nazwy wymaganej roli w istniejącym API grafiku; bez nowego lifecycle.
- `frontend/src/screens/SiteShiftCatalog.tsx` :: role dynamiczne, obowiązkowe dla ORDINARY.
- `frontend/src/screens/ControlPanel.tsx` + `frontend/src/screens/EmployeeDetail.tsx` :: jedno stanowisko + osobne zastępstwa.
- `frontend/src/api/client.ts` :: kontrakty API.

## 13. TASK_SCOPE

TASK_SCOPE:
- tasks/ROTA-T065-CONFIGURABLE-ROLES/**
- rota/domain.py
- rota/persistence/db.py
- rota/persistence/site_role_repository.py
- rota/persistence/employee_repository.py
- rota/persistence/site_profile_repository.py
- rota/persistence/plan_preview_repository.py
- rota/persistence/schedule_repository.py
- rota/persistence/schedule_lifecycle.py
- rota/planning/shift_catalog.py
- rota/planning/eligibility.py
- rota/planning/validator.py
- rota/planning/solver.py
- rota/planning/state.py
- rota/application/assembler.py
- rota/application/plan_ops.py
- rota/application/durable_inputs.py
- rota/site_memory_types.py
- api/routers/site_profile.py
- api/routers/roster.py
- api/routers/durable_inputs.py
- api/routers/schedule.py
- frontend/src/screens/SiteShiftCatalog.tsx
- frontend/src/screens/ControlPanel.tsx
- frontend/src/screens/EmployeeDetail.tsx
- frontend/src/api/client.ts
- tests/test_t065_configurable_roles.py
- tests/test_t065_ordinary_roles.py
- tests/test_site_profile_persistence.py
- tests/test_local_store_schema_migration.py
- tests/test_t030_shift_catalog_api.py
- tests/test_t031_schedule_api.py
- tests/test_t021_external_support_roster.py
- tests/test_t019.py
- tests/test_t019b.py
- tests/test_t020.py
- tests/test_t021_matrix_decision_link.py
- tests/test_t023b.py
- tests/test_t062.py
- tests/test_vertical_full_stack.py

## 14. HOLD

IMPLEMENTATION HOLD do preimplementation PASS Codexa na dokładnym SHA tego briefu.

Codex ma w re-checku sfalsyfikować przede wszystkim: jeden owner katalogu, jedno stanowisko per membership, stabilny historyczny snapshot per ScheduleVersion, skończoną w czasie autoryzację zastępstwa oraz brak drugiej ścieżki ROLE-01/solver.
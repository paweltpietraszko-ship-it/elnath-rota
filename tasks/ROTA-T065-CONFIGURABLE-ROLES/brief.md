# ROTA-T065-CONFIGURABLE-ROLES — konfigurowalne role ORDINARY bez degradacji stanowiska

STATUS: PREIMPLEMENTATION — IMPLEMENTATION HOLD UNTIL CODEX PASS

SOURCE:
- BOARD finding `ROTA-T065-CONFIGURABLE-ROLES`
- OWNER correction 2026-09-13: każda praca ORDINARY ma rolę; zestaw ról zależy od obiektu/branży
- OWNER correction: kierownik wykonujący zastępstwo sprzedawcy nadal jest kierownikiem; produkt nie może prezentować go jako `Kierownik/Sprzedawca`
- OWNER correction: solver nie może automatycznie użyć kierownika jako sprzedawcy; koordynator może wybrać np. external support zamiast zastępstwa
- istniejący T065 model `EmployeeRole`, `SiteMembership.allowed_roles`, `ShiftDemand.required_role`, ROLE-01

## 1. Cel

Naprawić zbyt wąski model T065 bez tworzenia drugiego solvera ani nowego planowania.

ORDINARY ma obsługiwać dowolny obiekt z własną listą ról, np. sklep, hurtownię lub inny obiekt usługowy. Role nie są globalnym Python `Enum` ograniczonym do dwóch wartości.

## 2. Dwie różne prawdy domenowe — NIE WOLNO ICH ŁĄCZYĆ

Produkt musi rozdzielić:

1. **stanowisko/rola organizacyjna pracownika na obiekcie** — kim człowiek jest w organizacji, np. `Kierownik`;
2. **rola wymaganej/wykonywanej pracy** — jaki rodzaj obsady pokrywa konkretny demand lub ręcznie dodana praca, np. `Sprzedawca`.

Kierownik, który jednorazowo pokrywa pracę sprzedawcy, nadal ma stanowisko `Kierownik`.

ZABRONIONE:
- pokazywanie `Kierownik/Sprzedawca` jako stanowiska tylko dlatego, że osoba może lub mogła pokryć slot sprzedawcy;
- zmiana stanowiska pracownika wskutek przydziału do innej pracy;
- używanie jednego zbioru jako równocześnie tytułu człowieka i listy zastępowalnych ról.

## 3. Katalog ról per obiekt

Każdy Site w reżimie ORDINARY ma konfigurowalny katalog ról biznesowych.

Minimalne wymagania roli:
- stabilne techniczne `role_id` należące do Site;
- dowolna nazwa prezentacyjna wpisana przez koordynatora, np. `Kierownik`, `Magazynier`, `Wózkowy`, `Kasjer`;
- aktywność/wycofanie bez reinterpretowania historii.

Nie wprowadzać globalnego enuma branżowego ani hardcode listy ról.

## 4. Każda praca ORDINARY ma rolę

Dla nowego ORDINARY `StandardShift/ShiftDemand.required_role` nie może mieć biznesowego znaczenia `brak roli`.

Każdy nowy demand ORDINARY wymaga jednej roli z katalogu Site.

OCHRONA pozostaje bez zmian i nie dostaje obowiązkowego katalogu ról ORDINARY.

Historyczny demand musi zachować rolę/nazwę potrzebną do prawdziwego odczytu starego grafiku nawet po późniejszej zmianie katalogu.

## 5. Stanowisko pracownika

SiteMembership dla ORDINARY przechowuje stanowisko organizacyjne pracownika na tym Site jako osobną wartość od uprawnień do zastępstwa.

Stanowisko jest tym, co pokazujemy przy osobie w konfiguracji/UI i co ma zachować godność/status organizacyjny pracownika.

Nie wolno wyprowadzać stanowiska z demandów, które pracownik historycznie pokrywał.

## 6. Zastępstwo innej roli — jawna decyzja koordynatora, nigdy fallback solvera

Solver automatycznie kwalifikuje pracownika do demandu jego własnego stanowiska zgodnie z istniejącymi gate'ami.

Jeżeli brakuje osoby w wymaganej roli, solver NIE może sam uznać, że rola wyższa/inna może ją zastąpić.

Nie ma globalnej hierarchii `Kierownik > Sprzedawca`, ani żadnej innej domyślnej zastępowalności.

Koordynator wybiera rozwiązanie operacyjne. Może m.in.:
- dopisać external support;
- jawnie dopuścić konkretną osobę do pokrycia innej roli;
- zmienić inne dane obsady.

Dopiero po jawnej zmianie stanu zwykły PLAN/REPLAN może korzystać z tego dopuszczenia.

Jawne dopuszczenie zastępstwa:
- jest osobnym faktem od stanowiska;
- wskazuje konkretną osobę, Site i rolę pracy, którą wolno pokryć;
- nie zmienia nazwy/stanowiska pracownika;
- nie wynika z hierarchii ani nazwy roli;
- musi mieć jawny zakres obowiązywania albo inny istniejący, audytowalny mechanizm aktywacji/dezaktywacji; nie wolno cicho przekształcić go w trwałe drugie stanowisko.

Brief nie narzuca nowej osobnej domeny, jeśli istniejący owner durable-input/site-membership może przechować tę informację bez dwóch źródeł prawdy. Codex ma sfalsyfikować minimalny właściciel danych przed implementacją.

## 7. Eligibility — jeden gate, jeden solver

ROLE-01 pozostaje jednym gate'em w istniejącym `eligibility.py`/validatorze.

Dla ORDINARY pracownik może pokryć rolę demandu tylko wtedy, gdy:
- to jego stanowisko na tym Site; LUB
- istnieje jawne, aktywne dopuszczenie koordynatora do pokrycia tej roli.

To samo dotyczy LOCAL i EXTERNAL_SUPPORT.

Nie dodawać:
- drugiego solvera;
- passu per rola;
- automatycznego fallbacku role-to-role;
- wyszukiwania external;
- role hierarchy engine.

## 8. UI

Konfiguracja ORDINARY musi pozwalać:
- utrzymać listę ról Site;
- przypisać pracownikowi jego stanowisko;
- wybrać obowiązkową rolę przy każdym wierszu katalogu zapotrzebowania;
- jawnie zarządzać zastępstwem bez zmiany stanowiska pracownika.

Usunąć biznesową opcję `— brak —` dla roli demandu ORDINARY.

UI nie może prezentować zastępstwa jako łączonego stanowiska `Kierownik/Sprzedawca`.

## 9. Historia i print

Historia zapisanej pracy zachowuje:
- rolę wymaganej/wykonywanej pracy;
- pracownika, który ją wykonał;
- jego stanowisko nie jest retrospektywnie przepisywane przez późniejsze zmiany katalogu/uprawnień.

`ROTA-T065-PRINT-GAP` ma przyjmować dowolną nazwę roli Site, bez założenia dwóch znanych wartości.

Jeżeli kierownik pokrył pracę sprzedawcy, wydruk nie może z tego robić jego stanowiska `Kierownik/Sprzedawca`. Prezentacja stanowiska i roli pracy pozostaje rozdzielna.

## 10. Migracja

Dzisiejsze ORDINARY są testowe zgodnie z wcześniejszą decyzją OWNERA przy T065 R4-01. Nie projektować rozbudowanej produkcyjnej migracji legacy, jeżeli Codex potwierdzi, że nie istnieją produkcyjne dane wymagające zachowania.

OCHRONA i jej historia nie mogą się zmienić.

## 11. Acceptance — minimum

1. Site A może mieć role `Kierownik`, `Sprzedawca`; Site B `Magazynier`, `Wózkowy`, `Kasjer` bez zmiany kodu domenowego.
2. Każdy nowy demand ORDINARY ma obowiązkową rolę Site.
3. Pracownik o stanowisku `Kierownik` nie kwalifikuje się automatycznie do demandu `Sprzedawca`.
4. Brak sprzedawcy może zakończyć PLAN istniejącym wynikiem/decyzją; solver nie wybiera kierownika jako remedium.
5. Po jawnym dopuszczeniu koordynatora ten sam kierownik może pokryć wskazaną rolę, ale w UI nadal pozostaje `Kierownik`.
6. External support jest alternatywą koordynatora, nie automatycznym skutkiem braku roli.
7. Historyczna rola pracy nie zmienia się po późniejszej edycji katalogu ról.
8. OCHRONA regression unchanged.

TASK_SCOPE:
- rota/domain.py
- rota/persistence/employee_repository.py
- rota/persistence/schema.py
- rota/planning/eligibility.py
- rota/planning/validator.py
- rota/planning/shift_catalog.py
- rota/application/durable_inputs.py
- api/routers/roster.py
- api/routers/site_config.py
- api/types.py
- frontend/src/screens/ControlPanel.tsx
- frontend/src/screens/SiteShiftCatalog.tsx
- frontend/src/screens/EmployeeDetail.tsx
- frontend/src/api/client.ts
- tests/

## 12. HOLD

IMPLEMENTATION HOLD do preimplementation PASS Codexa na dokładnym SHA tego briefu.

# ROTA-T065 — ORDINARY: role pracowników i rzeczywiste zmiany sklepowe

STATUS: PREIMPLEMENTATION — BRIEF ARCHITEKTA, IMPLEMENTATION HOLD UNTIL CODEX PASS

BASELINE: `main@8199143e414047447da69554d5c1558d7393d192`

SOURCE:
- finding Codexa `3d9600f`
- zweryfikowany scope `66181cf`
- re-check `c60f944`
- OWNER rulings 2026-09-13 zapisane w historii `BOARD.md`
- istniejący `SiteMembership`, `StandardShift`, `ShiftDemand`, `generate_catalog_demands` i jeden pipeline PLAN/REPLAN

## 1. Cel

T065 ma sprawić, żeby istniejący reżim `ORDINARY` rzeczywiście nadawał się do planowania pracy sklepu, bez budowania drugiego solvera, drugiego przebiegu planowania ani równoległej domeny grafiku.

T065 dodaje dwie rzeczy do istniejącego pipeline:

1. jawne role obsady sklepu: `KIEROWNIK` oraz `SPRZEDAWCA_ZALOGA`;
2. sklepowe zapotrzebowanie opisane rzeczywistym przedziałem czasu i dniem, a nie ochroniarską semantyką `D/N` ani biznesowym kodem zmiany.

Efektem PLAN/REPLAN pozostaje jeden `ScheduleVersion` tworzony przez ten sam solver.

## 2. Zasada nadrzędna — jeden solver i jedna prawda o obsadzie

T065 NIE tworzy:
- drugiego solvera dla sklepu;
- osobnego przebiegu dla kierowników i osobnego dla załogi;
- fallbacku „spróbuj kierownika jako sprzedawcę”;
- automatycznego szukania pracowników zewnętrznych;
- pętli „dodawaj ludzi aż grafik stanie się wykonalny”;
- drugiego generatora zapotrzebowania.

Role dzielą kandydatów w tym samym modelu solve. Wszystkie wymagane wystąpienia zmian trafiają jednocześnie do istniejącego PLAN/REPLAN, a ograniczenie roli tylko zawęża zbiór pracowników dopuszczonych do danego `ShiftDemand`.

Jeśli aktualna obsada jest niewystarczająca, program zatrzymuje się istniejącym biznesowym mechanizmem. Koordynator zmienia dane obsady, a następny zwykły PLAN/REPLAN pracuje na nowym stanie.

## 3. Zakres ról

T065 zna dokładnie dwie role sklepowe:

- `KIEROWNIK`
- `SPRZEDAWCA_ZALOGA`

Role są rozłączne jako wymagania obsady: demand wymagający kierownika może pokryć tylko osoba jawnie dopuszczona jako `KIEROWNIK`; demand załogi tylko osoba jawnie dopuszczona jako `SPRZEDAWCA_ZALOGA`.

Jedna osoba MOŻE być jednak jawnie dopuszczona do obu ról na tym samym obiekcie. To nie jest automatyczna zamienność ról.

Przypadek OWNERA: jeżeli koordynator chce użyć kierownika jako sprzedawcy, najpierw jawnie dopisuje tę osobę także do załogi. Dopiero późniejszy zwykły PLAN/REPLAN może użyć jej przy demandzie `SPRZEDAWCA_ZALOGA`.

### 3.1. Właściciel danych roli

Rola jest właściwością dopuszczenia pracownika na konkretnym obiekcie, nie globalną cechą `Employee`.

Obecne `SiteMembership` pozostaje jednym rekordem `(employee_id, site_id)` i nadal jest właścicielem członkostwa LOCAL/EXTERNAL, enabled, readiness i istniejących kwalifikacji. T065 ma dodać do tego członkostwa jawny zbiór dopuszczonych ról, a nie drugie `SiteMembership` dla tej samej osoby i obiektu.

Implementacja może użyć osobnej relacji persistence powiązanej z membershipem, ale kontrakt biznesowy jest jeden: dla `(employee_id, site_id)` istnieje zbiór `allowed_roles` zawierający zero, jedną albo obie role. Nie wolno modelować tego pojedynczym polem `role`, które uniemożliwi jawne dopisanie kierownika do załogi.

Zmiana `allowed_roles` jest materialną zmianą obsady i ma korzystać z istniejących mechanizmów invalidacji bieżącej decyzji/ponownego PLAN/REPLAN; nie tworzyć osobnej ścieżki lifecycle.

## 4. Skład ról jest per obiekt

System nie zakłada, że każdy sklep ma kierownika.

Legalne są m.in.:
- obiekt wymagający tylko `SPRZEDAWCA_ZALOGA`;
- obiekt wymagający `KIEROWNIK` + `SPRZEDAWCA_ZALOGA`;
- różne liczby osób wymaganych w danej roli w różnych przedziałach czasu.

Sklep referencyjny OWNERA ma czterech kierowników dostępnych do puli kierowniczej, ale liczba ta NIE jest domyślną regułą produktu.

## 5. Zmiana sklepowa jest przedziałem czasu, nie symbolem

Dla `ORDINARY` nie wprowadzamy sztywnego enumu ani biznesowej rodziny zmian typu:
- `D/N`;
- `RANO/POPOŁUDNIE/NOC`;
- `R1/R2/...`;
- `D1..D5/N1..N5`.

Powód: w sklepie mogą istnieć zmiany nakładające się i „środkowe”, a ich liczba nie jest z góry ograniczona.

Solver ma pracować na konkretnym wystąpieniu:

`start_datetime + end_datetime + required_role + required_primary_count`.

Przykład prezentacyjny: `Poniedziałek 05:00–12:00`, `Wtorek 10:00–18:00`.

Techniczny identyfikator rekordu/template może istnieć dla stabilnej referencji i historii, ale nie niesie semantyki biznesowej i nie może uruchamiać reguł planowania.

## 6. Konfiguracja powtarzalnych zmian obiektu

Panel sterowania → Obiekt ma pozwalać zdefiniować dla `ORDINARY` powtarzalne zapotrzebowanie jako rekord zawierający co najmniej:

- godzina początku;
- godzina końca;
- informacja o przejściu na następny dzień wynikająca jednoznacznie z przedziału/istniejącej semantyki czasu;
- aktywne dni tygodnia;
- wymagana rola;
- wymagana liczba osób.

Nie wymagamy od użytkownika kodu/nazwy zmiany.

T065 zachowuje obecną pełnogodzinną precyzję konfiguracji. Nie otwiera minutowych zmian.

Konfiguracja ma obsługiwać:
- zmiany 7–9 h;
- inne dodatnie długości wspierane przez istniejący `StandardShift`;
- zmiany przechodzące przez północ;
- kilka nakładających się zmian tego samego dnia;
- różne zmiany dla różnych dni tygodnia;
- sklepy działające 24/7 przez odpowiednio zdefiniowane pokrywające dobę zmiany.

„Sklep całodobowy” NIE oznacza automatycznie 24-godzinnej zmiany jednego pracownika. Produkt ma opisać rzeczywiste przedziały pracy skonfigurowane przez koordynatora.

## 7. Referencyjny sklep OWNERA — fixture, nie hardcode

Dla testu pionowego T065 przyjmujemy referencyjny układ:

- poniedziałek–piątek: `05:00–12:00` oraz `12:00–19:00`;
- sobota: `05:00–14:00`;
- niedziela: brak demandów;
- role: co najmniej `KIEROWNIK` i `SPRZEDAWCA_ZALOGA` w liczbach jawnie ustawionych w fixture.

Te godziny są wyłącznie fixture do dowodu działania. Nie wolno zaszyć ich w solverze, domenie ani domyślnej klasyfikacji `ORDINARY`.

## 8. Reuse istniejącego `StandardShift` i generatora

T065 ma rozwinąć istniejący właściciel konfiguracji czasu (`StandardShift` / katalog obiektu) i istniejący `generate_catalog_demands` zamiast tworzyć równoległy `StoreShift`, `StoreDemandGenerator` lub drugi pipeline.

Obecny backend już obsługuje arbitralną dodatnią pełnogodzinną długość przez `ShiftCatalogKind.OTHER/INNY` i `active_weekdays`.

Problemem do usunięcia jest obowiązkowa semantyka `ShiftKind.D/N` w `ORDINARY`.

Dla `OCHRONA` istniejące `D/N` pozostaje bez zmian.

Dla `ORDINARY`:
- rzeczywiste godziny + rola są źródłem znaczenia demandu;
- nie wolno sztucznie oznaczać `12:00–19:00` jako `N` ani `05:00–12:00` jako `D` tylko po to, żeby przejść przez istniejący enum;
- `DAY_ONLY-01`, `EMPLOYEE_ALLOWED_SHIFT_KINDS`, `EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS`, `allowed_shift_kind` external i inne reguły zależne od ochroniarskiego `D/N` nie mogą być przypadkiem aktywowane przez sklepowy przedział czasu.

Implementacja ma dokonać minimalnego rozdzielenia semantyki `D/N` od `ORDINARY` w istniejącym pipeline. Nie wolno osiągnąć tego przez skopiowanie generatora/eligibility/solvera.

## 9. `ShiftDemand` — zamrożona prawda dla solvera i historii

Każdy wygenerowany demand `ORDINARY` musi nieść wymaganie roli (`required_role`) razem z istniejącymi konkretnymi `start_datetime`, `end_datetime` i `required_primary_count`.

`required_role` jest snapshotem demandu i musi być zapisany w tej samej trwałej wersji danych, z której później odtwarzany jest `ScheduleVersion`.

Po akceptacji grafiku późniejsza zmiana:
- roli pracownika;
- katalogu zmian;
- godzin obiektu;
- wymaganej liczby osób

nie może retrospektywnie zmienić starego grafiku.

Historyczne grafiki są niemodyfikowalne — HARD.

## 10. Eligibility roli

Do istniejącej wspólnej bramki kwalifikacji dochodzi jedna deterministyczna reguła:

`demand.required_role ∈ membership.allowed_roles`.

Brak roli oznacza brak kwalifikacji do tego demandu.

Ta reguła obowiązuje identycznie LOCAL i EXTERNAL_SUPPORT. `EXTERNAL_SUPPORT` nie dostaje osobnej logiki ról ani osobnego solve.

Pozostałe istniejące HARD gate'y, które są rzeczywiście wspólne dla danego reżimu (enabled, absencje, urlopy, chorobowe itd.), pozostają w obecnych właścicielach.

## 11. External support — zero nowej automatyki

T065 nie zmienia biznesowego mechanizmu external.

Jeżeli bieżąca obsada nie wystarcza:
1. solver nie wyszukuje kandydatów;
2. solver nie uruchamia drugiego przebiegu;
3. system nie obserwuje rynku/zasobu external;
4. koordynator dopisuje osobę do obsady istniejącym flow;
5. nadaje jej jawnie właściwą rolę na tym obiekcie;
6. istniejący zakres dostępności external nadal ogranicza użycie tej osoby;
7. kolejny zwykły PLAN/REPLAN może ją wykorzystać.

Istniejący `membership_kind=EXTERNAL_SUPPORT` pozostaje tym samym membershipem i przechodzi tę samą bramkę roli co LOCAL.

Nie tworzyć `external_role_solver`, `external retry`, automatycznego rescue ani hidden helper synthesis.

## 12. Ogólne prawo pracy, nie profil Ochrona

`ORDINARY` nie dziedziczy ochroniarskiej semantyki 12/24 h ani specjalnych wyjątków D/N.

T065 ma zachować i stosować istniejące ogólne ograniczenia prawa pracy właściwe dla `ORDINARY`, w szczególności te już reprezentowane w jednym solverze/validatorze jako wspólne ograniczenia czasu pracy i odpoczynku. Nie wolno kopiować ich do osobnej implementacji sklepowej.

Jeżeli podczas implementacji okaże się, że konkretna wymagana przez sklep reguła ogólnego Kodeksu pracy nie ma jeszcze właściciela w produkcie, CC NIE implementuje jej „przy okazji” według własnej interpretacji. Zgłasza CONTRACT_GAP do Architekta/OWNERA. T065 nie jest zgodą na budowę nowego, kompletnego silnika prawa pracy.

Ochroniarskie reguły zależne od `D/N`, 24h rescue albo `OCHRONA` nie mogą zacząć obowiązywać dla `ORDINARY` tylko dlatego, że obecny kod historycznie współdzieli typy.

## 13. UI Panel sterowania

Dla `ORDINARY` Panel sterowania ma odzwierciedlać rzeczywistość sklepu:

### Obsada
- przy osobie widoczne są jej jawnie dopuszczone role na tym obiekcie;
- koordynator może dodać/usunąć `KIEROWNIK` i `SPRZEDAWCA_ZALOGA` bez tworzenia drugiego Employee i bez drugiego SiteMembership;
- osoba może mieć obie role;
- membership LOCAL/EXTERNAL pozostaje istniejącym pojęciem i nie jest zastępowany rolą.

### Obiekt / zmiany
- brak pola `Rodzaj = Dniówka/Nocka` dla `ORDINARY`;
- koordynator definiuje godziny, dni, rolę i liczbę wymaganych osób;
- UI nie wymaga symbolu zmiany;
- pusta konfiguracja `ORDINARY` nie może automatycznie udawać ochroniarskiej zmiany `06:00–18:00`;
- brak skonfigurowanego zapotrzebowania ma być jawnie niegotową konfiguracją zgodnie z istniejącym readiness/decision flow, a nie zerowym grafikiem uznanym za sukces.

`OCHRONA` zachowuje dotychczasowy UI/kontrakt D/N poza zmianami koniecznymi technicznie do współdzielenia komponentów.

## 14. PDF — osobny późniejszy Task

T065 NIE przebudowuje ochroniarskiego generatora PDF i NIE wciska sklepu w:
- `base_regime=12h/24h`;
- `D1..D5/N1..N5`;
- `D6+/N6+`;
- `S1/U*/C*`;
- rodzinę prezentacyjną D/N.

T065 ma wyłącznie zapisać wystarczającą historyczną prawdę (konkretne czasy + required_role + assignments), aby przyszły Task PDF mógł odtworzyć stary grafik bez czytania bieżącej konfiguracji.

Przyszły PDF `ORDINARY` będzie miał własną logikę prezentacji. OWNER ustalił już zasadę: w komórkach pokazuje konkretne godziny, np. `5–12`, `10–18`, zamiast mnożyć symbole zmian; jeden dokument może grupować `KIEROWNIK` i `SPRZEDAWCA/ZALOGA`.

Wspólna może pozostać niskopoziomowa infrastruktura eksportu i źródło tej samej zamrożonej `ScheduleVersion`. To nie jest zgoda na drugi solver.

## 15. Poza zakresem

Poza T065 pozostają:
- `UCZEN` / pracownik młodociany / praktyki;
- ekipa sprzątająca;
- sklepowy PDF i jego finalny layout;
- minutowa precyzja zmian;
- automatyczne zastępowanie ról;
- automatyczne pozyskiwanie external;
- nowy solver albo drugi przebieg solvera;
- nowe ogólne IAM/tenant/account mechanizmy;
- kompletna implementacja wszystkich możliwych wariantów polskiego prawa pracy;
- przebudowa Ochrony dla estetycznej unifikacji.

## 16. Migracja i kompatybilność

Zmiana ma być addytywna wobec istniejących danych Ochrony.

Wymagania:
- istniejące obiekty `OCHRONA` po migracji zachowują obecne zachowanie D/N;
- istniejące historyczne `ScheduleVersion` i legacy `ShiftDemand` nadal dają się odczytać;
- brak nowych pól w legacy danych nie może zostać arbitralnie zinterpretowany jako rola sklepowa;
- `ORDINARY` wymagający nowych ról/config ma failować jawnie jako niegotowy, a nie zgadywać defaults;
- migracja nie przepisuje starych grafików na nowe znaczenie.

## 17. Minimalne scenariusze acceptance

### T65-01 — dwie role w jednym solve

Dany jest obiekt `ORDINARY` z demandami `KIEROWNIK` i `SPRZEDAWCA_ZALOGA` w nakładającym się czasie oraz osobami przypisanymi tylko do swoich ról.

PLAN ma stworzyć jeden kandydat grafiku, w którym każdy demand pokrywa osoba z właściwą rolą. Nie ma dwóch wywołań solvera per rola.

### T65-02 — jawne dopisanie kierownika do załogi

Pracownik K ma początkowo tylko `KIEROWNIK`.

Demand `SPRZEDAWCA_ZALOGA` nie może zostać przez niego pokryty.

Koordynator jawnie dodaje K rolę `SPRZEDAWCA_ZALOGA` na tym samym Site, bez tworzenia drugiego Employee i drugiego SiteMembership.

Po zwykłym ponownym PLAN/REPLAN K staje się legalnym kandydatem do demandu załogi.

### T65-03 — brak ukrytej zamienności

Sama obecność wolnego kierownika nie naprawia braku sprzedawcy. Bez jawnego dopisania roli wynik pozostaje biznesowo niewykonalny/decyzyjny zgodnie z istniejącym flow.

### T65-04 — arbitrary / middle shifts

Fixture zawiera w tym samym tygodniu co najmniej trzy różne przedziały, w tym zmianę „środkową”, np. `05–12`, `10–18`, `12–19`.

Generator tworzy konkretne demandy bez wymagania kodów biznesowych i jeden solver je obsadza.

### T65-05 — zmiana przez północ / sklep 24/7

Fixture `ORDINARY` zawiera co najmniej jeden przedział przechodzący przez północ i zestaw zmian pozwalający opisać działanie obiektu przez pełną dobę.

Nie powstaje `N` tylko dlatego, że zmiana przebiega nocą. O legalności decydują konkretne czasy i istniejące ogólne reguły, nie ochroniarski ShiftKind.

### T65-06 — dni tygodnia

Fixture referencyjny generuje pon–pt `05–12` i `12–19`, sobotę `05–14`, a niedziela generuje zero demandów.

### T65-07 — external tą samą ścieżką

EXTERNAL_SUPPORT bez wymaganej roli nie może pokryć demandu. Po jawnej zmianie obsady/roli i przy spełnieniu istniejącego support window staje się kandydatem w tym samym solverze.

Brak drugiego solve/fallbacku external.

### T65-08 — historia

Po zaakceptowaniu grafiku zmień bieżące role membershipu i katalog zmian. Odczyt starej `ScheduleVersion` nadal zwraca pierwotne konkretne czasy i `required_role`; historyczny stan nie jest rekonstruowany z aktualnego membership/config.

### T65-09 — OCHRONA regression

Reprezentatywny istniejący D/N PLAN dla `OCHRONA` zachowuje wynik i reguły D/N po migracji T065.

### T65-10 — brak pustego sukcesu

`ORDINARY` bez kompletnej konfiguracji wymaganych ról/zapotrzebowania nie może zostać uznany za poprawny pusty grafik tylko dlatego, że generator zwrócił zero demandów.

## 18. Guardrails implementacyjne

CC ma najpierw użyć istniejących właścicieli kodu i dopiero potem minimalnie je rozszerzać:

- `rota/domain.py` — istniejące typy domenowe;
- `rota/planning/shift_catalog.py` — jeden generator demandów;
- `rota/planning/eligibility.py` — jedna wspólna bramka eligibility;
- istniejący solver — jeden model solve;
- istniejące repozytoria `SiteMembership` / profilu / schedule snapshot;
- istniejące API i ekran Panel sterowania;
- istniejące invalidation/PLAN/REPLAN lifecycle.

Zakazane bez powrotu do Architekta:
- `store_solver.py`;
- `ordinary_solver.py` jako drugi engine;
- `generate_store_demands()` obok istniejącego generatora;
- drugi endpoint PLAN dla sklepu;
- osobna tabela „store schedule”;
- automatyczny role fallback;
- hidden external synthesis;
- implementowanie PDF sklepu w T065;
- zastąpienie obecnego OCHRONA D/N ogólnym refactorem tylko dla „czystości architektury”.

Jeżeli minimalna implementacja ujawni rzeczywisty konflikt kontraktów, CC zatrzymuje się i wpisuje finding na BOARD zamiast rozszerzać scope.

## 19. Literalny TASK_SCOPE

Dozwolone są wyłącznie zmiany konieczne do pionowego T065 w następujących obszarach:

1. `tasks/ROTA-T065/**`
2. `rota/domain.py`
3. `rota/planning/shift_catalog.py`
4. `rota/planning/eligibility.py`
5. istniejący solver/validator tylko tam, gdzie jest to konieczne do wykonania role gate i usunięcia fałszywej semantyki D/N z `ORDINARY`
6. istniejące persistence/migrations/repositories dla `SiteMembership`, katalogu zmian i `ShiftDemand` snapshot
7. istniejące API durable inputs / site profile / roster potrzebne do nowych pól
8. `frontend/src/screens/ControlPanel.tsx`
9. `frontend/src/screens/SiteShiftCatalog.tsx`
10. odpowiadające istniejące typy/API client frontend
11. testy jednostkowe/integracyjne/E2E bez budowania nowej infrastruktury testowej

Poza scope bez nowej zgody Architekta pozostają:
- produkcyjny generator PDF i `PrintSettings` poza ewentualnym compile-only dostosowaniem typu, bez zmiany zachowania;
- osobne nowe pipeline'y planowania;
- ogólne refaktory folderów/modułów;
- nowy framework reguł;
- uczniowie i sprzątanie;
- nowe algorytmy external.

## 20. Acceptance techniczne

T65-A1 — persistence potrafi zapisać jednego `(employee, site)` z obiema rolami bez drugiego SiteMembership.

T65-A2 — `ShiftDemand` `ORDINARY` zachowuje konkretne datetimes i immutable `required_role` w snapshot/reload.

T65-A3 — role gate działa przed wyborem pracownika i identycznie dla LOCAL/EXTERNAL, z zachowaniem istniejących dodatkowych warunków external.

T65-A4 — `ORDINARY` nie wymaga `ShiftKind.D/N` do wygenerowania/obsadzenia nowych demandów i nie uruchamia przez przypadek DAY_ONLY-N ani site-rule D/N tylko z powodu godziny.

T65-A5 — `OCHRONA` nadal używa D/N i przechodzi reprezentatywną regresję.

T65-A6 — konfiguracja UI zapisuje co najmniej start/end/weekdays/required_role/required_count i odtwarza te dane po reloadzie.

T65-A7 — kilka nakładających się definicji czasu jest legalne i daje niezależne demandy.

T65-A8 — zmiana przechodząca przez północ zachowuje właściwe end datetime.

T65-A9 — zmiana ról/config po utworzeniu wersji nie zmienia starego snapshotu.

T65-A10 — instrumentacja/repro potwierdza jedno wywołanie istniejącego solve dla scenariusza z dwiema rolami; nie ma per-role drugiego przebiegu.

## 21. Preimplementation review Codexa

Przed implementacją Codex ma wykonać wąski re-check dokładnego SHA briefu. Bez szerokiego audytu całego repo.

Codex ma sfalsyfikować przede wszystkim:
1. czy proponowany `allowed_roles` da się wprowadzić bez złamania unikalnego `SiteMembership` i bez duplikowania membership;
2. czy `required_role` może być trwale snapshottowane razem z istniejącym `ShiftDemand`;
3. czy usunięcie obowiązkowej semantyki D/N z nowych `ORDINARY` demandów może zostać wykonane w istniejącym generatorze/eligibility/solverze bez drugiej ścieżki;
4. czy historyczne i bieżące OCHRONA D/N pozostają kompatybilne;
5. czy TASK_SCOPE wystarcza do jednego pionowego przejścia UI → persistence → generate → solve → snapshot/reload;
6. czy brief nie wymusza niejawnie przebudowy PDF.

PASS Codexa oznacza zgodę techniczną na implementację dokładnego briefu. Nie daje zgody na rozszerzenie produktu poza ten dokument i nie zastępuje decyzji OWNERA.
# ROTA-T065 — ORDINARY: role pracowników i rzeczywiste zmiany sklepowe

STATUS: PREIMPLEMENTATION — BRIEF ARCHITEKTA PO FALSYFIKACJI, IMPLEMENTATION HOLD UNTIL CODEX PASS

BASELINE: `main@8199143e414047447da69554d5c1558d7393d192`

SOURCE:
- finding Codexa `3d9600f`
- zweryfikowany scope `66181cf`
- re-check `c60f944`
- Work falsification `tests_r1.txt` + uzupełnienie `tests_r2.txt` z 2026-09-13
- OWNER rulings 2026-09-13 zapisane w historii `BOARD.md`
- istniejący `SiteMembership`, `StandardShift`, `ShiftDemand`, `generate_catalog_demands`, PLAN/REPLAN, solver/validator, manual correction/deviation/audit lifecycle

## 1. Cel

T065 ma sprawić, żeby istniejący reżim `ORDINARY` nadawał się do planowania pracy sklepów bez budowania drugiego solvera, drugiego przebiegu planowania ani równoległej domeny grafiku.

T065 dodaje wyłącznie brakujące pojęcia biznesowe:

1. jawne role obsady sklepu: `KIEROWNIK` oraz `SPRZEDAWCA_ZALOGA`;
2. wymaganie roli na konkretnym istniejącym zapotrzebowaniu czasowym.

T065 NIE buduje obsługi zmian 7–9 h. `StandardShift`, `ShiftCatalogKind.OTHER/INNY`, `active_weekdays`, przejście przez północ i istniejący generator już obsługują takie przedziały. T065 ma je wykorzystać.

Produkt nie jest projektowany pod jeden konkretny sklep. Sklep OWNERA służy wyłącznie jako realistyczny fixture i źródło przykładów operacyjnych. Kontrakt ma obsłużyć również sklepy 24/7 i inne konfiguracje godzin.

Efektem PLAN/REPLAN pozostaje ten sam `ScheduleVersion` tworzony przez istniejący engine i solver.

## 2. Zasada nadrzędna — jeden istniejący pipeline

T065 NIE tworzy:
- drugiego solvera dla sklepu;
- osobnego przebiegu dla kierowników i osobnego dla załogi;
- fallbacku „spróbuj kierownika jako sprzedawcę”;
- automatycznego szukania pracowników zewnętrznych;
- pętli „dodawaj ludzi aż grafik stanie się wykonalny”;
- drugiego generatora zapotrzebowania;
- drugiego silnika prawa pracy;
- drugiego mechanizmu odchyleń/manual override/audytu.

Role zawężają kandydatów w istniejącym pipeline. Wszystkie demandy trafiają do normalnego engine PLAN/REPLAN.

UWAGA po falsyfikacji Worka: „jeden pipeline” NIE oznacza „dokładnie jedno wywołanie `solve()`”. Obecny engine ma już własne kolejne etapy/próby. T065 nie może ich usuwać ani przerabiać tylko po to, żeby spełnić sztuczny licznik. Zakaz dotyczy wyłącznie dodania nowych przebiegów per rola, sklepowego retry, role fallbacku i osobnego external rescue.

Jeśli aktualna obsada jest niewystarczająca, program korzysta z istniejącego mechanizmu wyniku/decyzji. Koordynator zmienia dane obsady, a następny zwykły PLAN/REPLAN pracuje na nowym stanie.

## 3. Zakres ról

T065 zna dokładnie dwie role sklepowe:

- `KIEROWNIK`
- `SPRZEDAWCA_ZALOGA`

Demand wymagający kierownika może pokryć tylko osoba jawnie dopuszczona jako `KIEROWNIK`; demand załogi tylko osoba jawnie dopuszczona jako `SPRZEDAWCA_ZALOGA`.

Jedna osoba MOŻE być jawnie dopuszczona do obu ról na tym samym obiekcie. To nie jest automatyczna zamienność ról.

Jeżeli koordynator chce użyć kierownika jako sprzedawcy, najpierw jawnie dopisuje tę osobę także do załogi istniejącym flow obsady. Dopiero późniejszy zwykły PLAN/REPLAN może użyć jej przy demandzie `SPRZEDAWCA_ZALOGA`.

### 3.1. Właściciel danych roli

Rola jest właściwością dopuszczenia pracownika na konkretnym obiekcie, nie globalną cechą `Employee`.

Obecne `SiteMembership` pozostaje jednym rekordem `(employee_id, site_id)` i nadal jest właścicielem członkostwa LOCAL/EXTERNAL, enabled, readiness i istniejących kwalifikacji. T065 dodaje do tego członkostwa jeden zbiór dopuszczonych ról, zamiast tworzyć drugie `SiteMembership` dla tej samej osoby i obiektu.

Kontrakt biznesowy: dla `(employee_id, site_id)` istnieje `allowed_roles` zawierające zero, jedną albo obie role. Nie wolno modelować tego pojedynczym polem, które uniemożliwiłoby jawne dopisanie kierownika do załogi.

Nie wolno równolegle zapisywać tych samych ról w `SiteRule`; powstałyby dwa źródła prawdy.

Zmiana `allowed_roles` jest materialną zmianą obsady i korzysta z istniejącego lifecycle invalidacji/ponownego PLAN/REPLAN. Nie tworzyć osobnej ścieżki.

## 4. Skład ról jest per obiekt

System nie zakłada, że każdy sklep ma kierownika.

Legalne są m.in.:
- obiekt wymagający tylko `SPRZEDAWCA_ZALOGA`;
- obiekt wymagający `KIEROWNIK` + `SPRZEDAWCA_ZALOGA`;
- różne liczby osób wymaganych w danej roli w różnych przedziałach czasu.

Sklep referencyjny OWNERA ma czterech kierowników dostępnych do puli kierowniczej, ale liczba ta jest wyłącznie fixture i NIE jest regułą produktu.

## 5. Zmiana jest konkretnym przedziałem czasu

Dla `ORDINARY` prawdą biznesową solvera jest konkretne wystąpienie:

`start_datetime + end_datetime + required_role + required_primary_count`.

Przykłady: `Poniedziałek 05:00–12:00`, `Wtorek 10:00–18:00`, `22:00–06:00` następnego dnia.

Nie wolno budować nowej domeny kodów zmian tylko dlatego, że Ochrona historycznie używa `D/N`. W sklepie mogą istnieć zmiany nakładające się i „środkowe”, więc liczba możliwych przedziałów nie jest z góry ograniczona.

OWNER dopuszcza ewentualne pomocnicze oznaczenie kolejności `1/2/3` = pierwsza/druga/trzecia zmiana, jeśli okaże się przydatne dla UI lub kompatybilności istniejącego kodu. Taki numer:
- jest opcjonalnym metadanym/prezentacją;
- nie jest źródłem godzin;
- nie jest źródłem kwalifikacji;
- nie uruchamia reguł prawa pracy;
- nie może ograniczać liczby rzeczywistych przedziałów w obiekcie.

Techniczny identyfikator rekordu/template może istnieć dla stabilnej referencji i historii, ale nie niesie semantyki prawa pracy.

## 6. Konfiguracja powtarzalnych zmian obiektu — reuse

Panel sterowania → Obiekt dla `ORDINARY` korzysta z istniejącego katalogu czasu i pozwala zdefiniować powtarzalne zapotrzebowanie zawierające co najmniej:

- godzina początku;
- godzina końca;
- przejście na następny dzień zgodne z istniejącą semantyką czasu;
- aktywne dni tygodnia;
- wymagana rola;
- wymagana liczba osób.

T065 zachowuje obecną pełnogodzinną precyzję konfiguracji. Nie otwiera minutowych zmian.

Istniejący mechanizm już obsługuje:
- dodatnie długości inne niż 12/24 h przez `ShiftCatalogKind.OTHER/INNY`;
- zmiany przechodzące przez północ;
- kilka nakładających się zmian tego samego dnia;
- różne zmiany dla różnych dni tygodnia.

T065 ma te możliwości REUSE, a nie implementować ponownie.

Sklep 24/7 opisuje się przez odpowiednio zdefiniowane przedziały pokrywające dobę. Nie oznacza to automatycznie 24-godzinnej zmiany jednego pracownika.

## 7. Sklep referencyjny — wyłącznie fixture

Dla jednego testu pionowego można użyć realistycznego układu:

- poniedziałek–piątek: `05:00–12:00` oraz `12:00–19:00`;
- sobota: `05:00–14:00`;
- niedziela: brak demandów;
- role ustawione jawnie w fixture.

Te godziny NIE są profilem produktu, defaultem systemu ani ograniczeniem solvera. T065 musi również przejść scenariusz nietypowy/24h, aby udowodnić brak hardcode.

## 8. D/N, INNY i nowe ORDINARY

`ShiftCatalogKind.OTHER/INNY` już istnieje i oznacza kategorię długości inną niż 12/24 h. Nie jest rolą, nie jest reżimem ORDINARY i nie zastępuje `ShiftKind.D/N`.

Dla `OCHRONA` obecne `D/N` pozostaje bez zmian.

Dla nowych demandów `ORDINARY`:
- rzeczywiste godziny + rola są źródłem znaczenia biznesowego;
- godzina nocna nie może sama tworzyć ochroniarskiej semantyki `N`;
- `DAY_ONLY-01`, D/N-specific SiteRule ani D/N-specific external restriction nie mogą zostać przypadkiem aktywowane tylko dlatego, że sklep pracuje rano/wieczorem/nocą.

KRYTYCZNE po falsyfikacji Worka: nie wolno użyć legacy `shift_kind=None` jako niejawnego nowego znaczenia „ORDINARY bez symbolu”. Obecny `classify_demand()` potrafi dla legacy `None` odtworzyć D/N na podstawie bieżącego katalogu, więc historia zależałaby od późniejszej konfiguracji.

Implementacja ma w istniejącym modelu jednoznacznie odróżnić:
1. legacy demand wymagający istniejącego fallbacku klasyfikacji;
2. nowy demand ORDINARY, którego semantyka nie może być rekonstruowana z bieżącego katalogu.

Brief nie narzuca konkretnego nowego enuma/tabeli. Wymaga minimalnego rozwiązania w istniejącym modelu i jednego właściciela klasyfikacji używanego przez solver i validator. Nie wolno stworzyć drugiego klasyfikatora sklepowego.

## 9. `ShiftDemand` — snapshot roli i czasu

Każdy nowy demand `ORDINARY` niesie `required_role` razem z istniejącymi `start_datetime`, `end_datetime` i `required_primary_count`.

`required_role` przechodzi CAŁĄ istniejącą drogę:

`generator → PlanPreview → wybór → ScheduleVersion/ShiftDemand persistence → reload/history`.

Nie wystarczy dodać pola wyłącznie do końcowej tabeli. Istniejące serializery preview/schedule, semantic keys i material-change invalidation muszą przenosić nowe znaczenie tam, gdzie już ręcznie przenoszą pola demandu/membershipu.

Nie tworzyć nowego magazynu historii ról ani snapshotu całej dawnej puli `allowed_roles`. Do zachowania faktu, w jakiej roli wykonano konkretną zapisaną zmianę, wystarcza wersjonowany demand z `required_role` + istniejące `Assignment.covers_demand_id`.

Po akceptacji grafiku późniejsza zmiana membershipu albo katalogu nie może retrospektywnie zmieniać starego grafiku. Historyczne grafiki pozostają niemodyfikowalne.

## 10. Eligibility roli

Do istniejącej wspólnej bramki kwalifikacji dochodzi jedna deterministyczna reguła:

`demand.required_role ∈ membership.allowed_roles`.

Brak wymaganej roli oznacza brak kwalifikacji do tego demandu.

Ta reguła obowiązuje identycznie LOCAL i EXTERNAL_SUPPORT. Nie ma osobnej logiki ról dla external.

Pozostałe istniejące gate'y pozostają w swoich obecnych właścicielach.

## 11. External support — zero nowej automatyki

T065 nie zmienia biznesowego mechanizmu external.

Jeżeli bieżąca obsada nie wystarcza:
1. solver nie wyszukuje kandydatów;
2. nie powstaje dodatkowy przebieg sklepu/external;
3. system nie obserwuje rynku/zasobu external;
4. koordynator dopisuje osobę do obsady istniejącym flow;
5. nadaje jej właściwą rolę na tym obiekcie;
6. istniejący zakres dostępności nadal ogranicza użycie tej osoby;
7. kolejny zwykły PLAN/REPLAN może ją wykorzystać.

Stare ograniczenia external oparte na `allowed_shift_kind=D/N` nie mogą być automatycznie zamienione na „brak ograniczenia”, bo rozszerzałoby to dopuszczenie bez decyzji koordynatora. Dla nowych ORDINARY nie tworzymy takich D/N-specific ograniczeń. Jeżeli istnieją legacy ORDINARY z takim ustawieniem, mają zostać jawnie rozpoznane jako legacy/niezgodna konfiguracja do świadomej korekty, a nie cicho zmigrowane.

## 12. Prawo pracy i odchylenia — REUSE, nie nowa domena

T065 NIE tworzy nowych mechanizmów prawa pracy.

Zasada OWNERA jest taka sama jak w Ochronie:
- automatyczny solver ma przestrzegać obowiązujących HARD constraints dla danego reżimu;
- koordynator może użyć istniejącej Manual Correction tam, gdzie produkt już dopuszcza świadome odstępstwo;
- istniejący mechanizm deviation/action trail/audyt zapisuje jego decyzję;
- T065 nie kopiuje validatora, nie tworzy `store_law_engine`, nie tworzy osobnej ścieżki override.

Dla sklepów stosowany jest właściwy skonfigurowany system czasu pracy (w praktyce m.in. równoważny system czasu pracy), ale T065 nie koduje jednego sklepu ani jednego harmonogramu jako prawa produktu.

W szczególności T065 nie ustanawia nowego uproszczonego HARD typu „<=40 h w każdych ruchomych 7 dniach”. Wymiar, odpoczynki dobowe/tygodniowe, rozliczenie okresu, praca w dniach wolnych oraz istniejące zasady manual deviation mają pozostać w obecnych właścicielach produktu.

Jeżeli istniejąca reguła była zamrożona wyłącznie dla Ochrony, nie wolno rozszerzać jej na ORDINARY tylko dlatego, że kod współdzieli typy. Jeżeli istniejąca reguła ogólna już działa dla ORDINARY, T065 jej nie implementuje ponownie.

Szczególna kontrola po falsyfikacji: `THIRD-CONSECUTIVE-SHIFT-01` obecnie działa także dla ORDINARY, mimo że historycznie pochodzi z T058. CC nie może samodzielnie ani kopiować tej reguły do nowego modułu, ani usuwać jej globalnie. Ma najpierw sprawdzić obowiązujący kontrakt T058 i istniejący podział reżimów. Jeśli jest to ochrona-specyficzny leak do ORDINARY, korekta ma być minimalnym zawężeniem istniejącej reguły, nie nową implementacją prawa pracy. Jeśli kontrakty są sprzeczne, STOP + BOARD finding.

Analogicznie `WEEKLY-REST-01` nie może zostać uznany za „już ogólny” bez sprawdzenia istniejącego kontraktu — Work wykazał, że obecnie jest OCHRONA-only. T065 nie ma samodzielnie budować brakującego silnika odpoczynku.

## 13. UI — Panel sterowania i miesięczny grafik

### Obsada
- przy osobie widoczne są jej jawnie dopuszczone role na tym obiekcie;
- koordynator może dodać/usunąć `KIEROWNIK` i `SPRZEDAWCA_ZALOGA` bez drugiego Employee i drugiego SiteMembership;
- osoba może mieć obie role;
- LOCAL/EXTERNAL pozostaje istniejącym pojęciem.

### Obiekt / zmiany
- dla ORDINARY konfiguracja opiera się na godzinach/dniach/roli/liczbie osób;
- UI nie wymaga biznesowego kodu zmiany;
- opcjonalne `1/2/3` może być wyłącznie etykietą kolejności, jeśli reuse istniejącego komponentu tego wymaga;
- pusta konfiguracja ORDINARY nie może automatycznie udawać ochroniarskiej zmiany `06:00–18:00`;
- brak skonfigurowanego zapotrzebowania nie może dawać pustego sukcesu.

### `MonthlyPlanning` / preview

T065 MUSI objąć istniejący renderer miesięcznego grafiku/podglądu w zakresie minimalnym do nowych demandów. Work wykazał, że obecny renderer opiera label na `kind` i dla demandu bez D/N może pokazać `?`.

Dla ORDINARY komórka/podgląd ma pokazywać rzeczywiste godziny zmiany (np. `5–12`, `10–18`) i potrzebne dane roli, bez tworzenia drugiego ekranu planowania.

OCHRONA zachowuje istniejący renderer D/N.

## 14. PDF — osobny późniejszy Task

T065 NIE przebudowuje ochroniarskiego generatora PDF i NIE wciska sklepu w:
- `base_regime=12h/24h`;
- `D1..D5/N1..N5`;
- `D6+/N6+`;
- `S1/U*/C*`;
- rodzinę prezentacyjną D/N.

Istniejący PDF może po T065 nie obsługiwać nowych ORDINARY demandów. To świadoma granica dostawy, a nie powód do sztucznego mapowania sklepu na D/N.

T065 zapisuje wystarczającą historyczną prawdę (konkretne czasy + required_role + assignments), aby osobny późniejszy Task PDF mógł zbudować wydruk sklepu z własną logiką prezentacji.

## 15. Poza zakresem

Poza T065 pozostają:
- `UCZEN` / pracownik młodociany / praktyki;
- ekipa sprzątająca;
- sklepowy PDF i jego finalny layout;
- minutowa precyzja zmian;
- automatyczne zastępowanie ról;
- automatyczne pozyskiwanie external;
- nowy solver albo nowe role-specific przebiegi;
- nowy silnik prawa pracy;
- nowy framework deviation/manual override;
- kompletna implementacja wszystkich wariantów prawa pracy;
- przebudowa Ochrony dla estetycznej unifikacji.

## 16. Migracja i kompatybilność

Zmiana ma być addytywna wobec istniejących danych Ochrony i historii ORDINARY.

Wymagania:
- OCHRONA zachowuje obecne zachowanie D/N;
- historyczne `ScheduleVersion` i legacy `ShiftDemand` nadal dają się odczytać;
- legacy `shift_kind=None` zachowuje swój dotychczasowy kontrakt i nie staje się nowym znaczeniem ORDINARY;
- brak nowych pól w legacy danych nie może zostać arbitralnie zinterpretowany jako rola sklepowa;
- nowy ORDINARY bez kompletu wymaganych ról/config ma failować jawnie jako niegotowy;
- migracja nie przepisuje starych grafików na nowe znaczenie;
- zmiana katalogu wpływa na generowanie nowego zapotrzebowania zgodnie z istniejącym lifecycle; nie powstaje synchronizator nadpisujący demandy zaakceptowanej historii.

## 17. Minimalne scenariusze acceptance

### T65-01 — dwie role w jednym istniejącym pipeline

ORDINARY ma nakładające się demandy `KIEROWNIK` i `SPRZEDAWCA_ZALOGA` oraz osoby dopuszczone tylko do swoich ról.

PLAN ma stworzyć jeden kandydat grafiku, w którym każdy demand pokrywa osoba z właściwą rolą. Test nie zakłada liczby wewnętrznych wywołań `solve()`; dowodzi braku dodatkowego przebiegu per rola.

### T65-02 — jawne dopisanie kierownika do załogi

K ma początkowo tylko `KIEROWNIK`. Demand `SPRZEDAWCA_ZALOGA` nie może zostać przez niego pokryty.

Koordynator jawnie dodaje K rolę `SPRZEDAWCA_ZALOGA` na tym samym Site, bez drugiego Employee/SiteMembership. Po zwykłym ponownym PLAN/REPLAN K staje się kandydatem do demandu załogi.

### T65-03 — brak ukrytej zamienności

Sama obecność wolnego kierownika nie naprawia braku sprzedawcy. Bez jawnego dopisania roli nie ma fallbacku.

### T65-04 — istniejące INNY / middle shifts

Fixture zawiera co najmniej trzy różne przedziały, np. `05–12`, `10–18`, `12–19`.

Test dowodzi REUSE istniejącego generatora/INNY i braku nowego generatora/kodu biznesowego zmian.

### T65-05 — przez północ / 24/7

Fixture ORDINARY zawiera przedział przechodzący przez północ i zestaw zmian opisujący pełną dobę.

Godzina nocna nie aktywuje ochroniarskiej semantyki N. Nie powstaje drugi solver.

### T65-06 — historia preview → ScheduleVersion

`required_role` przechodzi przez preview, wybór, persist, reload i historyczny odczyt. Zmiana bieżącego membership/config nie zmienia starego demandu.

### T65-07 — external tą samą ścieżką

EXTERNAL_SUPPORT bez wymaganej roli nie może pokryć demandu. Po jawnej zmianie roli i przy spełnieniu istniejącego support window staje się kandydatem w tym samym pipeline. Brak dodatkowego external retry.

### T65-08 — MonthlyPlanning

Nowy ORDINARY demand jest pokazany w istniejącej siatce/podglądzie jako konkretne godziny, nie `?` i nie wymuszony D/N.

### T65-09 — OCHRONA regression

Reprezentatywny istniejący D/N PLAN OCHRONA zachowuje wynik i reguły D/N.

### T65-10 — brak pustego sukcesu

ORDINARY bez kompletnej konfiguracji wymaganych ról/zapotrzebowania nie może zostać uznany za poprawny pusty grafik.

### T65-11 — brak duplikacji prawa/override

Scenariusz z istniejącym HARD/deviation potwierdza, że T065 używa dotychczasowego solver/validator/manual-correction/deviation trail. Nie istnieje drugi sklepowy validator ani osobny store override.

## 18. Guardrails implementacyjne

CC ma najpierw użyć istniejących właścicieli kodu i dopiero potem minimalnie je rozszerzać:

- `rota/domain.py` — istniejące typy domenowe;
- `rota/planning/shift_catalog.py` — jeden generator demandów;
- `rota/planning/eligibility.py` — jedna wspólna bramka eligibility;
- istniejący engine/solver/validator;
- istniejące preview/schedule persistence i semantic keys;
- istniejący `SiteMembership` / profil;
- istniejące API i ekrany ControlPanel/SiteShiftCatalog/MonthlyPlanning;
- istniejące invalidation/PLAN/REPLAN/manual correction/deviation lifecycle.

Zakazane bez powrotu do Architekta:
- `store_solver.py`;
- `ordinary_solver.py` jako drugi engine;
- `generate_store_demands()`;
- `store_validator.py`;
- drugi endpoint PLAN;
- osobna tabela „store schedule”;
- osobny mechanizm deviations/override;
- automatyczny role fallback;
- hidden external synthesis;
- implementowanie PDF sklepu w T065;
- zastąpienie OCHRONA D/N ogólnym refactorem tylko dla estetyki.

Jeżeli minimalna implementacja ujawni konflikt zamrożonych kontraktów, CC zatrzymuje się i wpisuje finding na BOARD zamiast rozszerzać scope.

## 19. Literalny TASK_SCOPE

Dozwolone są wyłącznie zmiany konieczne do pionowego T065 w istniejących właścicielach:

1. `tasks/ROTA-T065/**`
2. `rota/domain.py`
3. `rota/planning/shift_catalog.py`
4. `rota/planning/eligibility.py`
5. istniejący engine/solver/validator — tylko minimalne połączenie roli i właściwe rozdzielenie legacy D/N vs new ORDINARY
6. istniejące persistence/migrations/repositories dla `SiteMembership`, PlanPreview, `ShiftDemand` i lifecycle snapshot
7. istniejące API durable inputs / site profile / roster / schedule DTO
8. `frontend/src/screens/ControlPanel.tsx`
9. `frontend/src/screens/SiteShiftCatalog.tsx`
10. `frontend/src/screens/MonthlyPlanning.tsx`
11. istniejący `EmployeeDetail` wyłącznie w zakresie koniecznym do niewprowadzania nowych sprzecznych ustawień D/N dla ORDINARY
12. odpowiadające istniejące typy/API client frontend
13. testy jednostkowe/integracyjne/E2E bez nowej infrastruktury testowej

Poza scope bez nowej zgody Architekta pozostają:
- produkcyjny generator PDF i `PrintSettings` poza compile-only dostosowaniem typu, bez nowej logiki sklepu;
- osobne pipeline'y planowania;
- ogólne refaktory;
- nowy framework reguł;
- uczniowie i sprzątanie;
- nowe algorytmy external;
- budowa nowego subsystemu prawa pracy.

## 20. Acceptance techniczne

T65-A1 — persistence zapisuje jednego `(employee, site)` z obiema rolami bez drugiego SiteMembership i bez równoległego SiteRule ról.

T65-A2 — nowy `ShiftDemand` ORDINARY zachowuje concrete datetimes + immutable `required_role` przez preview/persist/reload/history.

T65-A3 — role gate działa identycznie dla LOCAL/EXTERNAL, z zachowaniem istniejących dodatkowych gate'ów.

T65-A4 — new ORDINARY ma jednoznaczną semantykę odróżnioną od legacy `shift_kind=None`; późniejsza zmiana katalogu nie przeklasyfikowuje starego demandu.

T65-A5 — OCHRONA nadal używa istniejącego D/N i przechodzi reprezentatywną regresję.

T65-A6 — UI zapisuje start/end/weekdays/required_role/required_count i odtwarza je po reloadzie, wykorzystując istniejący katalog/INNY.

T65-A7 — kilka nakładających się definicji czasu daje niezależne demandy bez nowego generatora.

T65-A8 — zmiana przechodząca przez północ zachowuje właściwe end datetime.

T65-A9 — MonthlyPlanning/preview pokazuje rzeczywiste godziny dla ORDINARY, nie `?` i nie sztuczne D/N.

T65-A10 — instrumentation/repro potwierdza brak DODATKOWEGO solve/pipeline PER ROLA; nie wymaga globalnego `solve_calls == 1`.

T65-A11 — istniejące mechanizmy solver/validator/manual correction/deviation/action trail są reużyte; brak drugiego sklepowego mechanizmu prawa/override.

## 21. Preimplementation review Codexa

Codex ma wykonać wąski re-check dokładnego SHA briefu po tej korekcie.

Ma sfalsyfikować przede wszystkim:
1. czy `allowed_roles` i `required_role` są jedynymi nowymi pojęciami biznesowymi, bez duplikowania membership/SiteRule;
2. czy T065 naprawdę reużywa `StandardShift`/INNY/generator zamiast budować obsługę godzin ponownie;
3. czy rozróżnienie legacy `shift_kind=None` od new ORDINARY może zostać wykonane minimalnie w istniejącym modelu;
4. czy rola przechodzi przez cały preview → selection → ScheduleVersion/reload bez nowego magazynu historii;
5. czy engine zachowuje swoje istniejące etapy, a T065 nie dodaje role-specific retry;
6. czy MonthlyPlanning i schedule DTO wystarczają do prezentacji konkretnych godzin bez drugiego ekranu;
7. czy istniejące D/N-specific SiteRule/external nie zostają po cichu rozszerzone ani wyzerowane dla legacy;
8. czy T065 reużywa istniejące prawo/validator/manual deviation/audit zamiast je kopiować;
9. czy PDF pozostaje świadomie osobnym taskiem.

PASS Codexa oznacza zgodę techniczną na implementację dokładnego briefu. Nie daje zgody na rozszerzenie produktu poza ten dokument i nie zastępuje decyzji OWNERA.
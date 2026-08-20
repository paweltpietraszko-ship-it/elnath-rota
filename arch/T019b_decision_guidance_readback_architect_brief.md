# Handoff brief dla architekta — ROTA-T019b Pamięć materialnych decyzji i zmian koordynatora

STATUS: OWNER INTENT — READY FOR ARCHITECT CONTRACT

DATE: 2026-08-20

TASK_ID: ROTA-T019b

BASE_BRANCH: main

BASE_SHA: 9618477f6014fad63699a154b04730e2b8ff1db2

RELATED:
- T005 / istniejący Decision Ledger i Site Memory;
- T013 / końcowy coordinator-facing `DECISION_REQUIRED`;
- T019 / analityka WorkBalance — osobny, równoległy read model;
- T021 / przyszły UI konsumujący gotowe API aplikacyjne.

## 1. Skorygowana intencja właściciela

T019b nie jest już wyłącznie małym readbackiem „ostatniego
`DECISION_REQUIRED`”. Przegląd tego pomysłu ujawnił szerszą lukę: część
materialnych decyzji koordynatora trafia do append-only pamięci, a część jest
zapisywana jako zwykły stan bieżący i nadpisuje poprzednią wartość.

Docelowa zasada właściciela:

> Każda materialna decyzja lub zmiana koordynatora dotycząca grafiku ma trafić
> do pamięci programu w sposób pozwalający później ustalić co, kto i kiedy
> zmienił, od kiedy zmiana obowiązywała oraz jaki był stan przed i po zmianie.

Po pół roku koordynator ma móc odpowiedzieć między innymi na pytanie:
„od kiedy istnieje decyzja, że ten pracownik ma tylko dniówki, kto ją zapisał
i jak brzmiała dobrowolnie dodana uwaga?”.

## 2. Jawne decyzje właściciela

1. Historia materialnych działań koordynatora nie może być nadpisywana.
2. Nie tworzymy obowiązku wpisywania uzasadnienia.
3. Koordynator może dobrowolnie dodać krótką uwagę, np.:
   - „na prośbę pracownika”;
   - „wskazanie lekarskie”;
   - „wymóg zleceniodawcy”.
4. Brak uwagi nie może blokować ani zmieniać skutku operacji.
5. Nie zapisujemy jako decyzji:
   - wewnętrznych prób i retry solvera;
   - niewybranych stanów pośrednich;
   - automatycznych „decyzji systemu”.
6. Koordynator widzi końcowy rezultat i własne materialne działania, nie drogę
   solvera do rezultatu.
7. Historia ma być zapisana strukturalnie i wyszukiwalnie. Nie wolno tworzyć
   osobnego pliku na każdą decyzję ani zmuszać UI do przeglądania surowych
   plików lub ściany tekstu.
8. T019b nie tworzy UI. Dostarcza trwałość i read model potrzebne później T021.
9. T019 może być projektowane i implementowane równolegle; nie ma zależności
   technicznej T019 -> T019b ani T019b -> T019.

## 3. Fakty sprawdzone na BASE_SHA

### 3.1 Istniejąca pamięć decyzji jest rzeczywistą historią, ale ma wąski zakres

`rota/persistence/decision_ledger.py` zapisuje `DecisionRecord` w liniowym,
append-only łańcuchu `(site_id, rule_id)`. `decision_records` i relacje mają
ochronę przed update/delete, a `rota/application/memory_read.py` udostępnia
historię i provenance reguł.

Ta pamięć prawidłowo zachowuje decyzje należące do jej obecnego kontraktu,
między innymi tworzenie i zmianę SiteRuleVersion. T012 wykorzystuje ją również
dla audytowego `REST_OVERRIDE_RECORD`.

Nie jest to jednak ogólny dziennik wszystkich materialnych zmian wejść
planowania.

### 3.2 Potwierdzony reproduktor luki: `Employee.day_only`

`rota/application/durable_inputs.py::update_employee()` wywołuje
`rota/persistence/employee_repository.py::save_employee()`.

`save_employee()` wykonuje UPSERT i przy konflikcie zastępuje bieżące
`day_only`. Tabela `employees` przechowuje jedynie aktualne `true/false`; nie
zachowuje autora zmiany, czasu zmiany, poprzedniej wartości ani dobrowolnej
uwagi. `active_from`/`active_to` nie są historią `DAY_ONLY` i zgodnie z frozen
spec nie wolno użyć ich do takiej interpretacji.

W rezultacie program potrafi dziś odczytać aktualne `Employee.day_only`, lecz
nie odpowie, od kiedy ani dlaczego wartość obowiązuje.

Datowany `EMPLOYEE_DAY_ONLY_N_EXCEPTION` jest innym bytem: przechodzi przez
SiteRuleVersion/DecisionRecord i jego historia istnieje. Nie naprawia to braku
historii samego włączenia lub wyłączenia `Employee.day_only`.

### 3.3 `DECISION_REQUIRED` jest ulotnym pytaniem, nie decyzją koordynatora

`rota/planning/decision_guidance.py::build_decision_payload()` tworzy końcowy
`DecisionRequiredPayload`. `rota/application/plan_ops.py::plan_month()` i
`replan()` zwracają go synchronicznie w `PlanningResult`, ale nigdzie go nie
utrwalają.

Po odświeżeniu lub restarcie nie istnieje aplikacyjny readback bieżącego,
nierozwiązanego pytania. Ponowne uruchomienie PLAN nie jest odczytem
poprzedniego wyniku: może pracować na zmienionych danych i dać inny rezultat.

`DECISION_REQUIRED` nie ma być wpisem pod tytułem „system podjął decyzję”. Może
być zachowany jako bieżące nierozwiązane pytanie/kontekst, a późniejsza
materialna czynność koordynatora może zostać z nim jawnie powiązana. Nie wolno
zgadywać takiego związku wyłącznie z kolejności czasowej dwóch operacji.

## 4. Obowiązkowy predesign audit architekta

Przed zamrożeniem implementacji architekt ma zinwentaryzować publiczne,
mutujące operacje `rota.application.*` i przygotować jawną macierz:

- operacja;
- materialna dla grafiku: TAK/NIE;
- istniejący sposób trwałości: append-only/versioned/current-value;
- czy pełna historia jest już odtwarzalna;
- brakujące pola: actor, recorded_at, effective_from, before/after, optional
  note, affected entity, site/month/ScheduleVersion;
- czy operacja może być odpowiedzią na otwarte `DECISION_REQUIRED`.

Macierz musi objąć reprezentatywnie co najmniej następujące klasy, ale
architekt nie może uznać tej listy za zamkniętą bez sprawdzenia całej warstwy
aplikacyjnej:

- ograniczenia pracownika, w tym `Employee.day_only`;
- konfigurację Obiektu i katalog zmian wpływający na planowanie;
- Membership oraz dostępność/nieobecności;
- target hours i inne wejścia planowania;
- decyzje reguł i datowane wyjątki;
- external support i training/readiness, jeśli zmiana wpływa na obsadę;
- wybór wariantu, ręczne korekty, REPLAN, restore i finalize;
- jawne akceptacje odstępstw/Deviation.

Nie każda operacja musi dostać nową tabelę. Celem audytu jest wykrycie klas,
w których historia już istnieje, oraz tych, w których stan jest dziś tylko
nadpisywany.

## 5. Kontrakt prezentacyjny read modelu

Historia może być kompletna, ale domyślny odczyt nie może być ścianą tekstu.
Architekt ma zaprojektować minimalny aplikacyjny read model umożliwiający T021:

1. listę krótkich wpisów, np.:
   `12.03.2027 | Jan Kowalski | Tylko dniówki: NIE -> TAK | od 01.04.2027`;
2. filtrowanie co najmniej po Site, pracowniku/innym dotkniętym bycie, rodzaju
   zmiany, koordynatorze i zakresie dat;
3. przejście do szczegółu zawierającego stan przed/po, daty, aktora i
   opcjonalną uwagę;
4. odróżnienie stanu aktualnego/otwartego od nieaktualnej historii bez jej
   usuwania;
5. odczyt bieżącego nierozwiązanego `DECISION_REQUIRED` po restarcie;
6. pokazanie jawnego powiązania pytanie -> czynność koordynatora, jeżeli takie
   powiązanie zostało zapisane.

UI nie importuje `rota.persistence` ani `rota.planning` i nie składa historii
samodzielnie. Otrzymuje gotowe, deterministyczne DTO/read modele z
`rota.application.*`.

## 6. Granice zakresu

T019b nie może:

- zmieniać treści ani reguł budowania `DecisionRequiredPayload` z T013;
- zmieniać solvera, jego retry ani kolejności fallbacków;
- zapisywać prób pośrednich solvera;
- tworzyć obowiązkowego pola uzasadnienia;
- przechowywać jednej decyzji w osobnym pliku;
- udawać historii przez ponowne uruchomienie PLAN;
- automatycznie uznawać późniejszą zmianę za odpowiedź na wcześniejszy
  `DECISION_REQUIRED` bez jawnego identyfikatora/kontekstu;
- projektować finalnego UI T021;
- zamieniać Rota w ogólny workflow engine lub system kadrowo-płacowy.

## 7. ARCHITECTURE_PROPOSALS — jawne, niewiążące propozycje Codexa

### P1. Rozdzielić historię działań człowieka od bieżącego pytania solvera

Obecne zachowanie: `DecisionRecord` opisuje wybrane decyzje dotyczące reguł,
a `DECISION_REQUIRED` znika po zwróceniu wyniku.

Propozycja: utrzymywać append-only historię materialnych działań koordynatora
oraz osobny stan bieżącego nierozwiązanego pytania. Po jawnie powiązanej
czynności potrzebny snapshot/referencja pytania może pozostać provenance tej
czynności, ale nie jako „decyzja systemu”.

Korzyść: czytelny model odpowiedzialności i możliwość audytu po czasie.

Trade-off: trzeba jednoznacznie zdefiniować lifecycle otwartego pytania i
atomowość jego powiązania z czynnością.

### P2. Nie przeciążać istniejącego `DecisionRecord`, jeśli nie pasuje domenowo

Obecne zachowanie: `DecisionRecord` jest związany z `(site_id, rule_id)`,
łańcuchem reguły i często SiteRuleVersion. Nie każda zmiana, np.
`Employee.day_only`, jest wersją reguły Obiektu.

Propozycja: architekt ma porównać rozszerzenie istniejącego ledgeru z małym,
ustrukturyzowanym journalem materialnych działań. Nie wolno sztucznie tworzyć
fikcyjnych SiteRule tylko po to, aby wykorzystać obecną tabelę.

Korzyść: brak fałszywego modelowania i jeden spójny read model ponad
istniejącą historią reguł oraz nowymi brakującymi klasami.

Trade-off: osobny journal oznacza dodatkową trwałość i wymaga jednoznacznego
uniknięcia duplikatów między nim a istniejącym ledgerem.

### P3. Jedna operacja użytkownika = jeden logiczny wpis

Propozycja: jeżeli jedna czynność aplikacyjna zmienia kilka technicznych
wierszy, read model powinien prezentować ją jako jedną materialną zmianę z
listą dotkniętych bytów, a nie jako serię niskopoziomowych logów SQL.

Korzyść: koordynator widzi własne działanie, nie szczegóły implementacji.

Trade-off: granice transakcji aplikacyjnych muszą jednoznacznie wyznaczać
tożsamość logicznej operacji.

## 8. Pytania techniczne dla architekta

1. Które operacje z obowiązkowej macierzy już mają wystarczającą historię, a
   które wymagają nowej trwałości?
2. Czy istniejący Decision Ledger można bezpiecznie rozszerzyć bez łamania
   jego semantyki SiteRule, czy potrzebny jest odrębny journal z ujednoliconym
   read modelem?
3. Jak zapewnić atomowość: materialna zmiana i jej wpis pamięci albo powstają
   razem, albo nie powstaje żadne z nich?
4. Jak identyfikować jedną logiczną operację i jej before/after bez kopiowania
   całych snapshotów, jeśli wystarczą jednoznaczne referencje?
5. Jak przechować bieżące nierozwiązane `DECISION_REQUIRED` i jawnie powiązać
   je z późniejszą czynnością bez zapisu prób pośrednich i bez zgadywania?
6. Jakie minimalne DTO i filtry powinno udostępnić `rota.application.*` dla
   T021?
7. Jaki jest literalny TASK_SCOPE, migracja istniejącej bazy i macierz testów
   obejmująca restart, dwa Site, współdzielonego Employee oraz brak przecieków?

## 9. Wymagany wynik pracy architekta

1. Udokumentowana macierz istniejących mutujących operacji aplikacyjnych.
2. Zamrożona decyzja o granicy istniejącego Decision Ledger i ewentualnej nowej
   trwałości.
3. Zamrożony kontrakt `tasks/ROTA-T019b/brief.md` z literalnym TASK_SCOPE i
   testami bug classes, nie tylko pojedynczym reproduktorem `DAY_ONLY`.
4. Standardowa bramka:
   Codex preimplementation audit -> CC implementacja -> backend.py + pełna
   suita -> Codex implementation audit -> finalny gate architekta przed merge.

## 10. Relacja do T019, T020 i T021

T019 pozostaje niezależnym taskiem analityki WorkBalance i może ruszyć bez
czekania na T019b. T020 (wydruk grafiku) nie ma obecnie wskazanej zależności od
T019b. T021 konsumuje gotowe read modele T019 oraz T019b, ale nie projektuje
ich trwałości ani nie obchodzi warstwy aplikacyjnej.

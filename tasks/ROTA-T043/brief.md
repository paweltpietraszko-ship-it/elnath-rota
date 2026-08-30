# ROTA-T043 — Wiarygodny Symulator Koordynatora i bramka zaufania do testów

Status: **PROPOZYCJA CODEX DO NIEZALEŻNEGO PRZEGLĄDU — BEZ IMPLEMENTACJI**

Base: `main@c25c73e0332158bae703109e770f3cf83fd970a7`

Autor briefu: Codex jako niezależny tester. CC napisał T038/T039 i celowo nie
projektuje własnej poprawki. Źródłem zlecenia jest
`arch/REQUEST_SYMULATOR_INDEPENDENT_DIAGNOSIS_2026-08-30.md` na
`docs/symulator-repair-diagnosis-request@f248c07d3e6f65164080863b47b694118477574b`.

## 1. Wynik dla OWNERA

Obecny Symulator nie daje wiarygodnej odpowiedzi na pytanie „czy Rota tworzy
sensowny grafik”. Uruchamia prawdziwy backend, ale:

1. sam deklaruje, że **nie ocenia poprawności wyniku** i odsyła do odrzuconego
   przez OWNERA benchmarku (`tests/property/coordinator_simulator.py:4-6`);
2. po `DECISION_REQUIRED` może dopisać czterech kolejnych LOCAL, więc obiekt
   pięcioosobowy staje się dziewięcioosobowym
   (`tests/property/test_coordinator_simulator.py:109-123`);
3. nie ma wariantu podwójnej obsady i 10-osobowej załogi — każdy obecny wiersz
   katalogu wymaga jednej osoby (`coordinator_simulator.py:59-73`);
4. pomija L4 przed pierwszym PLAN, mimo że T041 już naprawił ten przepływ
   (`coordinator_simulator.py:220-242` oraz
   `test_coordinator_simulator.py:152-156`);
5. zapisuje kalendarz bezpośrednio do repozytorium, zamiast wykonać produkcyjną
   operację backendową (`coordinator_simulator.py:254-256`);
6. zwykły pytest nadpisuje śledzony historyczny raport T038
   (`test_coordinator_simulator.py:44-47,184-217`);
7. raportuje tylko listę użytych identyfikatorów. Nie pokazuje godzin każdego
   pracownika, targetu, różnicy godzin, walidacji, typu LOCAL/EXTERNAL ani
   rzeczywistego użycia wsparcia (`test_coordinator_simulator.py:193-212`);
8. za poprawny uznaje każdy wynik bez wyjątku/HTTP 5xx. Nierówny albo
   bezsensowny, lecz technicznie zapisany grafik pozostaje zielony
   (`test_coordinator_simulator.py:220-229`).

Na exact base wykonano jeden mały przebieg kontrolny, bez zapisu raportu:

```powershell
python -c "from tests.property.test_coordinator_simulator import _run_one_seed; import pprint; pprint.pp(_run_one_seed(0))"
```

Wynik: D/N 12 h, 720 h, 5 LOCAL, wszyscy dostępni, `FEASIBLE`, użyto wszystkich
pięciu. Przebieg trwał około 44 s. Nie rozstrzyga to sprawiedliwości, bo obecny
driver wyrzuca szczegóły przypisań i godzin przed zbudowaniem raportu.

T043 ma naprawić narzędzie i od razu użyć go do wytworzenia pierwszego
czytelnego raportu. Sam napis „testy PASS” nie jest kryterium odbioru.

## 2. Zamrożone decyzje OWNERA

### 2.1 Symulator odtwarza pracę koordynatora

- osobna SQLite `:memory:` dla każdego scenariusza;
- ustawienia przez istniejące produkcyjne endpointy/operacje backendowe;
- prawdziwy assembler, PLAN, `select_candidate()` z produkcyjnym `validate()`
  oraz REPLAN;
- bez ręcznego tworzenia wynikowych `Assignment`, demandów i wzorcowego
  grafiku;
- bez danych użytkownika, sieci i `rota_dev.db`;
- generator ustawia wejścia, naciska PLAN/REPLAN i raportuje wynik. Nie kopiuje
  do testu reguł odpoczynku, urlopu, L4 ani solvera.

### 2.2 Wielkość załogi wynika z rodzaju obiektu, nie z wygody solvera

- pojedyncza obsada całodobowa: dokładnie **5 LOCAL**;
- podwójna obsada całodobowa: dokładnie **10 LOCAL**;
- dotyczy również krótkiego miesiąca; symulator nie „zwalnia” pracownika w
  lutym;
- po `DECISION_REQUIRED` nie wolno dodać szóstego–dziewiątego LOCAL;
- obecne `ceil(monthly_hours / 160)` nie jest kontraktem i ma zniknąć z decyzji
  o liczebności załogi. Godziny zapotrzebowania nadal wylicza produkcyjny
  katalog, ale nie mogą niezależnie wylosować dowolnego rosteru.

### 2.3 Target godzin jest prawdziwym wejściem koordynatora

- każdy LOCAL dostaje jawny `target_hours` przez produkcyjny endpoint;
- EXTERNAL_SUPPORT nie dostaje targetu;
- dla zamrożonego miesiąca raportu `2026-09-01` target pełnego etatu wynosi
  **176 h**;
- wartość nie jest udziałem `720 / 5` ani stałą `168`/`160`;
- runtime testu nie korzysta z Internetu. Miesiąc i wartość są zamrożoną
  fixture z podanym źródłem. Państwowa Inspekcja Pracy opisuje wzór z art. 130
  KP, a urzędowa tabela dla 2026 r. podaje dla września 176 h:
  https://katowice.pip.gov.pl/aktualnosci/sierpien-2026-r-jak-ustalic-wymiar-czasu-pracy
  oraz
  https://sosnowiec.praca.gov.pl/strona-glowna/-/asset_publisher/Qat7ebECUfDp/content/id/56152826/pop_up.

### 2.4 Nieobecności

- w danym scenariuszu planowego urlopu nie ma albo ma go najwyżej jedna osoba;
- planowy urlop to jeden zakres do 14 dni kalendarzowych; backend wylicza jego
  godziny, a raport sprawdza tylko, że łączna wartość nie przekracza
  zaakceptowanego limitu 120 h;
- L4 ma losową/deterministycznie seedowaną długość od 0 do 21 dni
  kalendarzowych i może być znane przed PLAN albo pojawić się przed REPLAN;
- symulator zapisuje rodzaj i zakres nieobecności. Nie wpisuje do solvera
  oznaczeń `U`/`C` i nie liczy sam 8/12/16-godzinnych „zmian nieobecności”.

### 2.5 Wsparcie zewnętrzne jest reakcją, nie ukrytą nadwyżką

- syntetyczna osoba `SIM-EXTERNAL-*` może istnieć jako przypisanie
  `EXTERNAL_SUPPORT` do obiektu, bez targetu, ale przed pierwszym PLAN **nie ma
  aktywnego okna** i solver nie może jej użyć;
- po rzeczywistym `DECISION_REQUIRED` driver odczytuje produkcyjny zapis
  decyzji. Okno wolno dodać tylko wtedy, gdy produkcyjne
  `unblocking_options` naprawdę proponuje skonfigurowanie wsparcia dla tej
  osoby;
- wtedy symulator przyjmuje domyślną zgodę koordynatora, dodaje jedno okno
  przez istniejący endpoint z `responds_to_decision_required_id` i ponownie
  naciska PLAN;
- bez takiej propozycji nie dodaje okna, nie dopisuje LOCAL i uczciwie kończy
  scenariusz jako `DECISION_REQUIRED`;
- raport osobno pokazuje: osoba istniała / okna nie było / propozycja była lub
  nie / okno utworzono / czy wsparcie trafiło do grafiku.

### 2.6 Brak grafiku może być prawidłowym wynikiem

`DECISION_REQUIRED` nie jest automatycznie błędem. Jest poprawnym, użytecznym
wynikiem, jeżeli scenariusz rzeczywiście blokuje obsadę i payload zawiera
konkretny demand, blocker albo opcję działania. Całkowicie pusty payload jest
błędem narzędzia lub produktu i nie może przejść jako PASS.

## 3. Jedno zadanie, trzy checkpointy

Nie tworzymy osobnego tasku „napraw narzędzie”, potem „uruchom narzędzie”, a
potem „uwierz narzędziu”. T043 jest jednym testowym taskiem z trzema małymi,
kolejnymi checkpointami:

1. **A — prawdziwe wejścia i działania koordynatora;**
2. **B — niezależne, proste orakle oraz raport dla OWNERA;**
3. **C — mała bramka zaufania do istniejących testów, bez przepisywania całej
   suity.**

Każdy checkpoint ma osobny logiczny commit. Nie wolno w T043 poprawiać kodu
produktu. Jeżeli B ujawni defekt produktu, zachować JSON i reprodukcję, zgłosić
go i nie „pomagać” solverowi zmianą scenariusza.

## 4. Checkpoint A — poprawiony Symulator

### 4.1 Produkcyjna ścieżka

Wszystkie poniższe działania przechodzą przez te same endpointy, co frontend:

- utworzenie Site i katalogu zmian;
- ustawienie każdego dnia kalendarza przez `/api/workspace/calendar/day`
  (usunąć bezpośrednie `save_calendar_day()`);
- utworzenie pracowników, LOCAL/EXTERNAL membership i targetów LOCAL;
- zapis nieobecności/reguł pracownika;
- PLAN, odczyt decyzji, ewentualne okno wsparcia, ponowny PLAN;
- wybór kandydata, ponowny odczyt miesiąca/analityki;
- zmiana wejścia i REPLAN dla scenariuszy REPLAN.

`TestClient` i SQLite `:memory:` są dozwolone: to proces in-memory, lecz
wykonuje prawdziwy router, aplikację, bazę, assembler, solver i validator. Nie
wolno monkeypatchować wyniku PLAN, kandydata, walidacji ani analityki.

### 4.2 Zamknięta macierz scenariuszy

Macierz jest deterministyczna. Losowanie może wybierać datę/osobę w obrębie
rodziny, ale nie może decydować, czy dana rodzina w ogóle wystąpi. Każdy raport
zawiera co najmniej:

| ID | Obiekt | Załoga | Zdarzenie |
|---|---|---:|---|
| T43-S01 | D/N po 12 h, pojedyncza obsada | 5 LOCAL | wszyscy dostępni |
| T43-S02 | D/N po 12 h, pojedyncza obsada | 5 LOCAL | jedna osoba, urlop do 14 dni |
| T43-S03 | D/N po 12 h, pojedyncza obsada | 5 LOCAL | L4 przed pierwszym PLAN, 1–21 dni |
| T43-S04 | jedna zmiana 24 h, pojedyncza obsada | 5 LOCAL | wszyscy dostępni |
| T43-S05 | jedna zmiana 24 h, pojedyncza obsada | 5 LOCAL | urlop albo L4 |
| T43-S06 | D/N po 12 h, podwójna obsada | 10 LOCAL | wszyscy dostępni |
| T43-S07 | D/N po 12 h, podwójna obsada | 10 LOCAL | jedna osoba na urlopie i opcjonalne L4 innej osoby |
| T43-S08 | OCHRONA, granica miesiąca | 5 LOCAL | prawdziwy kontekst końca poprzedniego miesiąca |
| T43-S09 | D/N po 12 h | 5 LOCAL | aktywna reguła pracownika/DAY_ONLY |
| T43-S10 | D/N po 12 h | 5 LOCAL | rzeczywisty brak nocnej obsady; oczekiwane niepuste `DECISION_REQUIRED` |
| T43-S11 | wybrany poprawny grafik | 5 albo 10 LOCAL | nowe L4 po wyborze → produkcyjny REPLAN |
| T43-S12 | wybrany poprawny grafik | 5 albo 10 LOCAL | zmiana targetu lub parametru obiektu → REPLAN może ułożyć miesiąc od nowa |

`WEEKDAY_12H_WEEKEND_24H` z T039 można zachować jako dodatkową rodzinę, ale nie
zamiast S01–S12. Odrzuconego `SPLIT_NIGHT_12_8` nie przywracać.

### 4.3 Koszt uruchomienia

- zwykły test celowany uruchamia najwyżej po jednym krótkim scenariuszu z
  każdej zmienionej klasy;
- pełna macierz S01–S12 jest jawnym poleceniem raportowym, uruchamianym raz na
  finalnym SHA, a nie częścią każdego `pytest`;
- pełna regresja całego repo nie jest wymagana i nie wolno jej uruchamiać bez
  osobnej zgody OWNERA;
- timeout i seed muszą być zapisane. Nie wolno ratować timeoutu przez dodanie
  pracowników.

## 5. Checkpoint B — co Symulator ma naprawdę sprawdzać

Symulator nie buduje drugiego solvera ani drugiego validatora. Ma pięć prostych
orakli pochodzących bezpośrednio z decyzji OWNERA i produkcyjnych odczytów.

### B1. Zamknięty świat

- roster ma dokładnie 5 albo 10 LOCAL;
- po każdym PLAN/REPLAN nadal ma dokładnie tę samą liczbę LOCAL;
- w grafiku nie ma obcej osoby, obcego Site, obcego demandu ani godzin typu
  INNY;
- EXTERNAL może wystąpić wyłącznie we własnym aktywnym oknie utworzonym po
  propozycji.

### B2. Produkcyjna poprawność

Każdy zwrócony kandydat używany w raporcie przechodzi przez produkcyjne
`select_candidate()`, a następnie produkcyjny odczyt/revalidate. Symulator nie
odtwarza COVERAGE, REST, NIGHT-STREAK, urlopu ani L4 własnym kodem.

### B3. Godziny i sprawiedliwość widoczne dla człowieka

Raport pokazuje dla każdego LOCAL:

- target godzin;
- efektywny target zwrócony przez produkcyjną analitykę;
- faktycznie zaplanowane godziny;
- liczbę i długości zmian;
- różnicę względem najmniej i najbardziej obciążonego LOCAL.

Dla trzech czystych baz bez absencji — S01, S04 i S06 — 720 h / 5 albo
1440 h / 10 daje po 144 h na każdego. Jeżeli produkcyjne HARD nie wprowadzają
innej przeszkody, nierówny rozdział w tych bazach jest FAIL. Dla scenariuszy z
urlopem, L4 albo regułą pracownika raport pokazuje rozkład i produkcyjne
effective target, ale nie zgaduje własnego „idealnego” grafiku.

### B4. Uczciwy `DECISION_REQUIRED`

- payload nie jest całkowicie pusty;
- raport pokazuje blokujące demandy, osoby/warunki, load blocker i opcje;
- jeżeli brak grafiku jest oczekiwanym skutkiem S10, jest opisany jako
  poprawne wykrycie warunków, nie awaria;
- jeśli S01/S04/S06 bez absencji zwraca `DECISION_REQUIRED`, zapisać failure
  JSON i zgłosić defekt produktu. Nie dodawać ludzi ani nie osłabiać danych.

### B5. REPLAN reaguje na zmianę

Raport zachowuje zestaw godzin i przypisań przed zmianą oraz po REPLAN. Pokazuje
co zmieniono w wejściu i czy backend ponownie zbilansował cały dostępny miesiąc.
Nie wymusza ręcznie konkretnego grafiku.

### 5.1 Artefakty

Jawne uruchomienie pełnej macierzy tworzy dwa nowe artefakty na exact SHA:

- `tasks/ROTA-T043/round_01/tests/coordinator_report.md` — polski raport dla
  OWNERA;
- `tasks/ROTA-T043/round_01/tests/coordinator_report.json` — pełne wejście,
  wynik, seed i dane do odtworzenia.

Każdy nieudany przypadek ma osobny failure JSON i gotową komendę reprodukcji
jednego scenariusza. Zwykły pytest zapisuje wyłącznie do `tmp_path` i nigdy nie
dotyka historycznych raportów T038/T039.

## 6. Checkpoint C — bramka zaufania do testów

Nie przepisujemy mechanicznie około 1100 testów i nie kasujemy wszystkich
mocków. Mock jest poprawny przy testowaniu mapowania DTO albo kontrolowanego
błędu. Nie może jednak być jedynym dowodem zachowania widocznego dla
koordynatora.

### 6.1 Klasy dowodu

Testy używane w końcowym raporcie trzeba sklasyfikować:

- `REAL_UI` — prawdziwy browser + frontend + router + baza + produkt;
- `REAL_API` — TestClient + prawdziwy router + SQLite + aplikacja/solver;
- `REAL_APPLICATION` — prawdziwy assembler/solver/validate bez HTTP;
- `UNIT_OR_ADAPTER` — ręczny stan albo mock, ważny lokalnie, ale nie dowodzi
  działania programu jako całości;
- `BENCHMARK_ONLY` — testuje benchmark/generator, nie produktowy wynik.

Liczba testów z dwóch ostatnich klas nie może być przedstawiana OWNEROWI jako
„program sprawdzony”.

### 6.2 Minimalna mapa zaufania

W ramach T043 należy sprawdzić istniejące testy dotyczące:

- PLAN/wyboru kandydata;
- sprawiedliwego podziału i H24;
- urlopu/L4 przed PLAN i przed REPLAN;
- nakładających się demandów;
- EXTERNAL_SUPPORT i okna;
- zmiany katalogu/targetu i REPLAN;
- ostrzeżenia oraz wyniku widocznego w UI.

Jeżeli zachowanie ma dziś wyłącznie test mockowany, ręcznie zbudowany
`PlanningState` albo fixture z `benchmarks/**`, trzeba **dodać lub przerobić
najmniejszy istniejący test** na prawdziwy pion. Nie duplikować niższych
macierzy. `tests/support/t009_fixtures.py` i trzy testy benchmarków należy
sklasyfikować, nie automatycznie usuwać.

### 6.3 Prawdziwy browser

Jeden mały Playwright flow ma przejść bez stubowania sieci przez realny ekran:

1. koordynator widzi obiekt i właściwą liczbę osób;
2. zaznacza jedną nieobecność/ustawia target;
3. naciska PLAN;
4. widzi status oraz godziny/ostrzeżenie odpowiadające odczytowi API.

To sprawdza wiring UI. Nie uruchamia wszystkich scenariuszy solvera w
przeglądarce. Do diagnozy tego pionu Codex używa zainstalowanego
`playwright-interactive`; trwałym testem pozostaje zwykły Playwright.

### 6.4 Kalibracja na znanych błędach

Nowa bramka musi wykazać, że potrafi być czerwona. Na oddzielnym tymczasowym
worktree, bez commitowania mutacji produktu, auditor wykonuje trzy małe próby:

1. przywrócenie starego błędu H24 `occupancy=2*x` traktowanego jak Boolean;
2. wyłączenie terminu równego podziału dla brakującego targetu;
3. przywrócenie starego geometrycznego podwójnego liczenia legalnie
   nakładających się demandów.

Odpowiedni prawdziwy pion musi paść dla każdej mutacji i przejść na finalnym
SHA. Jeżeli pozostaje zielony, test nie chroni tej klasy błędu i ma zostać
poprawiony. To jest mała, ręczna kalibracja mutation testing — bez dodawania
ciężkiego narzędzia do każdej sesji.

## 7. Dlaczego nie instalujemy teraz wszystkiego

Aktualne źródła prowadzą do następującej decyzji:

- Playwright zaleca sprawdzanie zachowania widocznego dla użytkownika zamiast
  szczegółów implementacji — używamy go dla jednego prawdziwego pionu:
  https://playwright.dev/docs/best-practices
- Hypothesis stateful potrafi losować sekwencje działań i zmniejszać nieudany
  przypadek. Jest dobrym następnym rozszerzeniem po ustabilizowaniu realnych
  strategii danych, ale dodanie go teraz mogłoby tylko szybciej generować
  nierealne obiekty: https://hypothesis.readthedocs.io/en/latest/stateful.html
- Schemathesis dobrze wykrywa 5xx i błędy kontraktu OpenAPI, także w
  sekwencjach, lecz nie rozstrzyga, czy pięcioosobowy grafik jest sprawiedliwy.
  Nie jest częścią T043:
  https://schemathesis.readthedocs.io/en/latest/guides/stateful-testing/
- `mutmut` wymaga na Windows WSL i szeroki przebieg byłby kosztowny. T043 używa
  trzech kontrolowanych mutacji; ewentualną automatyzację oceniamy dopiero po
  wyniku: https://mutmut.readthedocs.io/en/latest/
- branch coverage jest mapą miejsc nieodwiedzonych, nie oraklem poprawności.
  Nie jest bramką PASS: https://coverage.readthedocs.io/en/latest/

Badania z 2025–2026 pokazują ten sam problem, który wystąpił w Rocie: test
napisany po przeczytaniu błędnej implementacji może kopiować jej założenia;
wysokie coverage i mutation score nie gwarantują wykrywania realnych błędów,
gdy kod wejściowy już może być wadliwy. Dlatego orakle T043 pochodzą z decyzji
OWNERA, prawdziwych incydentów i relacji między przebiegami, nie z obecnego
kształtu funkcji:

- https://arxiv.org/abs/2603.23443
- https://conf.researchr.org/details/issta-2026/issta-2026-research-papers/2/Do-Coverage-and-Mutation-Scores-of-LLM-Generated-Test-Suites-Correlate-With-Their-Eff
- https://arxiv.org/abs/2501.12862
- https://arxiv.org/abs/2506.18315

## 8. PREIMPLEMENTATION REDUCTION GATE

| Element | SOURCE | Konieczność | Redukcja |
|---|---|---|---|
| roster 5/10 | jawna decyzja OWNER | wejście widoczne dla OWNERA | stała rodziny scenariusza, bez algorytmu headcount |
| target 176 | OWNER + art. 130/PIP | prawdziwe wejście miesiąca | jedna zamrożona fixture, brak sieci runtime |
| osoba EXTERNAL bez okna | OWNER | pozwala produkcji realnie zaproponować okno | istniejący membership i endpoint; bez nowej encji |
| reakcja na propozycję | OWNER | odtwarza decyzję koordynatora | istniejący decisions read + support-window endpoint |
| godziny/spread | OWNER fairness + T041 | ujawnia bzdury widoczne ręcznie | odczyt assignments/analityki, bez drugiego solvera |
| produkcyjne validate | istniejący owner | legalność kandydata | select/revalidate, bez kopii walidatora |
| Markdown + JSON | prośba OWNER | czytelność i reprodukcja | jeden model danych, dwa renderery |
| jeden UI vertical | luka między API i ekranem | sprawdza realne kliknięcie | jeden flow, nie macierz browserowa |
| 3 mutacje kontrolne | znane incydenty | dowód, że test umie upaść | tymczasowy worktree, bez nowej zależności |

Usunięte z propozycji:

- nowy solver, validator albo checker reguł HARD;
- dowolna obsada 4–9 i reaktywne zatrudnianie LOCAL;
- domyślne aktywne wsparcie przed PLAN;
- liczenie urlopu/L4 w generatorze;
- sieć w trakcie testu;
- masowa migracja 1100 testów;
- pełna regresja jako automatyczny rytuał;
- Hypothesis/Schemathesis/mutmut jako nowe stałe zależności T043;
- zmiany `rota/**`, `api/**`, `frontend/src/**` i `benchmarks/**`.

## 9. TASK_SCOPE

TASK_SCOPE:
- tests/property/coordinator_simulator.py
- tests/property/test_coordinator_simulator.py
- frontend/e2e/t043-coordinator-confidence.spec.ts
- README.md
- tasks/ROTA-T043/brief.md
- tasks/ROTA-T043/round_01/tests/coordinator_report.md
- tasks/ROTA-T043/round_01/tests/coordinator_report.json
- tasks/ROTA-T043/round_01/tests/failures/**
- tasks/ROTA-T043/round_01/tests/tests_r*.txt

`frontend/e2e/t043-coordinator-confidence.spec.ts` i katalog `failures/` są
nowe tylko jeśli rzeczywiście potrzebne. Nie tworzyć frameworka, helperów ani
manifestu poza tym zakresem. Jeżeli istniejący e2e helper wystarcza, użyć go.

Zabronione:

- `rota/**`, `api/**`, `frontend/src/**`, `benchmarks/**`;
- zmiana kontraktu produktu pod wygodny test;
- ręczne Assignment/demand/wzorcowy grafik;
- mock wyniku PLAN/REPLAN/validate/analityki w bramce zaufania;
- usuwanie lub wyłączanie starych testów bez osobnego dowodu, że są sprzeczne z
  PRODUCT_TRUTH;
- naprawa znalezionego defektu produktu w T043.

## 10. WHERE_MAP

WHERE_MAP:
- MODE: OPTIONAL
- TARGETS: tests/property/coordinator_simulator.py
- TARGETS: tests/property/test_coordinator_simulator.py
- REASON: zmieniamy właściciela budowy scenariusza, raportu i wejścia pytest; mapa może ujawnić pozostałych konsumentów bez rozszerzania jej na produkt.

Wykonane przy tworzeniu kontraktu:

```powershell
python where.py tests/property/coordinator_simulator.py
python where.py tests/property/test_coordinator_simulator.py
```

Wynik: oba pliki są testowe. Produkcyjne moduły nie importują Symulatora.
Pierwszy plik jest rzeczywiście konsumowany przez drugi; pozostałe trafienia to
historyczne briefy/raporty albo niezależne symbole o tej samej nazwie. Nie ma
powodu poszerzać `TASK_SCOPE` na produkt.

## 11. Odbiór i sposób testowania

### Checkpoint A

- małe testy generatora bez solvera: roster 5/10, target 176, brak reaktywnego
  LOCAL, urlop/L4 w dozwolonych granicach;
- jeden prawdziwy API vertical S01;
- jeden `DECISION_REQUIRED` bez automatycznego zatrudniania.

### Checkpoint B

- celowane scenariusze S01, S04, S06 dla godzin 144/144/...;
- jeden przypadek wsparcia z realnym payloadem i jeden bez propozycji;
- jeden REPLAN;
- pełna S01–S12 raz na finalnym SHA, z raportem Markdown/JSON;
- nie uruchamiać całej suity repo.

### Checkpoint C

- jeden realny Playwright flow;
- klasyfikacja tylko testów z obszarów wskazanych w 6.2;
- trzy kontrolowane mutacje z 6.4 i dowód, że właściwy pion je wykrywa;
- TypeScript/build tylko jeśli dotknięto testu e2e/helpera wymagającego
  kompilacji.

Odbiór końcowy nie brzmi „N testów PASS”. Oczekiwane dowody to:

1. exact SHA;
2. raport czytelny przez OWNERA z godzinami każdego pracownika;
3. JSON i komendy reprodukcji;
4. jawna lista scenariuszy FEASIBLE, DECISION_REQUIRED i defektów produktu;
5. dowód, że żaden scenariusz nie zwiększył rosteru 5/10;
6. dowód, że bramka zrobiła się czerwona dla trzech znanych klas błędu;
7. lista starych testów, które pozostały UNIT/BENCHMARK i dlatego nie są
   używane jako dowód działania programu.

## 12. Warunki zatrzymania

Implementer zatrzymuje się i zgłasza problem, jeżeli:

- wykonanie S01/S04/S06 wymaga więcej niż 5/5/10 LOCAL;
- produkcja nie potrafi zaproponować wsparcia przy EXTERNAL membership bez
  okna — nie wolno parsować innej wiadomości ani wymyślać propozycji;
- raport godzin wymaga nowego endpointu lub zmiany produktu; najpierw wskazać,
  dlaczego obecny month view/analytics nie wystarcza;
- którykolwiek scenariusz wymaga ręcznego zbudowania wyniku;
- potrzebna jest zmiana poza TASK_SCOPE;
- kontrolowana mutacja pozostaje zielona i nie da się jej wykryć bez
  dopisania nowego zachowania produktowego — zgłosić lukę orakla, nie zgadywać.

## 13. Pytania do niezależnego review przed implementacją

1. Czy sekcja 2 wiernie zapisuje ostatnie decyzje OWNERA, szczególnie różnicę
   między EXTERNAL membership a aktywnym oknem?
2. Czy S01–S12 obejmuje pojedynczą/podwójną obsadę, 12 h/24 h, urlop/L4,
   ochronę, regułę pracownika, prawdziwy brak nocnej obsady i REPLAN bez
   dowolnego doboru ludzi?
3. Czy orakle B1–B5 wykrywają „zielony, lecz bzdurny” wynik bez kopiowania
   solvera?
4. Czy któryś element można usunąć, zachowując raport godzin, realny przepływ
   i kalibrację na znanych błędach?
5. Czy zakres C jest wystarczająco mały, aby nie zamienić T043 w przebudowę
   całej suity?

Do zamknięcia review: **CC READ-ONLY — NIE IMPLEMENTOWAĆ**.

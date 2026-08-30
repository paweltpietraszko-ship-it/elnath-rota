# ROTA-T043 — Wiarygodny Symulator Koordynatora i bramka zaufania do testów

Status: **OWNER_CORRECTED R2 — DO NIEZALEŻNEGO PRZEGLĄDU, BEZ IMPLEMENTACJI**

Base: `main@c25c73e0332158bae703109e770f3cf83fd970a7`

Autor briefu: Codex jako niezależny tester. CC napisał T038/T039 i celowo nie
projektuje własnej poprawki. Źródłem zlecenia jest
`arch/REQUEST_SYMULATOR_INDEPENDENT_DIAGNOSIS_2026-08-30.md` na
`docs/symulator-repair-diagnosis-request@f248c07d3e6f65164080863b47b694118477574b`.

## 0. OWNER_CORRECTED — czym jest Symulator i gdzie kończy się produkt

Symulator **nie odtwarza zamkniętej listy wymyślonych scenariuszy**. Jest
seedowanym generatorem pracy koordynatora: przed uruchomieniem solvera zakłada
wiele różniących się obiektów, wpisuje ich rzeczywiste parametry przez backend,
naciska PLAN/REPLAN i raportuje wynik. Parametry danego obiektu są ustalone
przed PLAN i nie wolno ich poprawiać pod wynik solvera.

Przykład OWNERA trzeba rozumieć dosłownie: od poniedziałku do piątku jedna osoba
pełni D 12 h i jedna osoba N 12 h, a w sobotę i niedzielę jedna osoba pełni H24.
To nadal **jedno ciągłe stanowisko 24/7**, czyli 168 godzin obsady w tygodniu, a
nie dwie równoległe obsady po 12 h. Dla tej rodziny roster wynosi 5 LOCAL, nie 8.

Automatyczne wsparcie ma inną granicę w teście i w produkcie:

- pierwszy PLAN Symulator zawsze wykonuje wyłącznie na wygenerowanej załodze
  LOCAL;
- dopiero jeżeli ten rzeczywisty PLAN zwróci `DECISION_REQUIRED`, Symulator
  automatycznie odtwarza zgodę koordynatora: przez produkcyjne operacje tworzy
  jedną syntetyczną osobę `EXTERNAL_SUPPORT`, bez targetu, dodaje jej okno i
  ponawia PLAN;
- ta automatyzacja istnieje wyłącznie po to, żeby test bez człowieka mógł
  sprawdzić oba etapy: wykrycie braku oraz grafik po udzieleniu pomocy;
- **nie jest to zachowanie produktu**. W zwykłym programie solver nadal ma
  zatrzymać się na decyzji, a prawdziwy koordynator ręcznie dopisuje nową osobę
  do obsady obiektu jako LOCAL;
- Symulator nigdy nie dodaje reaktywnie kolejnych LOCAL i nigdy z góry nie
  oznacza obiektu jako „wymagający wsparcia”. To ma wynikać z prawdziwego wyniku
  pierwszego PLAN.

W `tests/property/coordinator_simulator.py` nad modułem/driverem ma pozostać
komentarz lub docstring o tej treści merytorycznej (może być krótszy, ale nie
może zmienić sensu):

```text
TEST-HARNESS BOUNDARY: ten moduł symuluje działania koordynatora, a nie logikę
solvera. Wszystkie parametry obiektu powstają przed pierwszym PLAN. Pierwszy
PLAN używa tylko wygenerowanych LOCAL. Dopiero rzeczywisty DECISION_REQUIRED
uruchamia testową, automatyczną zgodę: utworzenie SIM-EXTERNAL, okna i ponowny
PLAN przez produkcyjny backend. To pozwala kontynuować automatyczny eksperyment
bez człowieka; nie jest funkcją produktu. W programie decyzję widzi koordynator
i ręcznie dodaje osobę do obsady jako LOCAL. Nie dodawaj reaktywnie LOCAL, nie
przewiduj z góry potrzeby wsparcia i nie dopasowuj wejść do wyniku solvera.
```

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

- osobna SQLite `:memory:` dla każdego wygenerowanego obiektu;
- ustawienia przez istniejące produkcyjne endpointy/operacje backendowe;
- prawdziwy assembler, PLAN, `select_candidate()` z produkcyjnym `validate()`
  oraz REPLAN;
- bez ręcznego tworzenia wynikowych `Assignment`, demandów i wzorcowego
  grafiku;
- bez danych użytkownika, sieci i `rota_dev.db`;
- generator tworzy różne obiekty i wszystkie ich wejścia przed PLAN, następnie
  naciska PLAN/REPLAN i raportuje wynik. Nie kopiuje
  do testu reguł odpoczynku, urlopu, L4 ani solvera.

### 2.2 Wielkość załogi wynika z rodzaju obiektu, nie z wygody solvera

- pojedyncza obsada całodobowa: dokładnie **5 LOCAL**;
- podwójna obsada całodobowa: dokładnie **10 LOCAL**;
- sposób podziału jednej ciągłej doby na D/N 12 h, H24 albo D/N 12 h w dni
  robocze i H24 w weekend nie zmienia jej w dodatkową równoległą obsadę;
- dotyczy również krótkiego miesiąca; symulator nie „zwalnia” pracownika w
  lutym;
- po `DECISION_REQUIRED` nie wolno dodać szóstego–dziewiątego LOCAL;
- obecne `ceil(monthly_hours / 160)` nie jest kontraktem i ma zniknąć z decyzji
  o liczebności załogi. Godziny zapotrzebowania nadal wylicza produkcyjny
  katalog, ale nie mogą niezależnie wylosować dowolnego rosteru.

### 2.3 Target godzin jest prawdziwym wejściem koordynatora, nie stałą testu

- każdy LOCAL dostaje jawny `target_hours` przez produkcyjny endpoint;
- EXTERNAL_SUPPORT nie dostaje targetu;
- generator wybiera miesiące i dla każdego LOCAL wpisuje wymiar pełnego etatu
  wyliczony z kalendarza tego miesiąca zgodnie z art. 130 KP;
- `2026-09-01 = 176 h` pozostaje małym przypadkiem kontrolnym kalkulatora, ale
  nie jest centralnym ani jedynym miesiącem raportu;
- wartość nie jest udziałem `720 / 5` ani stałą `168`/`160`;
- runtime testu nie korzysta z Internetu. Generator korzysta z zapisanego
  kalendarza i wzoru, a kontrolne wartości są zamrożonymi fixture z podanym
  źródłem. Państwowa Inspekcja Pracy opisuje wzór z art. 130 KP, a urzędowa
  tabela dla 2026 r. podaje dla września 176 h:
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

- przed pierwszym PLAN nie istnieje dodatkowa osoba ani aktywne okno wsparcia;
- rzeczywisty, niepusty `DECISION_REQUIRED` jest wystarczającym sygnałem dla
  **drivera testowego**, by zasymulował zgodę koordynatora; nie wolno uzależniać
  tego od brzmienia albo parsowania `unblocking_options`;
- driver tworzy jedną osobę `SIM-EXTERNAL-*`, membership `EXTERNAL_SUPPORT`
  bez targetu i okno przez istniejące produkcyjne operacje, dowiązując decyzję
  tam, gdzie wymaga tego istniejący kontrakt, po czym ponownie naciska PLAN;
- raport osobno zachowuje wynik pierwszego PLAN, payload decyzji, fakt udzielenia
  testowej zgody, utworzone okno, wynik drugiego PLAN i faktyczne użycie osoby;
- ten krok nie może zmieniać liczby LOCAL ani zostać przeniesiony do produktu.

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

### 4.2 Seedowany generator portfela obiektów, nie macierz scenariuszy

Pełny raport domyślnie zakłada **20 niezależnych, różniących się obiektów**.
Każdy obiekt dostaje przed pierwszym PLAN kompletną, seedowaną konfigurację.
Ten sam seed odtwarza ten sam portfel i daje gotową komendę reprodukcji jednego
obiektu, ale narzędzie nie odgrywa stałej listy S01–S12.

Generator składa poprawne kombinacje co najmniej z następujących osi:

- miesiąc z zapisanego kalendarza (w tym miesiące krótkie, święta i kontekst
  granicy miesiąca);
- jedna albo dwie pełne, ciągłe warstwy obsady 24/7, czyli odpowiednio 5 albo
  10 LOCAL;
- podział doby: D/N po 12 h, H24 oraz
  `WEEKDAY_12H_WEEKEND_24H` — D+N w dni robocze i jedna H24 w weekend;
- poprawne godziny rozpoczęcia i istniejący tryb ochrony;
- wszyscy dostępni albo najwyżej jedna planowa nieobecność do 14 dni;
- L4 0–21 dni, znane przed PLAN albo dodane przed REPLAN;
- brak lub aktywna istniejąca reguła pracownika, np. DAY_ONLY;
- zwykły PLAN albo zmiana wejścia i pełny REPLAN.

Losowanie zachodzi **wewnątrz tych dozwolonych wymiarów**, a raport zawiera
ledger pokrycia pokazujący, które wartości i pary wartości faktycznie wystąpiły.
Generator ma deterministycznie zapewnić reprezentację każdej osi w całym
portfelu, ale nie przez dwanaście ręcznie opisanych gotowych grafików.

Małe przypadki kontrolne generatora sprawdzają tylko jego matematykę i znaczenie
wejść: jedna pełna warstwa D/N = 5 LOCAL, jedna pełna warstwa H24 = 5 LOCAL,
`WEEKDAY_12H_WEEKEND_24H` = 5 LOCAL, dwie pełne warstwy = 10 LOCAL. Nie są
treścią głównego raportu i nie wolno kalibrować pod nie solvera.

T043 nie wymyśla jeszcze obiektu z częściową drugą równoległą warstwą, np. dwie
osoby tylko przez część tygodnia. Nie ma zamrożonej decyzji, jak z samego takiego
zapotrzebowania bezpiecznie wyliczyć załogę z uwzględnieniem odpoczynków. Przykład
OWNERA D/N w tygodniu + H24 w weekend **nie jest** takim obiektem. Odrzuconego
`SPLIT_NIGHT_12_8` nie przywracać.

### 4.3 Koszt uruchomienia

- zwykły test celowany uruchamia najwyżej po jednym krótkim obiekcie z
  każdej zmienionej klasy;
- pełny wygenerowany portfel 20 obiektów jest jawnym poleceniem raportowym,
  uruchamianym raz na finalnym SHA, a nie częścią każdego `pytest`;
- pełna regresja całego repo nie jest wymagana i nie wolno jej uruchamiać bez
  osobnej zgody OWNERA;
- timeout i seed muszą być zapisane. Nie wolno ratować timeoutu przez dodanie
  pracowników.

## 5. Checkpoint B — co Symulator ma naprawdę sprawdzać

Symulator nie buduje drugiego solvera ani drugiego validatora. Ma pięć prostych
orakli pochodzących bezpośrednio z decyzji OWNERA i produkcyjnych odczytów.

### B1. Zamknięty świat

- roster ma dokładnie liczbę LOCAL wynikającą z wygenerowanej pełnej warstwy:
  5 dla jednej albo 10 dla dwóch;
- po każdym PLAN/REPLAN nadal ma dokładnie tę samą liczbę LOCAL;
- w grafiku nie ma obcej osoby, obcego Site, obcego demandu ani godzin typu
  INNY;
- EXTERNAL może wystąpić wyłącznie we własnym aktywnym oknie utworzonym po
  rzeczywistym `DECISION_REQUIRED` pierwszego PLAN.

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

Dla wygenerowanych czystych obiektów bez absencji i indywidualnych ograniczeń
raport jawnie ocenia porównywalność godzin między LOCAL z uwzględnieniem
niepodzielności użytych zmian. Nie wpisuje stałego oczekiwania 144 h dla każdego
miesiąca. Dla obiektów z urlopem, L4 albo regułą pracownika pokazuje rozkład i
produkcyjny effective target, ale nie zgaduje własnego „idealnego” grafiku.

### B4. Uczciwy `DECISION_REQUIRED`

- payload nie jest całkowicie pusty;
- raport pokazuje blokujące demandy, osoby/warunki, load blocker i opcje;
- Symulator nie oznacza z góry przypadku jako „wymagający wsparcia”; zapisuje
  pierwsze `DECISION_REQUIRED`, automatycznie wykonuje testową zgodę opisaną w
  2.5 i porównuje oba etapy;
- jeśli certyfikowany przez generator czysty obiekt bez absencji zwraca
  `DECISION_REQUIRED`, zachować failure JSON. Nadal wolno wykonać reakcję
  wsparcia dla zebrania dowodu, ale wynik pierwszego PLAN nie przestaje być
  widoczny i nie wolno osłabiać jego danych wejściowych.

### B5. REPLAN reaguje na zmianę

Raport zachowuje zestaw godzin i przypisań przed zmianą oraz po REPLAN. Pokazuje
co zmieniono w wejściu i czy backend ponownie zbilansował cały dostępny miesiąc.
Nie wymusza ręcznie konkretnego grafiku.

### 5.1 Artefakty

Jawne uruchomienie pełnego wygenerowanego portfela tworzy dwa nowe artefakty na
exact SHA:

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
| generator 5/10 | jawna decyzja OWNER | prawdziwy roster pełnej warstwy 24/7 | 5 dla jednej warstwy, 10 dla dwóch; bez reaktywnego LOCAL |
| target miesiąca | OWNER + art. 130/PIP | prawdziwe wejście koordynatora | jeden kalkulator z kalendarza; 176 tylko kontrola września |
| seedowany portfel 20 obiektów | OWNER | różne wejścia zamiast benchmarku | kombinacje zamrożonych osi, ledger i reprodukcja z seedu |
| reakcja po `DECISION_REQUIRED` | OWNER | bezobsługowo odtwarza zgodę w teście | istniejące create-person/membership/support-window; zachowanie poza produktem |
| godziny/spread | OWNER fairness + T041 | ujawnia bzdury widoczne ręcznie | odczyt assignments/analityki, bez drugiego solvera |
| produkcyjne validate | istniejący owner | legalność kandydata | select/revalidate, bez kopii walidatora |
| Markdown + JSON | prośba OWNER | czytelność i reprodukcja | jeden model danych, dwa renderery |
| jeden UI vertical | luka między API i ekranem | sprawdza realne kliknięcie | jeden flow, nie macierz browserowa |
| 3 mutacje kontrolne | znane incydenty | dowód, że test umie upaść | tymczasowy worktree, bez nowej zależności |

Usunięte z propozycji:

- nowy solver, validator albo checker reguł HARD;
- dowolna obsada 4–9 i reaktywne zatrudnianie LOCAL;
- osoba lub aktywne wsparcie przed pierwszym PLAN;
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

- małe testy generatora bez solvera: znaczenie pełnych warstw 5/10, przykład
  D/N w tygodniu + H24 w weekend = 5, targety różnych miesięcy, brak
  reaktywnego LOCAL oraz urlop/L4 w dozwolonych granicach;
- jeden wygenerowany prawdziwy API vertical;
- jeden `DECISION_REQUIRED` z automatycznym EXTERNAL i dowodem, że liczba LOCAL
  nie wzrosła.

### Checkpoint B

- celowane obiekty jednej i dwóch warstw oraz wariantu
  `WEEKDAY_12H_WEEKEND_24H`, z raportem faktycznych godzin;
- jeden przypadek wsparcia po realnym, niepustym payloadzie;
- jeden REPLAN;
- pełny seedowany portfel 20 obiektów raz na finalnym SHA, z ledgerem pokrycia i
  raportem Markdown/JSON;
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
5. dowód, że żaden przebieg nie zwiększył liczby LOCAL ponad 5/10, a każda
   osoba EXTERNAL powstała dopiero po pierwszym `DECISION_REQUIRED`;
6. dowód, że bramka zrobiła się czerwona dla trzech znanych klas błędu;
7. lista starych testów, które pozostały UNIT/BENCHMARK i dlatego nie są
   używane jako dowód działania programu.

## 12. Warunki zatrzymania

Implementer zatrzymuje się i zgłasza problem, jeżeli:

- generator nie potrafi przed PLAN jednoznacznie przypisać 5 albo 10 LOCAL do
  dozwolonej pełnej warstwy obsady;
- automatyczna reakcja wymaga parsowania tekstu `unblocking_options` albo
  zmiany produktu — wystarczającym triggerem ma być niepusty
  `DECISION_REQUIRED`, a cała reakcja należy do drivera testowego;
- raport godzin wymaga nowego endpointu lub zmiany produktu; najpierw wskazać,
  dlaczego obecny month view/analytics nie wystarcza;
- którykolwiek scenariusz wymaga ręcznego zbudowania wyniku;
- potrzebna jest zmiana poza TASK_SCOPE;
- kontrolowana mutacja pozostaje zielona i nie da się jej wykryć bez
  dopisania nowego zachowania produktowego — zgłosić lukę orakla, nie zgadywać.

## 13. Pytania do niezależnego review przed implementacją

1. Czy sekcje 0 i 2 jednoznacznie oddzielają automatyczną reakcję testowego
   drivera od ręcznego działania koordynatora w produkcie?
2. Czy generator portfela naprawdę składa różne wejścia przed PLAN, obejmuje
   jedną/dwie pełne warstwy, 12 h/24 h, urlop/L4, ochronę, regułę pracownika i
   REPLAN, zamiast odgrywać zamkniętą macierz?
3. Czy orakle B1–B5 wykrywają „zielony, lecz bzdurny” wynik bez kopiowania
   solvera?
4. Czy któryś element można usunąć, zachowując raport godzin, realny przepływ
   i kalibrację na znanych błędach?
5. Czy zakres C jest wystarczająco mały, aby nie zamienić T043 w przebudowę
   całej suity?

Do zamknięcia review: **CC READ-ONLY — NIE IMPLEMENTOWAĆ**.

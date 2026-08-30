# ROTA-T043 — Wiarygodny Symulator Koordynatora i bramka zaufania do testów

Status: **ARCHITECT_CORRECTED R4 — READY FOR NIEZALEŻNY PREIMPLEMENTATION RE-AUDIT — CC READ-ONLY / BEZ IMPLEMENTACJI**

Base: `main@c25c73e0332158bae703109e770f3cf83fd970a7`

Autor briefu: Codex jako niezależny tester. CC napisał T038/T039 i celowo nie
projektuje własnej poprawki. Źródłem zlecenia jest
`arch/REQUEST_SYMULATOR_INDEPENDENT_DIAGNOSIS_2026-08-30.md` na
`docs/symulator-repair-diagnosis-request@f248c07d3e6f65164080863b47b694118477574b`.

Korekta architekta R4 uwzględnia wyłącznie ustalenia z:

- `tasks/ROTA-T043/round_01/tests/tests_r1.txt`;
- `tasks/ROTA-T043/round_01/tests/tests_r2.txt` — OWNER_CORRECTED: Cross-Site
  wycofane z T043 i zamknięte;
- `tasks/ROTA-T043/round_01/tests/tests_r3.txt` — pięć technicznych uwag
  potwierdzonych file:line;
- `tasks/ROTA-T043/round_01/tests/tests_r4.txt` — OWNER_CORRECTED: Symulator ma
  badać aktualny solver, zawsze oceniać fairness gotowego grafiku i wykonać
  prawdziwy przebieg kwartalny jednego obiektu.

T043 **nie naprawia solvera**. Jeżeli aktualny solver zwróci zły grafik, to jest
wartościowy wynik Symulatora: wejścia, seed, wynik, Assignmenty, wykryte
naruszenia i komenda reprodukcji zostają zachowane do osobnego późniejszego
TASK-u produktu. Nie wolno poprawiać scenariusza, grafiku ani solvera po to, by
Symulator zrobił się zielony.

## 0. OWNER_CORRECTED — czym jest Symulator i gdzie kończy się produkt

Symulator **nie jest symulatorem solvera**. Jest seedowanym generatorem pracy
koordynatora: zakłada rzeczywiste obiekty, wpisuje ich parametry przez backend,
naciska PLAN/REPLAN, odbiera rzeczywisty wynik i ocenia gotowy grafik. Nie
buduje własnego grafiku, drugiego solvera ani drugiego validatora.

Wszystkie parametry danego obiektu powstają przed pierwszym PLAN. Po zobaczeniu
wyniku nie wolno zmieniać rosteru LOCAL, targetów, katalogu, absencji ani reguł
po to, by solverowi było łatwiej. Jedynym automatycznym wyjątkiem jest opisana
niżej **testowa ścieżka wsparcia EXTERNAL**, uruchamiana dopiero po prawdziwym
`DECISION_REQUIRED` i zawsze z zachowaniem pierwszego wyniku.

Przykład OWNERA trzeba rozumieć dosłownie: od poniedziałku do piątku jedna osoba
pełni D 12 h i jedna osoba N 12 h, a w sobotę i niedzielę jedna osoba pełni H24.
To nadal **jedno ciągłe stanowisko 24/7**, czyli 168 godzin obsady w tygodniu, a
nie dwie równoległe obsady po 12 h. Dla tej rodziny roster wynosi 5 LOCAL, nie 8.

Automatyczne wsparcie ma inną granicę w teście i w produkcie:

- pierwszy PLAN Symulator zawsze wykonuje wyłącznie na wygenerowanej załodze
  LOCAL;
- dopiero jeżeli ten rzeczywisty PLAN zwróci `DECISION_REQUIRED`, Symulator
  uruchamia **testową ścieżkę wsparcia**: przez produkcyjne operacje tworzy
  jedną syntetyczną osobę `EXTERNAL_SUPPORT`, bez targetu, dodaje jej membership
  i okno, a następnie ponawia PLAN;
- ta automatyzacja istnieje wyłącznie po to, żeby test bez człowieka mógł
  sprawdzić oba etapy; nie jest funkcją produktu ani symulacją kliknięcia w UI;
- w prawdziwym programie solver zatrzymuje się na decyzji, a koordynator po tej
  decyzji **ręcznie dodaje nową osobę do LOCAL**;
- Symulator nigdy nie dodaje reaktywnie kolejnych LOCAL i nigdy z góry nie
  oznacza obiektu jako wymagającego wsparcia;
- ponowienie po EXTERNAL nigdy nie usuwa ani nie zamienia pierwszego wyniku w
  PASS. Pierwszy PLAN pozostaje osobnym faktem i reproduktorem.

W `tests/property/coordinator_simulator.py` nad modułem/driverem ma pozostać
komentarz lub docstring o tej treści merytorycznej:

```text
TEST-HARNESS BOUNDARY: ten moduł symuluje działania koordynatora, a nie logikę
solvera. Wszystkie parametry obiektu powstają przed pierwszym PLAN. Symulator
nie poprawia grafiku ani danych pod wynik solvera. Zły grafik jest wynikiem
badania i zostaje zachowany jako reproduktor. Pierwszy PLAN używa tylko
wygenerowanych LOCAL. Dopiero rzeczywisty DECISION_REQUIRED uruchamia testową
ścieżkę wsparcia EXTERNAL przez produkcyjny backend. Nie dodawaj reaktywnie
LOCAL, nie przewiduj z góry potrzeby wsparcia i nie kalibruj wejść pod PASS.
```

## 1. Wynik dla OWNERA

Obecny Symulator nie daje wiarygodnej odpowiedzi na pytanie „co aktualny solver
robi z prawdziwą pracą koordynatora”, bo między innymi:

1. nie ocenia poprawności gotowego wyniku;
2. po `DECISION_REQUIRED` potrafi dopisywać LOCAL i zmieniać badany obiekt;
3. nie ma wariantu podwójnej obsady i 10-osobowej załogi;
4. pomija L4 przed pierwszym PLAN;
5. zapisuje kalendarz poza produkcyjną operacją backendową;
6. zwykły pytest nadpisuje historyczny raport T038;
7. raport nie pokazuje pełnych godzin, targetów, typów membership,
   Assignmentów i rzeczywistego wsparcia;
8. technicznie zapisany, lecz zły albo niesprawiedliwy grafik może pozostać
   zielony;
9. nie wykonuje rzeczywistego wielomiesięcznego przebiegu jednego obiektu przez
   kwartał.

T043 naprawia narzędzie i od razu używa go do wytworzenia pierwszego
czytelnego raportu. Sam napis „testy PASS” nie jest kryterium odbioru T043, a
czerwony wynik produktu nie jest powodem do poprawiania scenariusza.

## 2. Zamrożone decyzje OWNERA

### 2.1 Symulator odtwarza pracę koordynatora

- osobna SQLite `:memory:` dla każdego niezależnego obiektu miesięcznego;
- wyjątek: obowiązkowy przebieg kwartalny używa **jednej tej samej bazy** dla
  wszystkich trzech miesięcy tego samego obiektu;
- ustawienia przez istniejące produkcyjne endpointy/operacje backendowe;
- prawdziwy assembler, PLAN, `select_candidate()` z produkcyjnym `validate()`
  oraz REPLAN;
- bez ręcznego tworzenia wynikowych `Assignment`, demandów i wzorcowego
  grafiku;
- bez danych użytkownika, sieci i `rota_dev.db`;
- generator tworzy wejścia przed PLAN, potem obserwuje wynik. Nie kopiuje
  solvera i nie zmienia wejść po wyniku, aby osiągnąć PASS.

### 2.2 Wielkość załogi wynika z rodzaju obiektu

- pojedyncza pełna obsada całodobowa: dokładnie **5 LOCAL**;
- podwójna pełna obsada całodobowa: dokładnie **10 LOCAL**;
- D/N 12 h, H24 i `WEEKDAY_12H_WEEKEND_24H` są tylko różnymi podziałami tej
  samej ciągłej warstwy, nie losowym sposobem liczenia headcountu;
- krótki miesiąc nie zmniejsza rosteru;
- po `DECISION_REQUIRED` nie wolno dodawać LOCAL;
- `ceil(monthly_hours / 160)` nie jest kontraktem i nie decyduje o rosterze.

### 2.3 Target godzin i kalendarz są niezależnym wejściem

- każdy LOCAL dostaje jawny `target_hours` przez produkcyjny endpoint;
- EXTERNAL_SUPPORT nie dostaje targetu;
- każdy LOCAL dostaje wymiar pełnego etatu dla badanego miesiąca, niezależny od
  liczby ludzi i godzin obiektu;
- wartość nie jest udziałem `monthly_hours / headcount` ani stałą 160/168;
- runtime testu nie korzysta z Internetu.

Kalendarz użyty jako wejście nie może sprawdzać sam siebie. T043 używa
zamrożonej fixture urzędowej 2026:

- stała lista polskich świąt ustawowo wolnych w 2026 r.;
- źródło kalendarza: Zielona Linia / Centrum Informacyjne Służb Zatrudnienia,
  „Święta wolne od pracy w 2026 roku”;
- niezależna tabela kontrolna wymiaru godzin 2026: Powiatowy Urząd Pracy w
  Sosnowcu;
- obowiązkowe kontrole: **styczeń 2026 = 160 h** i **wrzesień 2026 = 176 h**;
- pełny portfel losuje miesiące wyłącznie z 2026 objętego fixture;
- kalkulator targetu może być użyty dopiero po sprawdzeniu go przeciw fixture;
- brak pobierania danych z sieci podczas runtime.

Fixture sprawdza wejście i arytmetykę targetu. Nie czyni Symulatora niezależnym
audytorem całego prawa pracy.

### 2.4 Nieobecności

- w scenariuszu planowego urlopu nie ma albo ma go najwyżej jedna osoba;
- urlop to jeden zakres do 14 dni kalendarzowych;
- backend wylicza jego godziny, a raport zachowuje wynik;
- L4 ma seedowaną długość 0–21 dni i może być znane przed PLAN albo pojawić się
  przed REPLAN;
- Symulator zapisuje rodzaj i zakres nieobecności. Nie tworzy własnych zmian
  `U/C` ani własnego rachunku 8/12/16 h.

### 2.5 Testowa ścieżka wsparcia EXTERNAL

- przed pierwszym PLAN nie istnieje dodatkowa osoba ani aktywne okno wsparcia;
- prawdziwy, niepusty `DECISION_REQUIRED` uruchamia driver testowy;
- nie wolno parsować tekstu `unblocking_options` jako warunku;
- driver tworzy jedną nową osobę `SIM-EXTERNAL-*` jako `EXTERNAL_SUPPORT`, bez
  targetu;
- **wyłącznie create-person** niesie aktualne
  `responds_to_decision_required_id`;
- attach-membership i support-window przekazują
  `responds_to_decision_required_id = null`;
- dopiero po tych trzech zapisach następuje drugi PLAN;
- raport osobno zachowuje pierwszy PLAN, payload decyzji, ID pierwszego zapisu,
  utworzoną osobę/membership/okno, drugi PLAN i faktyczne użycie EXTERNAL;
- drugi PLAN nie może zmienić statusu pierwszego wyniku w raporcie;
- krok nie zmienia liczby LOCAL i nie trafia do produktu.

### 2.6 `DECISION_REQUIRED` może być poprawnym wynikiem

`DECISION_REQUIRED` nie jest automatycznie błędem. Jest użytecznym wynikiem,
jeżeli badany obiekt rzeczywiście nie może zostać obsadzony i payload zawiera
konkretne dane. Całkowicie pusty payload jest defektem narzędzia albo produktu i
nie może zostać przedstawiony jako zielony.

### 2.7 Zły grafik jest wynikiem badania, nie sygnałem do zmiany wejścia

Dla każdego FEASIBLE Symulator zachowuje gotowy grafik i go ocenia. Jeżeli
wykryje naruszenie, nierówność albo niespójność:

- zapisuje pełne wejście, seed, wynik PLAN/REPLAN, Assignmenty i wykryte fakty;
- tworzy failure JSON oraz komendę reprodukcji;
- nie zmienia rosteru LOCAL, targetów, katalogu, absencji ani reguł;
- nie buduje poprawionego grafiku;
- nie uruchamia własnego optymalizatora;
- nie poprawia kodu produktu w T043.

Taki wynik prowadzi później do osobnego TASK-u naprawczego solvera/produktu.

### 2.8 Granica twierdzeń o prawie

- produkcyjne `validate()` dowodzi wyłącznie zgodności kandydata z aktualnymi
  regułami HARD zaimplementowanymi w produkcie;
- raport nie nazywa tego niezależnym potwierdzeniem zgodności z całym Kodeksem
  pracy;
- T043 nie dodaje własnego checkera 11 h/35 h/16 h/24 h ani kopii validatora;
- kontrola art. 130 dotyczy wyłącznie niezależnego wejścia `target_hours`.

## 3. Jedno zadanie, trzy checkpointy

T043 jest jednym testowym taskiem:

1. **A — prawdziwe wejścia i działania koordynatora;**
2. **B — ocena gotowego grafiku, raport miesięczny i obowiązkowy przebieg
   kwartalny;**
3. **C — mała bramka zaufania do istniejących testów.**

Każdy checkpoint ma osobny logiczny commit. Nie wolno w T043 poprawiać kodu
produktu. Jeżeli B ujawni defekt, zachować reproduktor i nie pomagać solverowi.

## 4. Checkpoint A — poprawiony Symulator

### 4.1 Produkcyjna ścieżka

Wszystkie działania przechodzą przez te same endpointy/operacje co frontend:

- utworzenie Site i katalogu zmian;
- ustawienie każdego dnia kalendarza przez `/api/workspace/calendar/day`;
- utworzenie pracowników, membership i targetów LOCAL;
- zapis nieobecności/reguł pracownika;
- PLAN, odczyt decyzji, ewentualna testowa ścieżka EXTERNAL, ponowny PLAN;
- wybór pierwszego zwróconego kandydata jako deterministycznej decyzji drivera,
  `select_candidate()`, ponowny odczyt miesiąca/analityki;
- zmiana wejścia i REPLAN w scenariuszach REPLAN;
- w kwartalnym pionie: kolejny miesiąc tego samego Site i tej samej bazy po
  zapisaniu poprzedniego miesiąca.

`TestClient` i SQLite `:memory:` są dozwolone. Nie wolno monkeypatchować wyniku
PLAN, kandydata, walidacji ani analityki.

### 4.2 Seedowany portfel miesięczny

Pełny raport miesięczny domyślnie zakłada **20 niezależnych, różniących się
obiektów**. Każdy dostaje przed pierwszym PLAN kompletną konfigurację. Ten sam
seed odtwarza ten sam obiekt.

Generator składa kombinacje co najmniej z osi:

- miesiąc z fixture 2026;
- jedna albo dwie pełne warstwy 24/7 — 5 albo 10 LOCAL;
- D/N 12 h, H24, `WEEKDAY_12H_WEEKEND_24H`;
- istniejący tryb ochrony i poprawne godziny startu;
- wszyscy dostępni albo najwyżej jedna planowa nieobecność do 14 dni;
- L4 0–21 dni, przed PLAN albo przed REPLAN;
- brak albo istniejąca reguła pracownika, np. DAY_ONLY;
- PLAN albo późniejsza materialna zmiana i REPLAN.

Losowanie zachodzi wyłącznie wewnątrz tych osi. Ledger pokazuje faktyczne
pokrycie wartości i par wartości. Parametry są ustalone przed PLAN.

Małe testy generatora sprawdzają wyłącznie jego wejścia: 5/10 LOCAL, kształty
katalogu oraz targety kontrolne 160/176. Nie wolno kalibrować solvera pod te
testy.

T043 nie dodaje częściowej drugiej warstwy, `SPLIT_NIGHT_12_8`, Cross-Site ani
nowego rodzaju obiektu.

### 4.3 Obowiązkowy kontrolny przebieg kwartalny

Oprócz 20 niezależnych obiektów miesięcznych T043 wykonuje jeden jawny pion
**Q3 2026: lipiec → sierpień → wrzesień** dla tego samego obiektu.

Warunki pionu:

- jedna SQLite `:memory:` przez cały kwartał;
- ten sam Site i te same 5 LOCAL przez trzy miesiące;
- jedna pełna warstwa 24/7 w prostym istniejącym kształcie D/N 12 h;
- brak urlopu, L4 i indywidualnych reguł w tym jednym pionie — ma izolować
  przenoszenie godzin, nie mieszać kilku problemów naraz;
- dla każdego miesiąca kalendarz i target_hours pochodzą z tej samej niezależnej
  fixture 2026;
- każdy miesiąc wykonuje prawdziwy PLAN; jeśli potrzebna jest testowa ścieżka
  EXTERNAL, pierwszy `DECISION_REQUIRED` zostaje zachowany, wsparcie może
  pozwolić kontynuować badanie, ale nie zamienia pierwszego wyniku w PASS;
- po FEASIBLE driver wybiera pierwszy kandydat, wykonuje `select_candidate()` i
  dopiero wtedy przechodzi do kolejnego miesiąca;
- jeżeli mimo dozwolonej ścieżki wsparcia nie da się uzyskać bazowego grafiku,
  pion kończy się `QUARTER_BLOCKED`, zapisuje reproduktor i nie seeduje ręcznie
  Assignmentów, żeby sztucznie kontynuować.

Oracle kwartalny nie buduje drugiego mechanizmu WorkBalance. Dla tego kontrolnego
pionu bez absencji niezależna arytmetyka jest prosta:

`month_balance_expected = actual PRIMARY hours - target_hours`

`quarter_balance_expected(month) = quarter_balance_expected(previous) + month_balance_expected`

Pierwszy miesiąc ma carry-in 0. Dla sierpnia i września raport dodatkowo
sprawdza:

`product_quarter_balance - product_month_balance == previous_product_quarter_balance`

oraz porównuje produkcyjne `month_balance`, `quarter_balance` i
`unresolved_carryover` z powyższą arytmetyką. Mismatch to
`QUARTER_BALANCE_FAIL` + failure JSON. To nie jest drugi solver ani system
kadrowy; to niezależne dodawanie godzin na jednym obiekcie.

### 4.4 Koszt uruchomienia

- zwykły test celowany uruchamia najwyżej jeden krótki przypadek z każdej
  zmienionej klasy;
- pełny portfel 20 obiektów i jeden pion kwartalny są jawnym poleceniem
  raportowym, uruchamianym raz na finalnym SHA;
- pełna regresja repo nie jest wymagana bez osobnej zgody OWNERA;
- timeout i seed muszą być zapisane;
- timeoutu nie wolno ratować przez dodanie LOCAL ani zmianę danych wejściowych.

## 5. Checkpoint B — co Symulator ocenia

Symulator ocenia **gotowy wynik**, nie sposób dochodzenia solvera do wyniku.
Każdy wynik ma status diagnostyczny i dowód. Czerwony wynik produktu może być
poprawnym wynikiem wykonania T043, jeżeli Symulator go prawidłowo wykrył i
zachował.

### B1. Zamknięty świat

- roster LOCAL pozostaje dokładnie 5 albo 10;
- w grafiku nie ma obcej osoby, Site, demandu ani godzin typu INNY;
- EXTERNAL może wystąpić wyłącznie we własnym aktywnym oknie utworzonym po
  rzeczywistym `DECISION_REQUIRED`;
- powstanie EXTERNAL nie zmienia liczby LOCAL.

### B2. HARD zaimplementowany w produkcie

Każdy kandydat używany w raporcie przechodzi przez produkcyjne
`select_candidate()` oraz produkcyjny revalidate/readback. Wynik jest raportowany
jako `PRODUCT_VALIDATE_PASS/FAIL`.

Symulator nie odtwarza COVERAGE, REST, NIGHT-STREAK, urlopu ani L4 własnym
validatorem i nie nazywa `PRODUCT_VALIDATE_PASS` niezależnym dowodem zgodności z
całym prawem.

Jeżeli produkcyjny validator przepuści grafik, a inny zamrożony oracle T043
wykaże sprzeczność, oba fakty zostają w raporcie. Nie wolno uznać validatora za
ważniejszy tylko dlatego, że jest produkcyjny.

### B3. Sprawiedliwość jest oceniana zawsze

Każdy FEASIBLE gotowy grafik dostaje **dokładnie jeden** status:

- `FAIRNESS_PASS`;
- `FAIRNESS_FAIL`;
- `FAIRNESS_UNPROVEN`.

`FAIRNESS_UNPROVEN` **nie jest zielonym wynikiem**. Oznacza, że Symulator potrafi
policzyć fakty, ale dla tej klasy wejścia nie istnieje jeszcze zamrożony oracle,
który pozwala uczciwie stwierdzić, że solver osiągnął najlepszy możliwy SOFT.
Nie wolno wtedy wpisywać PASS ani wymyślać progu.

Dla każdego grafiku raport liczy z gotowych Assignmentów i istniejących danych:

- raw `target_hours` każdego LOCAL;
- produkcyjny `effective_target` i `absence_hours` jako osobno oznaczone fakty
  produktu;
- `actual PRIMARY hours`;
- `total_target_deviation = sum(abs(actual - effective_target))` dla LOCAL z
  istniejącym effective targetem;
- dla `effective_target > 0` dokładnie T032:
  `completion_pct = floor(100 * actual / effective_target)` i
  `target_equity_spread = max(completion_pct) - min(completion_pct)`;
- godziny weekendowe i ich max-min spread;
- godziny świąteczne/historyczne widoczne dla badanego obiektu i ich spread;
- liczbę okien `D → N → wolne → wolne` według zamrożonej semantyki T032;
- liczbę okien T034 `D/D/D`, `D/D/N`, `D/N/N`;
- jeżeli w danym wejściu aktywne są DAY_SHIFT_OFF/LEAVE_PLAN SOFT, liczbę
  Assignmentów kolidujących z tymi wejściami.

Do klasyfikacji D/N wolno użyć istniejącego canonical `classify_demand`; nie
powstaje drugi klasyfikator ani drugi solver.

#### B3.1 Kiedy wolno wystawić `FAIRNESS_PASS`

PASS wolno wystawić wyłącznie, gdy oczekiwany wynik fairness został ustalony
**przed PLAN** z danych wejściowych i istniejącej decyzji OWNERA, bez szukania
lepszego grafiku po fakcie.

T043 obowiązkowo ma co najmniej kontrolne przypadki symetryczne:

- wszyscy LOCAL mają identyczną eligibility, brak absencji i indywidualnych
  reguł, identyczny target i brak EXTERNAL;
- dla czystego D/N 12 h atomem podziału jest jedna 12 h służba;
- dla czystego H24 atomem podziału jest jedna 24 h służba, nie dwa niezależne
  komponenty;
- dla `R` identycznych LOCAL i `N` identycznych atomów pracy minimalny możliwy
  spread actual hours wynosi `0`, gdy `N % R == 0`, w przeciwnym razie dokładnie
  jeden atom pracy;
- ponieważ targety są identyczne, ten sam rozkład jest również minimalnym
  możliwym rozrzutem procentu realizacji targetu dla tej klasy.

Jeżeli gotowy grafik w takiej klasie osiąga tę z góry znaną granicę i nie ma
sprzeczności z pozostałymi dokładnie sprawdzalnymi SOFT, może dostać
`FAIRNESS_PASS`. Jeżeli ją przekracza, dostaje `FAIRNESS_FAIL` i reproduktor.

`WEEKDAY_12H_WEEKEND_24H`, scenariusze z absencją, DAY_ONLY albo inną asymetrią
nie dostają automatycznie PASS tylko dlatego, że solver zwrócił
`optimization_complete=True`. Jeżeli nie istnieje dla nich osobny zamrożony,
niezależny oracle, dostają `FAIRNESS_UNPROVEN` i pozostają widoczne jako
nie-zielone wyniki diagnostyczne.

Znany OWNER-T041-01 z brakującym targetem pozostaje osobnym istniejącym pionem
kalibracyjnym, poza głównym generatorem T043. Nie dodawać brakującego targetu do
portfela tylko po to, by uzyskać łatwy PASS.

#### B3.2 Czego evaluator fairness nie robi

- nie szuka innego grafiku;
- nie uruchamia drugiego CP-SAT;
- nie zmienia danych wejściowych;
- nie tworzy nowego progu typu „do X godzin jest sprawiedliwie”;
- nie uznaje `optimization_complete=True` za niezależny dowód fairness;
- nie zamienia `FAIRNESS_FAIL/UNPROVEN` na PASS po późniejszym wsparciu EXTERNAL
  lub REPLAN. Każdy etap ma własny wynik.

### B4. Uczciwy `DECISION_REQUIRED`

- payload nie jest całkowicie pusty;
- raport zachowuje blokujące demandy, osoby/warunki, load blocker i opcje;
- pierwszy wynik pozostaje niezmieniony;
- testowa ścieżka EXTERNAL może zebrać drugi wynik, ale nie usuwa pierwszego;
- certyfikowany przez generator czysty obiekt zwracający podejrzane
  `DECISION_REQUIRED` dostaje failure JSON do późniejszej diagnozy produktu.

### B5. REPLAN reaguje na zmianę, ale niczego nie poprawia za solver

Raport zachowuje stan przed zmianą i po REPLAN: Assignmenty, godziny, fairness,
produktowy validate i decyzje. Symulator nie wymusza konkretnego poprawionego
grafiku. Zły REPLAN jest wynikiem badania i dostaje reproduktor.

### B6. Rozliczenie kwartalne

Obowiązkowy pion z 4.3 raportuje dla każdego z 5 LOCAL i każdego miesiąca:

- target_hours;
- actual PRIMARY hours;
- product month_balance;
- product quarter_balance;
- product unresolved_carryover;
- niezależnie policzony expected month_balance i running quarter balance;
- wynik `QUARTER_BALANCE_PASS/FAIL`.

Warunek PASS jest wyłącznie arytmetyczny i nie zależy od tego, czy miesięczny
grafik był „ładny”. Jeżeli solver da nierówny, ale wybrany grafik, jego realne
godziny są używane jako wejście do rachunku — Symulator nie podmienia ich na
wzorcowe.

### 5.1 Artefakty

Jawne uruchomienie pełnego raportu tworzy na exact SHA:

- `tasks/ROTA-T043/round_01/tests/coordinator_report.md`;
- `tasks/ROTA-T043/round_01/tests/coordinator_report.json`;
- osobny failure JSON dla każdego czerwonego lub nieudowodnionego przypadku,
  który wymaga dalszej diagnozy.

JSON przechowuje pełne wejście, wynik, Assignmenty, fairness facts, quarter
facts, seed i gotową komendę reprodukcji. Zwykły pytest zapisuje wyłącznie do
`tmp_path` i nie nadpisuje T038/T039.

## 6. Checkpoint C — bramka zaufania do testów

Nie przepisujemy około 1100 testów i nie kasujemy wszystkich mocków. Mock może
być poprawny lokalnie, ale nie może być jedynym dowodem zachowania widocznego
dla koordynatora.

### 6.1 Klasy dowodu

- `REAL_UI` — browser + frontend + router + baza + produkt;
- `REAL_API` — TestClient + router + SQLite + aplikacja/solver;
- `REAL_APPLICATION` — prawdziwy assembler/solver/validate bez HTTP;
- `UNIT_OR_ADAPTER` — ręczny stan albo mock;
- `BENCHMARK_ONLY` — test generatora/benchmarku, nie wynik produktu.

Dwie ostatnie klasy nie mogą być przedstawiane OWNEROWI jako dowód całego
programu.

### 6.2 Minimalna mapa zaufania

Sprawdzić istniejące testy dotyczące:

- PLAN/wyboru kandydata;
- fairness i H24;
- urlopu/L4 przed PLAN i REPLAN;
- nakładających się demandów;
- EXTERNAL_SUPPORT;
- targetu, REPLAN i WorkBalance quarter carry-in;
- ostrzeżeń oraz wyniku widocznego w UI.

Jeżeli zachowanie ma wyłącznie mock/ręczny PlanningState/benchmark, dodać albo
przerobić najmniejszy prawdziwy pion. Nie duplikować dużych macierzy.

### 6.3 Prawdziwy browser

Jeden mały Playwright flow bez stubowania sieci:

1. koordynator widzi obiekt i właściwą liczbę osób;
2. ustawia target lub jedną nieobecność;
3. naciska PLAN;
4. widzi status oraz godziny/ostrzeżenie odpowiadające API.

To sprawdza wiring UI, nie wszystkie scenariusze solvera.

### 6.4 Kalibracja na znanych błędach

Na tymczasowym worktree, bez commitowania mutacji produktu, auditor wykonuje
trzy małe próby:

1. przywrócenie starego błędu H24 `occupancy=2*x` traktowanego jak Boolean;
2. wyłączenie fallback fairness dla brakującego targetu i uruchomienie
   istniejącego pionu
   `tests/test_t041_checkpoint_a.py::test_t41_a01_one_missing_target_splits_equally_across_all_five`;
3. przywrócenie starego geometrycznego podwójnego liczenia legalnie
   nakładających się demandów.

Właściwy pion musi paść dla każdej mutacji i przejść na finalnym SHA. Jeżeli
pozostaje zielony, test nie chroni klasy błędu i ma zostać poprawiony. Nie
modyfikować generatora T043 pod mutację.

## 7. Narzędzia, których T043 nie dodaje

T043 nie dodaje Hypothesis, Schemathesis, mutmut ani pełnego branch-coverage
jako nowej bramki. Jeden realny Playwright vertical i trzy kontrolowane mutacje
wystarczają do tego tasku. Rozszerzenia można ocenić po wyniku T043.

## 8. PREIMPLEMENTATION REDUCTION GATE

| Element | SOURCE | Konieczność | Redukcja |
|---|---|---|---|
| generator 5/10 | OWNER | prawdziwy roster | 5/10; bez reaktywnego LOCAL |
| target miesiąca | OWNER + niezależna fixture 2026 | prawdziwe wejście | kalendarz + kontrole 160/176 |
| portfel 20 | OWNER | różne miesięczne wejścia | seed + ledger + reprodukcja |
| EXTERNAL po decyzji | OWNER | bezobsługowy drugi etap testu | jeden EXTERNAL; pierwszy wynik zachowany |
| evaluator fairness | OWNER R4 + T032/T034/T041 | każdy grafik musi być oceniony | PASS tylko przy frozen oracle; FAIL/UNPROVEN zachowane, bez drugiego solvera |
| product validate | istniejący owner | stan HARD zaimplementowany w produkcie | bez claimu o całym prawie |
| REPLAN | istniejący owner | reakcja na zmianę | wynik oceniany, nie poprawiany |
| quarter Q3 2026 | OWNER R4 + istniejący WorkBalance | prawdziwy carry-in jednego obiektu | jeden prosty pion 3-miesięczny, niezależne dodawanie salda |
| Markdown + JSON | OWNER | czytelność/reprodukcja | jeden model danych, dwa renderery |
| jeden UI vertical | luka API/UI | wiring | jeden flow |
| 3 mutacje | znane incydenty | test ma umieć upaść | tymczasowy worktree |

Nie powstają:

- nowy solver, optimizer ani drugi validator;
- nowy threshold fairness;
- reaktywne LOCAL;
- wsparcie przed pierwszym PLAN;
- własny rachunek urlopu/L4;
- Cross-Site;
- częściowa druga warstwa ani SPLIT_NIGHT_12_8;
- sieć w runtime;
- masowa migracja testów;
- zmiany produktu w `rota/**`, `api/**`, `frontend/src/**`, `benchmarks/**`.

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

`frontend/e2e/t043-coordinator-confidence.spec.ts` i `failures/` są nowe tylko
jeśli potrzebne. Nie tworzyć frameworka/helperów poza zakresem, jeżeli istniejący
helper wystarcza.

Zabronione:

- `rota/**`, `api/**`, `frontend/src/**`, `benchmarks/**`;
- zmiana kontraktu produktu pod wygodny test;
- ręczne Assignment/demand/wzorcowy grafik;
- mock wyniku PLAN/REPLAN/validate/analityki w bramce zaufania;
- drugi solver/optimizer/validator;
- własny prawny validator;
- Cross-Site i współdzieleni pracownicy pomiędzy obiektami;
- dodawanie brakującego targetu jako osi głównego generatora;
- usuwanie/wyłączanie starych testów bez osobnego dowodu;
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
Pierwszy plik jest konsumowany przez drugi; pozostałe trafienia to historyczne
briefy/raporty albo niezależne symbole o tej samej nazwie. R4 nie rozszerza
TASK_SCOPE na produkt.

Przed implementacją/audytem należy dodatkowo przeczytać istniejących ownerów,
na których opiera się evaluator i quarter: T032/T034/T041 oraz
`rota/balance.py`, `rota/application/assembler.py` i
`rota/application/balance_read.py`. To jest analiza kontraktu, nie zgoda na ich
modyfikację.

## 11. Odbiór i sposób testowania

### Checkpoint A

- testy generatora: 5/10, istniejące kształty, fixture 2026, targety 160/176,
  brak reaktywnego LOCAL, granice urlopu/L4;
- jeden realny API vertical;
- jeden realny `DECISION_REQUIRED` z testową ścieżką EXTERNAL i zachowaniem
  pierwszego wyniku;
- tylko create-person używa decision id.

### Checkpoint B

- celowane miesięczne przypadki jednej/dwóch warstw i trzech istniejących
  kształtów;
- każdy FEASIBLE ma `PRODUCT_VALIDATE_*` i `FAIRNESS_PASS/FAIL/UNPROVEN`;
- co najmniej kontrolne symetryczne D/N i H24 mają z góry policzalny fairness
  oracle;
- wynik fairness nie jest korygowany przez zmianę scenariusza;
- jeden REPLAN ze stanem przed/po;
- pełny portfel 20 raz na finalnym SHA;
- obowiązkowy Q3 lipiec→sierpień→wrzesień na jednym Site/jednej bazie z
  `QUARTER_BALANCE_PASS/FAIL`;
- raport Markdown/JSON i failure JSON dla czerwonych/nieudowodnionych wyników;
- nie uruchamiać całej suity repo.

### Checkpoint C

- jeden realny Playwright flow;
- klasyfikacja testów z 6.2;
- trzy kontrolowane mutacje i dowód, że właściwy pion je wykrywa;
- TypeScript/build tylko jeśli dotknięto e2e/helpera wymagającego kompilacji.

Odbiór końcowy T043 nie wymaga, by aktualny solver przeszedł wszystkie
scenariusze na zielono. Wymaga, by Symulator **uczciwie sklasyfikował i zachował**
wyniki. Dowody końcowe:

1. exact SHA;
2. raport z godzinami, targetami, Assignmentami i membership każdego przypadku;
3. JSON i komendy reprodukcji;
4. jawna lista FEASIBLE, DECISION_REQUIRED, TECHNICAL_ERROR oraz wykrytych
   defektów;
5. dla każdego FEASIBLE jawny wynik product validate i fairness;
6. żaden `FAIRNESS_UNPROVEN` nie jest pokazany jako zielony;
7. pierwszy błędny wynik nie znika po EXTERNAL albo REPLAN;
8. żaden przebieg nie zwiększa liczby LOCAL ponad 5/10;
9. dokładny porządek testowego EXTERNAL: create-person z decision id,
   membership null, support-window null;
10. fixture kalendarza 2026 i kontrole 160/176;
11. kontrolny Q3 pokazuje miesięczne i narastające saldo dla każdego LOCAL oraz
    wykrywa każdą różnicę względem niezależnego dodawania;
12. trzy kontrolowane mutacje robią właściwe piony czerwone;
13. lista starych testów UNIT/BENCHMARK, które nie są przedstawiane jako dowód
    działania programu;
14. Cross-Site nie występuje w T043.

## 12. Warunki zatrzymania

Implementer zatrzymuje się i zgłasza problem, jeżeli:

- nie da się przed PLAN jednoznacznie zbudować rosteru 5/10 dla dozwolonej
  pełnej warstwy;
- reakcja EXTERNAL wymaga zmiany produktu albo parsowania tekstu opcji;
- nie da się zachować decision-link bez zmiany produktu;
- raport godzin/fairness wymaga nowego endpointu produktu;
- aby wystawić FAIRNESS_PASS trzeba byłoby uruchomić drugi optimizer albo
  wymyślić próg — wtedy wynik ma być `FAIRNESS_UNPROVEN`, nie PASS;
- kwartalny pion wymaga ręcznego seedowania Assignmentów — wtedy
  `QUARTER_BLOCKED`, reproduktor i stop, bez obchodzenia solvera;
- potrzebna jest zmiana poza TASK_SCOPE;
- kontrolowana mutacja pozostaje zielona i nie da się jej wykryć bez nowego
  zachowania produktowego — zgłosić lukę orakla, nie zgadywać.

## 13. Pytania do niezależnego review przed implementacją

1. Czy brief jednoznacznie mówi, że Symulator bada aktualny solver i nigdy go
   nie poprawia ani nie kalibruje wejścia pod PASS?
2. Czy każdy FEASIBLE ma automatyczny status fairness, a `UNPROVEN` nie może być
   zielone?
3. Czy PASS fairness jest dozwolony tylko przy oracle ustalonym przed PLAN i
   nie wymaga drugiego solvera/progu wymyślonego przez implementatora?
4. Czy zły grafik i pierwszy `DECISION_REQUIRED` pozostają trwałym reproduktorem
   także po EXTERNAL/REPLAN?
5. Czy Q3 2026 jest prawdziwym przebiegiem jednego Site/jednej bazy przez trzy
   miesiące i używa produkcyjnego carry-in?
6. Czy niezależny oracle kwartalny jest tylko arytmetyką actual-hours minus
   target i sumą narastającą, bez ręcznych Assignmentów?
7. Czy `PRODUCT_VALIDATE_PASS` nie jest przedstawiane jako niezależny audyt
   całego prawa?
8. Czy prawdziwy koordynator po decyzji ręcznie dodaje nową osobę do LOCAL, a
   EXTERNAL pozostaje wyłącznie automatyzacją testową?
9. Czy Cross-Site pozostaje całkowicie poza T043?

Do zamknięcia re-review: **CC READ-ONLY — NIE IMPLEMENTOWAĆ**.

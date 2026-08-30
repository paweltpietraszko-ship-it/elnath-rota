# ROTA-T043 — Wiarygodny Symulator Koordynatora i bramka zaufania do testów

Status: **ARCHITECT_CORRECTED R3 — READY FOR NIEZALEŻNY PREIMPLEMENTATION RE-AUDIT — CC READ-ONLY / BEZ IMPLEMENTACJI**

Base: `main@c25c73e0332158bae703109e770f3cf83fd970a7`

Autor briefu: Codex jako niezależny tester. CC napisał T038/T039 i celowo nie
projektuje własnej poprawki. Źródłem zlecenia jest
`arch/REQUEST_SYMULATOR_INDEPENDENT_DIAGNOSIS_2026-08-30.md` na
`docs/symulator-repair-diagnosis-request@f248c07d3e6f65164080863b47b694118477574b`.

Korekta architekta R3 odpowiada wyłącznie na pięć potwierdzonych uwag z:

- `tasks/ROTA-T043/round_01/tests/tests_r1.txt`;
- `tasks/ROTA-T043/round_01/tests/tests_r2.txt` — OWNER_CORRECTED: Cross-Site
  wycofane z T043 i zamknięte, nie wraca jako warunek ani pytanie;
- `tasks/ROTA-T043/round_01/tests/tests_r3.txt` — pięć pozostałych uwag
  potwierdzonych file:line przez CC.

Ta korekta nie dodaje nowego zachowania produktu ani nowej funkcji Symulatora.
Zawęża wyłącznie to, co T043 ma prawo nazywać dowodem.

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
  uruchamia **testową ścieżkę wsparcia**: przez produkcyjne operacje tworzy
  jedną syntetyczną osobę `EXTERNAL_SUPPORT`, bez targetu, dodaje jej okno i
  ponawia PLAN;
- ta automatyzacja istnieje wyłącznie po to, żeby test bez człowieka mógł
  sprawdzić oba etapy: wykrycie braku oraz grafik po udzieleniu pomocy;
- **nie jest to odtworzenie produkcyjnego ręcznego dodania LOCAL ani zachowanie
  produktu**. LOCAL i EXTERNAL mają inne zasady: LOCAL ma target i uczestniczy
  w odpowiednim bilansowaniu, EXTERNAL_SUPPORT nie;
- w zwykłym programie solver nadal ma zatrzymać się na decyzji, a prawdziwy
  koordynator ręcznie wybiera dalsze działanie;
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
uruchamia testową ścieżkę wsparcia: utworzenie SIM-EXTERNAL, membership
EXTERNAL_SUPPORT, okna i ponowny PLAN przez produkcyjny backend. To pozwala
kontynuować automatyczny eksperyment bez człowieka; nie jest funkcją produktu
i nie jest dowodem produkcyjnego ręcznego dodania LOCAL. Nie dodawaj reaktywnie
LOCAL, nie przewiduj z góry potrzeby wsparcia i nie dopasowuj wejść do wyniku
solvera.
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
- wartość nie jest udziałem `720 / 5` ani stałą `168`/`160`;
- runtime testu nie korzysta z Internetu.

Kalendarz użyty jako wejście Symulatora **nie może być wymyślony przez ten sam
kod, który później sprawdza target**. T043 używa zamrożonej, niezależnej fixture
urzędowej dla 2026 r.:

- lista polskich świąt ustawowo wolnych w 2026 r. jest przepisana jako stałe
  dane testowe z urzędowego źródła i nie jest wyliczana przez
  `nominal_monthly_hours_kp()`;
- źródło kalendarza: Zielona Linia / Centrum Informacyjne Służb Zatrudnienia,
  „Święta wolne od pracy w 2026 roku”:
  https://zielonalinia.gov.pl/swieta-wolne-od-pracy-w-2026-roku/;
- niezależna tabela kontrolna wymiaru godzin 2026 pochodzi z urzędowej tabeli
  Powiatowego Urzędu Pracy w Sosnowcu:
  https://sosnowiec.praca.gov.pl/strona-glowna/-/asset_publisher/Qat7ebECUfDp/content/id/56152826/pop_up;
- dwa obowiązkowe przypadki kontrolne nie są liczone przez generator:
  **styczeń 2026 = 160 h** oraz **wrzesień 2026 = 176 h**;
- dla stycznia fixture zawiera co najmniej 1 i 6 stycznia jako święta; dla
  września nie ma polskiego święta obniżającego wymiar;
- pełny portfel T043 losuje miesiące wyłącznie z roku 2026 objętego tą fixture.
  Rozszerzenie na inne lata nie należy do T043;
- dopiero po zgodności zamrożonego kalendarza z wybranym miesiącem kalkulator
  może wyliczyć target używany jako wejście produkcyjne. Jeżeli kalkulator nie
  odtworzy zamrożonej wartości kontrolnej, test generatora ma być czerwony;
- podczas runtime nie ma pobierania danych z sieci.

Ta fixture sprawdza wejście i matematykę targetu. Nie czyni Symulatora
niezależnym audytorem całego prawa pracy.

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
  **drivera testowego**, by uruchomił testową ścieżkę wsparcia; nie wolno
  uzależniać tego od brzmienia albo parsowania `unblocking_options`;
- driver tworzy jedną nową osobę `SIM-EXTERNAL-*` jako `EXTERNAL_SUPPORT`, bez
  targetu, i okno przez istniejące produkcyjne operacje;
- ponieważ utworzenie tej nowej osoby jest pierwszym materialnym zapisem po
  decyzji, **wyłącznie create-person niesie aktualne
  `responds_to_decision_required_id`**;
- następujące po nim attach-membership `EXTERNAL_SUPPORT` oraz utworzenie okna
  wsparcia przekazują `responds_to_decision_required_id = null`, bo pierwszy
  materialny zapis już unieważnił poprzednie ID decyzji;
- dopiero po tych trzech zapisach driver ponownie naciska PLAN;
- raport nazywa ten etap dokładnie **„testowa ścieżka wsparcia EXTERNAL”** i
  nie przedstawia go jako produkcyjnego ręcznego dodania LOCAL;
- raport osobno zachowuje wynik pierwszego PLAN, payload decyzji, ID powiązane
  z pierwszym zapisem, utworzoną osobę/membership/okno, wynik drugiego PLAN i
  faktyczne użycie osoby;
- ten krok nie może zmieniać liczby LOCAL ani zostać przeniesiony do produktu.

### 2.6 Brak grafiku może być prawidłowym wynikiem

`DECISION_REQUIRED` nie jest automatycznie błędem. Jest poprawnym, użytecznym
wynikiem, jeżeli scenariusz rzeczywiście blokuje obsadę i payload zawiera
konkretny demand, blocker albo opcję działania. Całkowicie pusty payload jest
błędem narzędzia lub produktu i nie może przejść jako PASS.

### 2.7 Granica twierdzeń o prawie i bilansie kwartalnym

T043 nie rozszerza Symulatora o drugi zestaw reguł prawa pracy.

- produkcyjne `validate()` dowodzi wyłącznie zgodności kandydata z aktualnymi
  regułami zaimplementowanymi w produkcie;
- raport nie używa określeń „zgodny z Kodeksem pracy”, „legalny według prawa”
  ani równoważnych na podstawie samego `validate()`;
- T043 nie dodaje własnego checkera 11 h/35 h/16 h/24 h ani kopii reguł HARD;
- kontrola art. 130 w 2.3 dotyczy wyłącznie zamrożonego wejścia
  `target_hours`, nie certyfikacji całego grafiku.

T043 również **nie certyfikuje kwartalnego przenoszenia salda godzin**.
Każdy obiekt głównego portfela pozostaje niezależnym przebiegiem miesiąca, a
REPLAN w T043 sprawdza zmianę w tym samym miesiącu. Istniejący mechanizm
quarter carry-in pozostaje zachowaniem produktu, ale nie jest dowodem ani
obietnicą raportu T043. Nie dodajemy wielomiesięcznego scenariusza tylko po to,
żeby rozszerzyć zakres Symulatora.

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
- PLAN, odczyt decyzji, ewentualna testowa ścieżka wsparcia EXTERNAL, ponowny
  PLAN;
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

- miesiąc z zamrożonego kalendarza 2026 (w tym miesiące krótkie, święta i
  kontekst granicy miesiąca);
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
`WEEKDAY_12H_WEEKEND_24H` = 5 LOCAL, dwie pełne warstwy = 10 LOCAL, styczeń
2026 = 160 h targetu i wrzesień 2026 = 176 h targetu. Nie są treścią głównego
raportu i nie wolno kalibrować pod nie solvera.

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

### B2. Zgodność z produkcyjnym validate

Każdy zwrócony kandydat używany w raporcie przechodzi przez produkcyjne
`select_candidate()`, a następnie produkcyjny odczyt/revalidate. Symulator nie
odtwarza COVERAGE, REST, NIGHT-STREAK, urlopu ani L4 własnym kodem.

W raporcie wynik tej kontroli ma być nazwany np. `PRODUCT_VALIDATE_PASS/FAIL`
lub prostym polskim odpowiednikiem „przeszedł/nie przeszedł reguły sprawdzane
przez program”. **Nie wolno na tej podstawie pisać, że cały grafik został
niezależnie sprawdzony z Kodeksem pracy.**

### B3. Godziny i sprawiedliwość widoczne dla człowieka

Raport pokazuje dla każdego LOCAL:

- target godzin;
- efektywny target zwrócony przez produkcyjną analitykę;
- faktycznie zaplanowane godziny;
- liczbę i długości zmian;
- różnicę względem najmniej i najbardziej obciążonego LOCAL.

Główny portfel Symulatora **nie wydaje własnego automatycznego werdyktu
„sprawiedliwy / niesprawiedliwy”**. Zgodnie z 2.3 każdy wygenerowany LOCAL ma
jawny `target_hours`; T043 nie dodaje specjalnego przypadku z brakującym
targetem tylko po to, żeby uzyskać łatwy oracle. Dla scenariuszy z kompletnymi
targetami, urlopem, L4 albo indywidualną regułą raport pokazuje liczby i
produkcyjny effective target jako dowód diagnostyczny dla OWNERA. Nie zgaduje,
czy istniał lepszy legalny grafik i nie buduje drugiego optymalizatora.

Znany OWNER-T041-01 z brakującym targetem pozostaje osobnym, już istniejącym
pionem testowym. Służy wyłącznie do kalibracji bramki zaufania w 6.4; nie jest
nową osią generatora T043 i nie trafia do głównego portfela Symulatora.

### B4. Uczciwy `DECISION_REQUIRED`

- payload nie jest całkowicie pusty;
- raport pokazuje blokujące demandy, osoby/warunki, load blocker i opcje;
- Symulator nie oznacza z góry przypadku jako „wymagający wsparcia”; zapisuje
  pierwsze `DECISION_REQUIRED`, automatycznie wykonuje testową ścieżkę wsparcia
  EXTERNAL opisaną w 2.5 i porównuje oba etapy;
- jeśli certyfikowany przez generator czysty obiekt bez absencji zwraca
  `DECISION_REQUIRED`, zachować failure JSON. Nadal wolno wykonać reakcję
  wsparcia dla zebrania dowodu, ale wynik pierwszego PLAN nie przestaje być
  widoczny i nie wolno osłabiać jego danych wejściowych.

### B5. REPLAN reaguje na zmianę

Raport zachowuje zestaw godzin i przypisań przed zmianą oraz po REPLAN. Pokazuje
co zmieniono w wejściu i czy backend ponownie zbilansował cały dostępny miesiąc.
Nie wymusza ręcznie konkretnego grafiku.

B5 **nie jest testem kwartalnego carry-in**. T043 nie tworzy w tym celu
kolejnych miesięcy tego samego obiektu i nie przedstawia tego wyniku jako dowodu
rozliczenia kwartału.

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
2. wyłączenie terminu równego podziału dla brakującego targetu — auditor
   uruchamia istniejący prawdziwy pion
   `tests/test_t041_checkpoint_a.py::test_t41_a01_one_missing_target_splits_equally_across_all_five`,
   który zamraża OWNER-T041-01 i oczekuje 144 h dla każdego z pięciu LOCAL;
   nie dodaje brakującego targetu do generatora T043 i nie modyfikuje tego
   testu bez nowego dowodu, że istniejący pion nie wykrywa mutacji;
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
| target miesiąca | OWNER + art. 130 + zamrożona fixture urzędowa 2026 | prawdziwe wejście koordynatora bez samosprawdzania generatora | kalkulator korzysta z niezależnego kalendarza; obowiązkowe kontrole 160/176 |
| seedowany portfel 20 obiektów | OWNER | różne wejścia zamiast benchmarku | kombinacje zamrożonych osi, ledger i reprodukcja z seedu; obiekty niezależne |
| reakcja po `DECISION_REQUIRED` | OWNER + istniejący ControlPanel flow | bezobsługowa **testowa ścieżka wsparcia EXTERNAL** | create-person niesie decision id; membership/window null; bez zmiany LOCAL |
| godziny/spread | prośba OWNER + OWNER-T041-01 jako osobna kalibracja | ujawnia bzdury widoczne ręcznie | Symulator tylko raportuje godziny/spread; mutacja fairness używa istniejącego pionu T041, bez nowej osi generatora |
| produkcyjne validate | istniejący owner | zgodność z regułami sprawdzanymi przez produkt | select/revalidate; bez claimu o całym prawie i bez kopii walidatora |
| REPLAN | istniejący owner | reakcja na zmianę w tym samym miesiącu | bez rozszerzenia T043 o certyfikację quarter carry-in |
| Markdown + JSON | prośba OWNER | czytelność i reprodukcja | jeden model danych, dwa renderery |
| jeden UI vertical | luka między API i ekranem | sprawdza realne kliknięcie | jeden flow, nie macierz browserowa |
| 3 mutacje kontrolne | znane incydenty | dowód, że test umie upaść | tymczasowy worktree, bez nowej zależności |

Usunięte z propozycji:

- nowy solver, validator albo checker reguł HARD/prawa pracy;
- dowolna obsada 4–9 i reaktywne zatrudnianie LOCAL;
- osoba lub aktywne wsparcie przed pierwszym PLAN;
- przedstawianie testowego EXTERNAL jako produkcyjnego dodania LOCAL;
- liczenie urlopu/L4 w generatorze;
- sieć w trakcie testu;
- własny automatyczny oracle fairness w głównym portfelu Symulatora;
- dodawanie brakującego targetu jako nowej osi generatora T043;
- wielomiesięczny przebieg tylko po to, by certyfikować bilans kwartalny;
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
- własny prawny validator albo nowy checker fairness dla złożonych przypadków;
- test Cross-Site lub współdzielonych pracowników pomiędzy obiektami w T043;
- dodawanie brakującego targetu jako nowej osi głównego generatora T043;
- wielomiesięczny scenariusz kwartalny w T043;
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

Korekta R3 nie zmienia ownershipu ani TASK_SCOPE, więc nie dodaje kolejnego
mechanicznego `WHERE_MAP`. Pięć uwag zostało potwierdzonych file:line w R3;
przed implementacją audytor nadal ma przeczytać rzeczywiste wskazane ownery na
exact SHA, zgodnie z `AGENTS.md`.

## 11. Odbiór i sposób testowania

### Checkpoint A

- małe testy generatora bez solvera: znaczenie pełnych warstw 5/10, przykład
  D/N w tygodniu + H24 w weekend = 5, niezależna fixture kalendarza 2026,
  kontrolne targety styczeń=160/wrzesień=176, brak reaktywnego LOCAL oraz
  urlop/L4 w dozwolonych granicach;
- jeden wygenerowany prawdziwy API vertical;
- jeden `DECISION_REQUIRED` z testową ścieżką wsparcia EXTERNAL i dowodem, że
  liczba LOCAL nie wzrosła oraz tylko pierwszy zapis użył decision id.

### Checkpoint B

- celowane obiekty jednej i dwóch warstw oraz wariantu
  `WEEKDAY_12H_WEEKEND_24H`, z raportem faktycznych godzin;
- jawne oznaczenie wyniku produkcyjnego validate bez claimu „zgodne z prawem”;
- w głównym Symulatorze fairness jest wyłącznie raportowane jako liczby/spread,
  bez własnego PASS/FAIL i bez brakującego targetu jako osi generatora;
- jeden przypadek testowej ścieżki wsparcia EXTERNAL po realnym, niepustym
  payloadzie;
- jeden REPLAN w tym samym miesiącu;
- pełny seedowany portfel 20 obiektów raz na finalnym SHA, z ledgerem pokrycia i
  raportem Markdown/JSON;
- nie uruchamiać całej suity repo.

### Checkpoint C

- jeden realny Playwright flow;
- klasyfikacja tylko testów z obszarów wskazanych w 6.2;
- trzy kontrolowane mutacje z 6.4 i dowód, że właściwy pion je wykrywa; mutacja
  fairness używa istniejącego T041, a nie nowej osi Symulatora;
- TypeScript/build tylko jeśli dotknięto testu e2e/helpera wymagającego
  kompilacji.

Odbiór końcowy nie brzmi „N testów PASS”. Oczekiwane dowody to:

1. exact SHA;
2. raport czytelny przez OWNERA z godzinami każdego pracownika;
3. JSON i komendy reprodukcji;
4. jawna lista scenariuszy FEASIBLE, DECISION_REQUIRED i defektów produktu;
5. dowód, że żaden przebieg nie zwiększył liczby LOCAL ponad 5/10, a każda
   osoba EXTERNAL powstała dopiero po pierwszym `DECISION_REQUIRED`;
6. dowód dokładnego porządku testowego EXTERNAL: create-person z decision id,
   membership null, support-window null;
7. dowód, że target nie sprawdza sam siebie: urzędowa fixture kalendarza 2026 i
   kontrolne 160/176 przechodzą niezależnie od wygenerowanego scenariusza;
8. jawne rozróżnienie „przeszedł produkcyjny validate” od „sprawdzony z prawem”;
9. główny raport nie wydaje własnego werdyktu fairness; znana klasa błędu
   brakującego targetu jest kalibrowana istniejącym pionem T041 poza portfelem
   Symulatora;
10. dowód, że bramka zrobiła się czerwona dla trzech znanych klas błędu;
11. lista starych testów, które pozostały UNIT/BENCHMARK i dlatego nie są
   używane jako dowód działania programu;
12. brak twierdzenia, że T043 przetestował kwartalne przenoszenie salda.

## 12. Warunki zatrzymania

Implementer zatrzymuje się i zgłasza problem, jeżeli:

- generator nie potrafi przed PLAN jednoznacznie przypisać 5 albo 10 LOCAL do
  dozwolonej pełnej warstwy obsady;
- automatyczna reakcja wymaga parsowania tekstu `unblocking_options` albo
  zmiany produktu — wystarczającym triggerem ma być niepusty
  `DECISION_REQUIRED`, a cała reakcja należy do drivera testowego;
- nie da się zachować istniejącego porządku decision-link dla testowego
  EXTERNAL bez zmiany produktu;
- raport godzin wymaga nowego endpointu lub zmiany produktu; najpierw wskazać,
  dlaczego obecny month view/analytics nie wystarcza;
- główny Symulator potrzebowałby nowego progu fairness albo drugiego
  optymalizatora — wtedy raportować liczby bez werdyktu i nie dodawać
  brakującego targetu jako obejścia;
- którykolwiek scenariusz wymaga ręcznego zbudowania wyniku;
- potrzebna jest zmiana poza TASK_SCOPE;
- kontrolowana mutacja pozostaje zielona i nie da się jej wykryć bez
  dopisania nowego zachowania produktowego — zgłosić lukę orakla, nie zgadywać.

## 13. Pytania do niezależnego review przed implementacją

1. Czy B2 i raport mówią wyłącznie o zgodności z produkcyjnym validate, bez
   przedstawiania tego jako niezależnego audytu całego prawa pracy?
2. Czy kalendarz 2026 i kontrolne targety 160/176 są zamrożoną fixture
   niezależną od kalkulatora/generatora, a runtime nie korzysta z sieci?
3. Czy główny Symulator tylko pokazuje godziny/spread bez własnego werdyktu
   fairness, a kalibracja brakującego targetu używa istniejącego pionu T041
   poza generatorem T043?
4. Czy raport i driver nazywają EXTERNAL testową ścieżką wsparcia i zachowują
   kolejność: pierwszy materialny zapis z decision id, kolejne dwa z null?
5. Czy T043 jawnie nie rości sobie dowodu kwartalnego carry-in i nie dodaje
   wielomiesięcznego scenariusza?
6. Czy Cross-Site pozostaje całkowicie poza T043 zgodnie z OWNER_CORRECTED R2?

Do zamknięcia re-review: **CC READ-ONLY — NIE IMPLEMENTOWAĆ**.

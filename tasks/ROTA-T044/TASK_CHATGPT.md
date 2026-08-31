# ROTA-T044 — TASK wykonawczy ChatGPT — Symulator Koordynatora Wariant B

Status: **READY_FOR_CC_DEVILS_ADVOCATE — CC READ-ONLY — NIE IMPLEMENTOWAĆ**

## 0. Źródła i obowiązujący stan

Ten plik jest zredukowanym Taskiem wykonawczym na podstawie zaakceptowanego kontraktu T044. Nie zastępuje historii decyzji w `brief.md`.

Obowiązujące źródła:

- branch: `task/ROTA-T044`;
- source brief R8: `tasks/ROTA-T044/brief.md` @ `b8fccffa4591fe979fae09a6915a35f161566e12`;
- niezależny reaudyt Codex R6: `tasks/ROTA-T044/round_01/tests/tests_r6.txt` @ `7c892a8ac1a2816e4f26c015ccc27a270b616c40` — **PASS**;
- product base wskazany przez brief: `main@1b6bfbf` po merge ROTA-T043;
- `AGENTS.md` — obowiązujące gate'y, w tym `WHERE_MAP`, reduction gate i zasady niezależnego audytu.

Jeżeli ten Task i `brief.md` wydają się sprzeczne, **STOP** i zgłoś konkretną różnicę. Nie wybieraj wygodniejszej wersji. Ten Task nie może tworzyć nowego zachowania poza finalnym R8.

## 1. Cel

Dodać **Wariant B Symulatora Koordynatora** jako testowy, stateful generator prawdziwych działań koordynatora przez istniejące API.

Wariant B ma przy każdym uruchomieniu badać nowe, poprawnie zbudowane obiekty i sekwencje działań. Ma obserwować rzeczywisty PLAN/REPLAN i zachowywać wynik produktu.

**Symulator nie poprawia solvera i nie ocenia jakości gotowego grafiku.** Jeżeli solver zwróci zły, dziwny lub niesprawiedliwy grafik, to jest wynik badania do późniejszego Tasku produktu. Wariant B nie zmienia wejścia po fakcie, nie szuka lepszego grafiku, nie buduje drugiego solvera/validatora/evaluatora.

Jedyna własna odpowiedzialność obliczeniowa Wariantu B to **kalkulator liczby LOCAL przed pierwszym PLAN**.

Wariant A z T043 pozostaje nietknięty i nadal pełni rolę deterministycznego czujnika regresji.

## 2. Granice bezwzględne

### 2.1 Wolno

- testowy kod Wariantu B;
- nowe, addytywne helpery w `tests/property/coordinator_simulator.py`;
- nowy `tests/property/test_coordinator_simulator_variant_b.py`;
- dodanie zależności `hypothesis` do `pyproject.toml`;
- realny `TestClient`, SQLite `:memory:`, istniejące endpointy i prawdziwy backend;
- raporty/pomiary/reproduktory w `tasks/ROTA-T044/round_01/tests/**`.

### 2.2 Nie wolno

- żadnych zmian `rota/**`, `api/**`, `frontend/src/**`, `benchmarks/**`;
- zmieniać działania istniejącego Wariantu A;
- zmieniać produktu pod wygodę Symulatora;
- ręcznie tworzyć wynikowych Assignmentów lub wzorcowego grafiku;
- monkeypatchować PLAN/REPLAN/validate/analitykę;
- budować własny checker fairness, kwartalny oracle, prawny validator albo drugi solver;
- Cross-Site;
- pełny UI/Playwright;
- evaluator zewnętrzny lub wywołanie modelu;
- Internet w runtime testu;
- reaktywnie dodawać LOCAL po wyniku solvera.

## 3. OWNER-01 — kalkulator obsady jest jednym, prostym ownerem

Kalkulator działa **raz, przed pierwszym PLAN**, wyłącznie na wygenerowanym wzorze zapotrzebowania. Nie zna urlopów, L4, odpoczynków, DAY_ONLY ani wyniku solvera.

### 3.1 Zakres wymagań

`required_primary_count` dla wygenerowanego `(rodzaj zmiany, dzień tygodnia)` należy do `{1, 2}` i może różnić się między wierszami/dniami.

Mieszany przypadek OWNERA musi być reprezentowalny:

- dni robocze: `required_primary_count = 2`;
- weekend: `required_primary_count = 1`.

Nie wolno cofnąć tego do jednej wartości dla całego obiektu.

### 3.2 Kalkulator warstwowy

Dla `k = 1..2`:

1. zsumuj godziny occurrence, dla których `required_primary_count >= k`;
2. policz potrzebną liczbę osób dla tej warstwy jako `ceil(godziny_warstwy / nominal_monthly_hours_kp(m, POLISH_2026_HOLIDAYS))`;
3. wykonaj to dla każdego z 12 miesięcy 2026;
4. dla danej warstwy weź maksimum z 12 miesięcy;
5. wynik kalkulatora = suma wyników warstw.

Warstwa bez aktywności wnosi `0`.

**Nie ma żadnego marginesu urlopowego ani L4.** Maksimum po miesiącach jest elementem rachunku na rzeczywistym kalendarzu, nie zapasem bezpieczeństwa.

Kalkulator nie tworzy Assignmentów, nie wybiera osób do zmian, nie sprawdza odpoczynku i nigdy nie jest uruchamiany ponownie po zobaczeniu wyniku PLAN/REPLAN.

### 3.3 Obowiązkowe kontrolne oracle kalkulatora

Przed podłączeniem do Hypothesis muszą istnieć małe deterministyczne testy:

- `T44-B-CALC-01`: D/N 12h, wymóg `1` cały tydzień → **5 LOCAL**;
- `T44-B-CALC-02`: D/N 12h, wymóg `2` cały tydzień → **10 LOCAL**;
- `T44-B-CALC-03`: D/N 12h, robocze=`2`, weekend=`1` → **9 LOCAL**.

Te trzy liczby są kontraktem, nie orientacyjną statystyką.

## 4. OWNER-02 — swobodny generator obiektu

Wariant B nie wybiera z zamkniętej listy gotowych kształtów Wariantu A.

Dla obiektu generator wybiera w dozwolonych granicach:

- `month`: jeden z 12 miesięcy 2026;
- obecność D/N/H24 w poszczególnych dniach tygodnia;
- godziny rozpoczęcia/zakończenia w ramach istniejącego katalogu produktu;
- `required_primary_count` per wiersz/dzień z `{1,2}`;
- istniejący tryb obiektu/regime i dozwolone wejścia koordynatora;
- nieobecności opisane w §5.

Wielokrotne wpisy i legalne overlap'y katalogu **nie są automatycznie odrzucane**.

Jedyny wzór odrzucany/przelosowywany przed budową Site to taki, który daje **zero zapotrzebowania w całym miesiącu**.

Reprezentacja wewnętrzna jest szczegółem implementacji. Wolno grupować równoważne dni w jeden wiersz katalogu, ale nie wolno utracić semantyki per dzień/wiersz ani zmienić `required_primary_count`.

Po wygenerowaniu obiektu i przed PLAN:

`declared_LOCAL_count == layered_headcount_calculator(generated_demand_pattern)`

musi być zawsze prawdą.

## 5. OWNER-03 — nieobecności to wejścia koordynatora, nie element kalkulatora

### 5.1 Urlop

Urlop jest wpisywany przez istniejące API dostępności.

- bloki mają długość **10 dni roboczych** albo **5 dni roboczych**;
- kolejni LOCAL dostają naprzemiennie 10/5 dni roboczych według kolejności rosteru, deterministycznie względem wygenerowanego obiektu/seeda;
- bloki różnych LOCAL nie nakładają się na siebie;
- `liczba_LOCAL == 1` **nie wyłącza urlopu** — jedyny LOCAL również dostaje blok na tych samych zasadach;
- nie ma rocznego budżetu urlopu do bilansowania w Symulatorze;
- urlop nie wpływa na kalkulator liczby LOCAL.

### 5.2 L4

- jeden blok **5 dni**;
- decyzja o L4 jest losowana **dokładnie raz na obiekt**, nie per krok state machine;
- szansa ma być około **25%**;
- nie wolno implementować sztywnego schematu typu „co czwarty przypadek”;
- osoba z L4 musi należeć do zadeklarowanego LOCAL, nigdy do EXTERNAL;
- działa również dla `liczba_LOCAL == 1`;
- L4 nie wpływa na kalkulator liczby LOCAL.

Dokładny mechanizm strategii Hypothesis realizujący ~25% jest detalem implementacyjnym, ale powyższa semantyka nie może się zmienić.

## 6. OWNER-04 — Hypothesis stateful

Dodać `hypothesis` jako normalną zależność projektu w `pyproject.toml`.

Wariant B używa `RuleBasedStateMachine` albo równoważnego stateful API Hypothesis i wykonuje prawdziwe operacje produktu.

Obowiązkowe ustawienia:

- `database=None`;
- `deadline=None`;
- `derandomize=False`.

Każdy przykład Hypothesis ma:

- świeżą SQLite `:memory:`;
- nowy Site;
- własny wygenerowany immutable input/spec;
- jawne preconditions dla operacji zależnych od wcześniejszego stanu.

Przykłady preconditions:

- `select_candidate` dopiero po FEASIBLE z kandydatem;
- REPLAN dopiero po istniejącym current ScheduleVersion;
- reakcja EXTERNAL dopiero po rzeczywistym, niepustym `DECISION_REQUIRED`.

Nielegalna kolejność wygenerowana przez harness jest błędem narzędzia. Zły wynik prawidłowo wywołanej operacji produktu jest wynikiem badania i nie może być „naprawiany” przez generator.

### 6.1 Profil domyślny i eksploracyjny — liczby tylko z pomiaru

Nie zamrażać `max_examples` ani `stateful_step_count` z góry.

Implementer najpierw wykonuje mały realny pomiar (rząd 1–2 przykładów, kilka kroków) przez API + prawdziwy solver i zapisuje:

- komendę;
- exact SHA;
- czas całkowity;
- czas/przykład lub czas/krok;
- na tej podstawie wybrane `max_examples` i `stateful_step_count`.

Dowód trafia do `tasks/ROTA-T044/round_01/tests/**`.

Profil domyślny ma być realnie używalny w częstym `pytest`: pojedyncze dziesiątki sekund do niskich minut, wyraźnie poniżej około 750 s zmierzonego wcześniej pełnego portfela Wariantu A.

Profil eksploracyjny jest opt-in przez:

`ROTA_SIM_VARIANT_B_FULL=1`

i musi być wyraźnie większy od profilu domyślnego. Jego liczby również wynikają z pomiaru, nie zgadywania.

Jeżeli realny koszt nie pozwala zbudować sensownego profilu codziennego — STOP z pomiarem; nie fałszować problemu przez ustawienie symbolicznego `max_examples=1` i nazwanie go profilem częstym.

## 7. OWNER-05 — prawdziwe API i reuse Wariantu A

Wariant B przechodzi przez prawdziwy backend (`TestClient` + SQLite) i istniejące operacje koordynatora.

Reużyj istniejące helpery Wariantu A tam, gdzie ich semantyka jest identyczna (np. niskopoziomowe operacje tworzenia danych/API). Nie zmieniaj istniejących funkcji Wariantu A, żeby pasowały do Wariantu B.

Jeżeli helper Wariantu A koduje starą decyzję specyficzną dla A (np. stały shape/5×layer), dodaj osobny addytywny helper B zamiast zmieniać A.

Wariant A musi przejść swoje istniejące celowane testy bez zmiany kontraktu.

## 8. OWNER-06 — EXTERNAL jest wyłącznie testową reakcją po decyzji

Pierwszy PLAN zawsze używa wyłącznie zadeklarowanych LOCAL.

Jeżeli PLAN zwróci realny, niepusty `DECISION_REQUIRED`:

1. zachowaj pierwszy wynik i pełny payload;
2. utwórz jedną syntetyczną osobę `EXTERNAL_SUPPORT` przez istniejące operacje;
3. zachowaj istniejący decision-link ordering Wariantu A: create-person niesie bieżące decision id, kolejne zapisy membership/window przekazują `null`;
4. ponów PLAN;
5. jeżeli kolejny PLAN znów zwróci realny `DECISION_REQUIRED`, wolno powtórzyć reakcję z nowym bieżącym decision id;
6. maksymalna liczba utworzonych EXTERNAL dla jednego obiektu = początkowa `liczba_LOCAL` z kalkulatora;
7. po wyczerpaniu limitu zachowaj wynik jako finding/reproducer; nie twórz Assignmentów i nie dodawaj LOCAL.

Każdy etap musi pozostać w raporcie. Późniejszy FEASIBLE nie usuwa wcześniejszego `DECISION_REQUIRED`.

## 9. OWNER-07 — co Wariant B sprawdza, a czego nie

### 9.1 Dwa obowiązkowe invariants harnessu

Wariant B sam automatycznie sprawdza tylko:

1. **HEADCOUNT** — zadeklarowana liczba LOCAL jest dokładnie wynikiem kalkulatora warstwowego dla wygenerowanego obiektu;
2. **CLOSED WORLD** — każdy Assignment zwrócony przez produkt należy do zadeklarowanego LOCAL albo do EXTERNAL utworzonego przez dozwoloną reakcję dla tego obiektu.

Nie wymagaj, aby każdy LOCAL wystąpił w Assignmentach.

### 9.2 Wynik solvera nie jest oceniany przez Wariant B

Wariant B nie wystawia własnego PASS/FAIL za:

- fairness;
- TARGET-01;
- rytm D/N;
- odpoczynek;
- jakość rozkładu zmian;
- poprawność bilansu kwartalnego.

Te dane wolno i należy **zapisać** jako surowe dane produktu, ale nie wolno zbudować z nich drugiego orakla w tym Tasku.

Jeżeli produkt zwróci `TECHNICAL_ERROR`, niepusty `DECISION_REQUIRED`, FEASIBLE z dziwnym rozkładem albo inny zaskakujący rezultat — zachowaj go. Nie zmieniaj obiektu pod wynik.

## 10. OWNER-08 — raport i reprodukcja

Wariant B zapisuje maszynowo czytelny komplet danych potrzebny do późniejszej diagnozy, bez wysyłania go gdziekolwiek.

Dla znalezionego naruszenia invariantów harnessu lub awarii zachowaj co najmniej:

- run id / dane odtworzenia Hypothesis używane przez harness;
- wygenerowany katalog i miesiąc;
- wynik kalkulatora i zadeklarowany roster;
- targety i nieobecności;
- kolejność działań PLAN/EXTERNAL/select/REPLAN;
- statusy i payloady decyzji;
- zwrócone Assignmenty;
- istotne readback/analitykę już dostępną z produktu;
- gotową komendę reprodukcji jednego przypadku.

Artefakty trwałe należą do:

`tasks/ROTA-T044/round_01/tests/failures/**`

Nie dodawaj połączenia z zewnętrznym modelem ani automatycznej oceny tych JSON-ów.

## 11. Wielomiesięczne sekwencje

State machine może naturalnie przejść na kolejny miesiąc tego samego Site/rosteru i zapisać odczyt produktu.

Nie buduj kwartalnego oracle'a i nie duplikuj `rota/balance.py`. Wielomiesięczny przebieg jest tylko kolejną sekwencją działań koordynatora.

## 12. TASK_SCOPE

Dozwolone pliki:

- `tests/property/coordinator_simulator.py` — wyłącznie nowe addytywne funkcje/helpery Wariantu B; istniejący Wariant A nietknięty;
- `tests/property/test_coordinator_simulator_variant_b.py` — nowy;
- `pyproject.toml` — wyłącznie dodanie `hypothesis`;
- `tasks/ROTA-T044/TASK_CHATGPT.md`;
- `tasks/ROTA-T044/round_01/tests/**` — dowody, pomiary, reproduktory i audyty.

`tasks/ROTA-T044/brief.md` jest frozen source contract — implementer go nie edytuje.

Każda potrzeba pliku spoza powyższego scope = **STOP**, chyba że jest to wyłącznie aktualizacja `BOARD.md` przez osobę wykonującą handoff, nie implementacja produktu.

## 13. WHERE_MAP — REQUIRED

Źródłowy audyt R6 wykonał:

`python where.py tests/property/coordinator_simulator.py`

i potwierdził, że istniejącym konsumentem Wariantu A jest `tests/property/test_coordinator_simulator.py`, a zakres nie wymaga zmian produktu.

Przed „adwokatem diabła” i ponownie przed implementacją CC uruchamia na swoim exact HEAD:

```text
python where.py tests/property/coordinator_simulator.py
```

Po napisaniu nowych symboli B implementer uruchamia `where.py ... --symbol <NAME>` tylko dla faktycznie nowych/współdzielonych ownerów kalkulatora/generatora/state-machine seamów, zgodnie z `AGENTS.md`. Raw output nie jest werdyktem — trzeba przeczytać wskazane miejsca.

Jeżeli mapa pokaże nowego produkcyjnego konsumenta albo konieczność zmiany Wariantu A, STOP i zgłoś przed kodowaniem.

## 14. Kolejność implementacji po przejściu gate'u CC

### Checkpoint A — czysta arytmetyka i generator

Najpierw, bez uruchamiania state machine:

1. kalkulator warstwowy;
2. testy `5/10/9`;
3. generator wzoru zapotrzebowania z `required_primary_count` per wiersz/dzień;
4. asercja `declared_LOCAL == calculator`;
5. test mieszanej obsady robocze=2/weekend=1;
6. test legalnego overlapu nieodrzucanego przez generator;
7. test odrzucenia wyłącznie zero-coverage.

Dopiero gdy A jest zielone, podłączaj prawdziwy backend.

### Checkpoint B — działania koordynatora

1. świeża baza/Site per przykład;
2. prawdziwe API konfiguracji;
3. urlop 10/5 bez nakładania, także dla 1 LOCAL;
4. L4 raz/obiekt ~25%;
5. PLAN;
6. reakcja EXTERNAL na realny `DECISION_REQUIRED`;
7. select candidate / REPLAN tylko przy spełnionych preconditions;
8. CLOSED WORLD dla każdego zwróconego Assignmentu;
9. trwały reproduktor awarii/naruszenia harnessu.

### Checkpoint C — Hypothesis i koszt

1. state machine;
2. `database=None`, `deadline=None`, `derandomize=False`;
3. deterministyczny test pokazujący, że dwa jawnie różne identyfikatory przebiegu mogą wygenerować różne kanoniczne obiekty — bez oczekiwania „zwykle się różnią”;
4. mały realny pomiar czasu;
5. dopiero z pomiaru ustaw profil domyślny i `ROTA_SIM_VARIANT_B_FULL=1`;
6. celowana regresja Wariantu A.

Nie uruchamiaj pełnej regresji repo bez osobnej zgody OWNERA.

## 15. Minimalna macierz odbioru implementacji

- `T44-B-01` — kalkulator = 5 dla jednej pełnej warstwy D/N req=1;
- `T44-B-02` — kalkulator = 10 dla req=2 cały tydzień;
- `T44-B-03` — kalkulator = 9 dla robocze=2/weekend=1;
- `T44-B-04` — zadeklarowany LOCAL count zawsze equals kalkulator dla wygenerowanego obiektu;
- `T44-B-05` — generator rzeczywiście potrafi reprezentować różne `required_primary_count` per dzień/wiersz;
- `T44-B-06` — legalny overlap katalogu nie jest filtrowany jako „niesensowny”;
- `T44-B-07` — zero-coverage jest odrzucane przed API;
- `T44-B-08` — urlopy 10/5 dni roboczych są niepokrywające; działa także dla 1 LOCAL;
- `T44-B-09` — L4 jest decyzją raz/obiekt, blok 5 dni, LOCAL-only; brak harmonogramu „co N przypadek”;
- `T44-B-10` — pierwszy PLAN nie ma EXTERNAL;
- `T44-B-11` — realny DECISION_REQUIRED uruchamia addytywny EXTERNAL, z zachowaniem pierwszego wyniku i decision-link ordering;
- `T44-B-12` — limit EXTERNAL = początkowa liczba LOCAL, potem STOP/reproducer;
- `T44-B-13` — CLOSED WORLD wykrywa obcy employee_id w Assignmentach, ale nie wymaga użycia każdego LOCAL;
- `T44-B-14` — świeża SQLite + Site per przykład; stateful preconditions nie pozwalają harnessowi wykonywać nielegalnej kolejności;
- `T44-B-15` — Hypothesis nie używa persistent database ani deadline, nie jest derandomized;
- `T44-B-16` — profil domyślny i FULL mają liczby poparte zapisanym pomiarem, FULL > default;
- `T44-B-17` — Wariant A zachowuje dotychczasowe zachowanie i celowane testy;
- `T44-B-18` — finding/reproducer nie modyfikuje wejścia po wyniku solvera i zawiera komendę odtworzenia.

## 16. Warunki STOP

STOP bez implementowania obejścia, gdy:

- kalkulator nie odtwarza 5/10/9;
- `where.py` ujawnia potrzebę zmiany produktu lub istniejącego ownera A;
- generator potrzebuje nowej reguły określającej, które niezerowe wzory są „niesensowne”;
- state machine wymaga operacji bez odpowiednika w realnym API;
- legalny przebieg wymaga ręcznie utworzonego Assignmentu;
- limit EXTERNAL okazuje się niewystarczający/nadmierny — zgłoś reprodukcję i dane;
- nie da się uzyskać realnie używalnego profilu domyślnego po pomiarze;
- potrzebny jest plik poza TASK_SCOPE;
- implementacja zaczyna oceniać solver zamiast obserwować jego wynik.

## 17. Następny gate — jawny „adwokat diabła” CC

**CC teraz NIE IMPLEMENTUJE.**

CC ma przeczytać:

1. `BOARD.md`;
2. `tasks/ROTA-T044/brief.md` @ `b8fccffa4591fe979fae09a6915a35f161566e12`;
3. `tasks/ROTA-T044/round_01/tests/tests_r6.txt` @ `7c892a8ac1a2816e4f26c015ccc27a270b616c40`;
4. ten `TASK_CHATGPT.md` na exact HEAD;
5. raw `where.py tests/property/coordinator_simulator.py` na exact HEAD.

Następnie CC działa **wyłącznie jako adwokat diabła**: próbuje podważyć Task, znaleźć ukrytą sprzeczność, nierealny oracle, przypadkowe rozszerzenie produktu, ryzyko zmiany Wariantu A, niemożliwy state transition, fałszywe założenie o API albo miejsce, w którym generator może dawać solverowi fory.

Raport CC zapisuje jako nowy plik:

`tasks/ROTA-T044/round_01/tests/cc_devils_advocate_r1.txt`

Raport ma dla każdego findingu podać:

- TRACE do `brief.md`/OWNER decision;
- konkretny fragment tego Tasku;
- kod/seam na exact SHA;
- minimalny przykład pokazujący problem;
- klasyfikację: `BLOCKER` albo `NON_BLOCKING`.

CC **nie proponuje i nie implementuje poprawki produktu** w tej rundzie. Jeżeli nie znajdzie blockera, raport kończy się `NO_BLOCKER_FOUND`, ale to nadal nie jest automatyczna zgoda na implementację — Task wraca do architekta/OWNERA do zamknięcia gate'u.

# ROTA-T044 — Symulator Koordynatora Wariant B (prawdziwa zmienność zachowania)

Status: **CC AUTOR (OWNER 2026-08-30), KOREKTA R2 — DO AUDYTU CODEX, POTEM DO TASKU CZATGPT**

Pipeline dla tego Tasku, ustalony wprost przez OWNERA: CC pisze ten brief →
Codex audytuje → ChatGPT pisze Task na jego podstawie → **CC dostanie na końcu
wyraźne polecenie "adwokata diabła" i ma podważyć gotowy Task do podłogi**,
zanim cokolwiek zostanie zaimplementowane. To jest świadome odwrócenie
zwykłego zakazu self-review: zamiast liczyć, że CC przypadkiem nie będzie
bronić własnej roboty, CC dostaje wprost zadanie ją atakować.

Ta wersja (R2) zastępuje `725568e` po niezależnym audycie Codexa
(`tasks/ROTA-T044/round_01/tests/tests_r1.txt`, WYMAGA KOREKTY) i dalszej
rozmowie z OWNER, która poprawiła fundamentalne rozumienie tego, co Symulator
w ogóle ma robić.

Base: `main@1b6bfbf` (po merge ROTA-T043).

## 0. Skąd to się wzięło

ROTA-T043 dało **Wariant A**: Symulator Koordynatora, deterministyczny, stały
zestaw 20 obiektów (seedy 0-19). OWNER, po przejrzeniu realnych wyników,
zidentyfikował to jako **czujnik regresji**, wartościowy, ale niewystarczający
do testowania programu w szerszym sensie — bo zawsze daje ten sam wynik.
Wariant A **zostaje bez zmian**, ten Task go nie dotyka.

Rozmowa z OWNER (2026-08-30) — cytaty dosłowne, bo to są rozstrzygnięcia, nie
streszczenia:

> "Ta wersja może byc tylko jako wariant A wykrywający regresję [...]. Ale do
> testowania programu musi być generatorem scenariuszy obsada/obiekt."

> "Nie rozumiem, gdzie powiedziałem, że obsada 5/10 jest sztywna. Ona miała
> wynikać z kalkulatora godzin, który miał być w Symulatorze A, jest?"

(Odpowiedź: NIE JEST. `tests/property/coordinator_simulator.py:212`:
`employee_count = 5 * layer_count  # R4 frozen rule -- never derived from
workload`. Żaden kalkulator obsady nie istnieje w Wariancie A. Zweryfikowane
wprost w kodzie.)

> "Kalkulator to podstawa [...]. Jeśli kalkulator godzin i obsady będzie
> zły/nieużywany przez Hypothesis, to dostaniemy stos bzdurnych grafików jak w
> benchmarkach. Wpisze 8 osób na obiekt 5 osobowym i wesoło napisze, że
> wszystko jest zielone."

> "To ja chyba nie rozumiem ptaszków. Bo ja myślałem, że wystarczy odhaczyć
> dostepność w dni tygdnia w obiekcie i przy obsadzie i masz taki rytm pracy
> jaki chcesz." — potwierdzone: `frontend/src/screens/SiteShiftCatalog.tsx`
> ma dokładnie to, checkbox per dzień tygodnia per wiersz zmiany. Produkt jest
> w porządku; Wariant A tego mechanizmu po prostu nie używa swobodnie.

> "No w końcu. Sama nazwa mówi o co chodzi to Symulator zachowania
> koordynatora w programie, a wy napisaliście 20 testowych przejść przez
> solver."

> "Ok, przesadziłem, klikalne ekrany odłożymy na inny Symulator, bo sie
> zakopiemy w kodzie." — pełny UI/przeglądarka świadomie POZA zakresem,
> zostaje na osobny, przyszły Symulator.

**Kluczowa korekta R2, po dalszej rozmowie z OWNER:**

> "CC kalkulator wylicza tylko raz dla obiektu: ile jest na obiekcie godzin
> słuzby i dzieli je na według kodeksu pracy na ilość obsady. Symulator
> wpisuje je w panelu sterowania w zakładce obiekty wraz z innymi danymi [...],
> jego rola kończy sie na Plan/Replan i automatycznym potwierdzeniu EXTERNAL,
> bo ktoś MUSI byc na zmianie. Jeśli solver cos źle policzy to to jest wynik
> naszego testu, mamy co poprawiać. [...] SYMULATOR NICZEGO NIE LICZY POZA
> KALKULACJĄ OBSADY."

> "Evaluator jako zewnętrzny model, który odciąży nas od pisania naszego
> programu to mój pomysł." — osobny, późniejszy, poza tym Taskiem.

> [po sprawdzeniu surowych danych Wariantu A dla Q3 2026] "Czyli mamy
> sprawdzone, że Rota liczy kwartały, czyli w Symulatorze B nie musimy sie
> tym martwic." — CC ręcznie zweryfikował arytmetykę `month_balance`/
> `quarter_balance` z `tasks/ROTA-T043/round_01/tests/coordinator_report.json`
> dla wszystkich 5 osób przez lipiec-sierpień-wrzesień: w 100% spójna.
> Mechanizm `rota/balance.py` jest generyczny (liczy z godzin przypisań i
> absencji, nie z kształtu zmian), więc to jest dowód na poprawność
> mechanizmu, nie tylko jednego przypadku. **Wariant B nie buduje żadnej
> maszynerii kwartalnej ani oceny bilansu — to już zweryfikowane, poza
> zakresem.**

> [o strukturalnym deficycie godzin wykrytym w tych samych danych — 5 osób
> zawsze poniżej targetu, bo zapotrzebowanie/osobę < norma pełnoetatowa]
> "Nie, bo to sprawa kadrowa nie nasza, koordynator musi pamiętać o urlopach
> nie Rota, Rota mu podaje narastająco bilans poprawnie." — Rota liczy
> poprawnie; co koordynator z tym zrobi, to jego sprawa kadrowa. Nie Task.

## 1. Czym Symulator jest i czym nie jest — fundament, nie szczegół

**Symulator automatyzuje wyłącznie decyzje koordynatora.** Nie jest drugim
solverem, nie jest benchmarkiem, nie ocenia poprawności gotowego grafiku.
Jego jedyna odpowiedzialność obliczeniowa to kalkulator obsady (sekcja 1.1) —
poza tym **niczego nie liczy**. Jeśli solver źle policzy grafik, bilans albo
sprawiedliwość — to jest WYNIK testu, realny reproduktor do naprawy produktu,
nie coś, co Symulator ma sam wykryć oceną. To jest odwrócenie tego, co T043
Checkpoint B zbudował (evaluator fairness + oracle kwartalny) — Wariant B
świadomie tego nie powtarza. (Fakt, że Wariant A w main już łamie tę zasadę,
jest osobno zgłoszony OWNEROWI, nie jest częścią tego Tasku.)

### 1.1 Kalkulator obsady — jedno proste liczenie, raz, na starcie

Kalkulator liczy **dokładnie jedną rzecz, raz, przy tworzeniu obiektu**:
suma godzin służby wynikająca z wygenerowanego wzoru zapotrzebowania (sekcja
1.2) podzielona według normy z Kodeksu pracy (art. 130, ten sam wzór co
`nominal_monthly_hours_kp` w Wariancie A) = liczba obsady LOCAL. To NIE jest
solver ani drugi algorytm układający dyżury z uwzględnieniem odpoczynku —
to jest prosta arytmetyka kadrowa, jaką realny koordynator robi ręcznie,
zanim w ogóle otworzy Rotę.

Kalkulator ma własne, ręcznie zweryfikowane przypadki kontrolne (ten sam
wzorzec co `POLISH_2026_HOLIDAYS` + kontrole 160h/176h w Wariancie A) —
np. "720h/mies. zapotrzebowania przy normie 160h → 5 osób, policzone ręcznie
i potwierdzone" — zanim zostanie podłączony do losowego generatora.

**Warunek zawsze sprawdzany po wygenerowaniu obiektu** (poprawiony po
audycie Codexa R2 z `tests_r1.txt` — poprzednia wersja żądała fałszywej
równości):
- zadeklarowana liczba LOCAL == wynik kalkulatora dla wygenerowanego wzoru
  zapotrzebowania;
- **zamknięty świat**: każdy Assignment w dowolnym zwróconym wyniku należy
  do zadeklarowanego LOCAL albo do EXTERNAL utworzonego przez dozwoloną
  reakcję (sekcja 1.4) — nigdy do kogoś innego.

Nie wymaga się, żeby KAŻDY zadeklarowany LOCAL dostał Assignment w każdym
gotowym grafiku (Codex R2: absencja, DAY_ONLY, DECISION_REQUIRED bez grafiku
to normalne, poprawne wyniki, w których nie każdy się pojawia). To
zabezpiecza dokładnie przed obawą OWNERA ("8 osób na obiekcie 5-osobowym,
wesoło zielone") bez fałszywych FAIL-i na poprawnych wynikach.

### 1.2 Swobodne generowanie wzoru zapotrzebowania, nie gotowe kształty

Generator losuje NIEZALEŻNIE, dla każdego rodzaju zmiany (D/N/24h), każdego
dnia tygodnia z osobna: czy ta zmiana występuje tego dnia, o jakich godzinach,
i jaki jest `required_primary_count` (poprawka po Codex R3 — poprzednia
wersja o tym nie wspominała, mimo że to pole decyduje o liczbie równoległych
stanowisk i jest konieczne dla obiektów z podwójną obsadą). To ma naturalnie
wytwarzać "tylko weekend", "tylko dni robocze", "tylko noce", i kombinacje,
których nikt nie nazwał z osobna — bez enumerowania ich jako oddzielne
"kształty". `SiteShiftCatalog.tsx`'s checkboxy per dzień tygodnia to
dokładnie ten sam mechanizm w prawdziwym UI, potwierdzone działające.

**Poprawka po Codex R3**: `rota/planning/shift_catalog.py:250` (na exact SHA)
mówi wprost, że wielokrotne wpisy i nakładanie się zmian w katalogu są
LEGALNE i tworzą niezależne occurrence — to jest przeciwieństwo tego, co
poprzednia wersja tego briefu twierdziła ("nakładające się zmiany to znany,
nieobsługiwany przypadek"). Ten Task nie odrzuca legalnych overlapów.
Jedyny przypadek do odrzucenia PRZED budową obiektu (nie po, jako "błąd
produktu") to wzór dający **zero pokrycia w całym miesiącu** (nic do
zaplanowania w ogóle) — to nie jest błąd produktu, to bezużyteczny obiekt
testowy, generator ma go odrzucić/przelosować, nie budować.

### 1.3 Hypothesis (stateful) — prawdziwa zmienność, jawny kontrakt

Zamiast `for seed in range(20)` (Wariant A, zostaje bez zmian, osobny plik):
silnik oparty o Hypothesis (`RuleBasedStateMachine`), losujący przy KAŻDYM
uruchomieniu nowy zestaw obiektów/sekwencji działań koordynatora.

**Poprawka po Codex R5** (kontrakt nie był wykonywalny w poprzedniej
wersji): brief musi zamrozić, nie implementer wybierać:
- `hypothesis` jako jawna zależność w `pyproject.toml` (nie ma jej dziś);
- ograniczony profil eksploracyjny: jawny `max_examples` i limit kroków
  stateful, dobrany tak, żeby zwykły `pytest` pozostał tani (T043's pełny
  portfel 20 obiektów + kwartał trwał ~750s — domyślne parametry Hypothesis
  byłyby nieadekwatne dla prawdziwego API+solvera, muszą być jawnie
  zawężone, nie domyślne);
- jawny artefakt reprodukcji per znalezione naruszenie (seed/przykład +
  gotowa komenda), zapisany tak jak Wariant A to robi (`failures/**`);
- jawny, deterministyczny sposób sprawdzenia realnej zmienności: test
  porównuje kanoniczne wygenerowane obiekty z dwóch RÓŻNYCH, jawnie
  podanych identyfikatorów przebiegu — nie polega na "zwykle wychodzi
  inaczej".

**Poprawka po Codex R6**: każdy przykład stateful dostaje świeżą SQLite
`:memory:` i nowy Site — bez tego shrinking może odtwarzać przypadek na
stanie pozostawionym przez poprzedni przykład. Brief wymaga jawnych
warunków stanu (precondition) dla każdej reguły: np. REPLAN wymaga
istniejącego current_version, select_candidate wymaga wyniku FEASIBLE z
poprzedniego kroku. Zły wynik PRODUKTU (np. solver zwraca coś dziwnego)
pozostaje wynikiem badania; tylko generator próbujący nielegalnej kolejności
akcji (np. REPLAN bez istniejącego grafiku) jest błędem narzędzia.

Gdy Hypothesis znajdzie naruszenie niezmiennika z 1.1 (jedynego niezmiennika,
jaki Symulator w ogóle sprawdza), automatycznie skraca je do najmniejszego
przykładu (wbudowana funkcja Hypothesis).

### 1.4 EXTERNAL — automatyczna, powtarzalna reakcja

Pierwszy PLAN zawsze używa wyłącznie wygenerowanych LOCAL. Jeżeli produkt
zwróci prawdziwy, niepusty `DECISION_REQUIRED`:
1. pierwszy wynik zostaje zachowany, niezmieniony;
2. Symulator automatycznie tworzy jedną syntetyczną osobę `EXTERNAL_SUPPORT`
   i okno przez istniejące produkcyjne operacje (ten sam porządek zapisów co
   Wariant A: create-person niesie decision id, kolejne zapisy null);
3. ponawia PLAN;
4. jeśli produkt PONOWNIE zwróci realny `DECISION_REQUIRED` żądający
   dalszego wsparcia, powtarza krok 2-3 (kolejny EXTERNAL) — z jawnym,
   bezpiecznym warunkiem zakończenia (limit prób, żeby nie zapętlić się w
   nieskończoność na wadliwym obiekcie testowym), nie zgadywaniem kiedy
   przestać;
5. jeśli nawet to nie da grafiku, Symulator zachowuje wynik jako
   ograniczenie/błąd produktu. Nie tworzy Assignmentów ręcznie.

Uzasadnienie: obiekt musi zostać obsadzony — kimś. W testowej automatyzacji
tę rolę reprezentuje syntetyczny EXTERNAL, tak jak w produkcie reprezentuje
ją realny coordinator, wsparcie albo w ostateczności właściciel.

### 1.5 Kwartał — więcej działań koordynatora, zero nowej oceny

Wariant B może kontynuować ten sam Site/roster przez kolejne miesiące (więcej
kroków stateful sekwencji: kolejny miesiąc, kolejny PLAN), ale **nie liczy
niczego samodzielnie** — to jest już zweryfikowane jako poprawne w Wariancie A
(sekcja 0 wyżej, ręcznie sprawdzone przez CC na surowych danych Q3 2026).
Jeśli Wariant B naturalnie wygeneruje sekwencję obejmującą kilka miesięcy
tego samego obiektu, po prostu odczytuje i zapisuje to, co realna Analityka
i bilanse już zwraca — bez budowania własnego oracle'a.

### 1.6 Evaluator zewnętrzny — poza zakresem tego Tasku

OWNER ma pomysł na osobny, późniejszy krok: eksport anonimowego, kompletnego
pakietu JSON (konfiguracja obiektu, roster, targety, nieobecności, decyzje,
Assignmenty, validate, analityka) przekazywany zewnętrznemu modelowi do
diagnostycznej oceny — żeby odciążyć OWNERA od ręcznego przeglądania setek
surowych grafików. To NIE jest częścią Wariantu B — Symulator ma tylko
zapisywać kompletne, surowe dane w formacie, który taki eksport mógłby
później skonsumować (to znaczy: raport JSON ma być kompletny i czytelny
maszynowo, nic więcej). Sam mechanizm eksportu/oceny to osobny, przyszły
Task.

## 2. Co NIE wchodzi w zakres tego Tasku

- **Pełny UI/przeglądarka** — świadomie odłożone na osobny, przyszły
  Symulator. Ten Task zostaje na poziomie API (`TestClient` + prawdziwy
  backend), jak Wariant A.
- **Jakakolwiek ocena wyniku przez Symulator** (fairness, jakość grafiku,
  poprawność bilansu) — usunięte całkowicie z Wariantu B, nie tylko
  "odłożone". Symulator liczy TYLKO kalkulator obsady (1.1).
- **Maszyneria kwartalna/oracle bilansu** — już zweryfikowane w Wariancie A
  jako poprawne (sekcja 0), nie duplikować.
- **Evaluator jako funkcja produktu** ani jako eksport do zewnętrznego
  modelu — oba osobne tematy (patrz 1.6 i
  `arch/REQUEST_SYMULATOR_WARIANT_B_2026-08-30.md`), nie mieszać z tym
  Taskiem.
- **Wariant A sam w sobie** — zostaje jako czujnik regresji, bez zmian.
- **Rozliczenie z Codexem** za wcześniejsze zignorowanie instrukcji o
  replay — OWNER świadomie to odpuszcza ("już mi wyjaśnił, zostawmy to").
- Wszystko, co T043 sekcja 9 już zakazywało (`rota/**`, `api/**`,
  `frontend/src/**`, `benchmarks/**`, drugi solver/validator, Cross-Site,
  wsparcie przed pierwszym PLAN, własny rachunek urlopu/L4, sieć w runtime).

## 3. Zamrożone decyzje z Wariantu A, które nadal obowiązują

Prawdziwe produkcyjne ścieżki API (bez monkeypatchowania PLAN/REPLAN/
validate/analityki), target_hours jako prawdziwe wejście, nieobecności przez
prawdziwy endpoint, zły grafik jako wynik badania (nie sygnał do zmiany
wejścia), granica twierdzeń o prawie (produkcyjny `validate()` to stan HARD
zaimplementowany w produkcie, nie certyfikat całego Kodeksu pracy).

## 4. PREIMPLEMENTATION REDUCTION GATE

| Element | Źródło | Konieczność | Redukcja |
|---|---|---|---|
| prosty kalkulator obsady (godziny/norma KP) | OWNER 2026-08-30 R2, upraszcza R1 audytu | bez tego generator testuje fikcyjne obiekty | jedno dzielenie + ręcznie zweryfikowane przypadki kontrolne |
| asercja deklaracja=kalkulacja + zamknięty świat | OWNER 2026-08-30 + Codex R2 (poprawia błędną wersję) | zapobiega "8 osób na obiekcie 5-osobowym" bez fałszywych FAIL | dwa sprawdzenia po każdym przypadku |
| swobodne dni tygodnia/rodzaj/required_primary_count | OWNER 2026-08-30 + Codex R3 | usuwa gotowe kształty i nieaktualny zakaz overlapów | losowanie niezależne per (dzień, rodzaj, required_primary_count) |
| Hypothesis stateful z jawnym kontraktem | OWNER 2026-08-30 + Codex R5/R6 | prawdziwa zmienność, wykonywalny kontrakt | jeden stateful engine, jawny profil, izolacja per przykład, reużywa produkcyjne helpery Wariantu A |
| WHERE_MAP: REQUIRED | Codex R7 | nowy właściciel kalkulatora/generatora | mapa na `coordinator_simulator.py` + nową zależność `hypothesis` |
| brak oceny fairness/kwartału | OWNER 2026-08-30 R2 (fundamentalna korekta) | Symulator nie jest sędzią | usunięte całkowicie, nie "opcjonalne" |

Nie powstają: pełny UI/Playwright, jakikolwiek evaluator wbudowany w
Symulator, drugi solver/validator, zmiana Wariantu A.

## 5. TASK_SCOPE

TASK_SCOPE:
- `tests/property/coordinator_simulator.py` (nowe funkcje: kalkulator,
  swobodny generator wzoru zapotrzebowania, stateful engine — istniejące
  funkcje Wariantu A nietknięte/reużywane, nie kasowane)
- `tests/property/test_coordinator_simulator_variant_b.py` (nowy plik,
  osobny od Wariantu A)
- `pyproject.toml` (wyłącznie dodanie zależności `hypothesis`)
- `tasks/ROTA-T044/brief.md`
- `tasks/ROTA-T044/round_01/tests/**`

Zabronione: `rota/**`, `api/**`, `frontend/src/**`, `benchmarks/**`,
modyfikacja istniejących funkcji Wariantu A poza dodaniem nowych,
addytywnych funkcji które Wariant B reużywa.

## 6. WHERE_MAP

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: `tests/property/coordinator_simulator.py`
- REASON: Task dodaje nowego właściciela (kalkulator obsady, swobodny
  generator wzoru zapotrzebowania) do pliku już współdzielonego z Wariantem
  A; mapa ma ujawnić, czy coś poza `test_coordinator_simulator.py` i nowym
  `test_coordinator_simulator_variant_b.py` go konsumuje.

## 7. Warunki zatrzymania

Implementer zatrzymuje się i zgłasza problem, jeżeli:
- kalkulator obsady nie da się zweryfikować ręcznie na małym zestawie
  przypadków kontrolnych przed podłączeniem go do losowania;
- generowany wzór zapotrzebowania wymaga rozstrzygnięcia, którego dziś nie
  ma (np. nowa klasa "niesensownego" wzoru poza "zero pokrycia w miesiącu")
  — zgłosić, nie zgadywać nowej reguły;
- Hypothesis stateful wymaga symulowania czegoś, co dziś nie ma
  odpowiednika w prawdziwym produkcyjnym API;
- limit prób EXTERNAL (1.4) okazuje się za niski/wysoki dla realnych
  wygenerowanych obiektów — zgłosić z danymi, nie zgadywać liczby.

## 8. Pytania do niezależnego audytu Codexa

1. Czy kalkulator obsady to faktycznie jedno proste dzielenie (godziny
   zapotrzebowania / norma KP), zgodnie z ostatnią korektą OWNERA — nie
   powrót do złożonego liczenia z ograniczeniami odpoczynku z R1?
2. Czy asercja z 1.1 (deklaracja=kalkulacja + zamknięty świat) faktycznie
   nie generuje fałszywych FAIL na poprawnych wynikach (absencja, DAY_ONLY,
   DECISION_REQUIRED)?
3. Czy generator faktycznie losuje `required_primary_count` i nie odrzuca
   legalnych overlapów?
4. Czy kontrakt Hypothesis (profil, izolacja per przykład, artefakt
   reprodukcji, dowód realnej zmienności) jest teraz wykonywalny i
   jednoznaczny, nie zostawiony do wyboru implementera?
5. Czy brief jednoznacznie zeruje wszelką ocenę fairness/kwartału w
   Wariancie B, zamiast zostawiać to jako "opcjonalne"?
6. Czy Wariant A pozostaje całkowicie nietknięty?

Do zamknięcia audytu: **implementacja czeka na PASS Codexa na tym briefie,
potem na Task napisany przez ChatGPT, potem na jawne polecenie "adwokat
diabła" dla CC przed jakimkolwiek kodowaniem.**

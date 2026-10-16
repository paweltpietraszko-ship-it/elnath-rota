# ROTA-PRESERVED-FACTS-REPLAN — przeliczanie przyszłości z zachowaniem faktów

STATUS: READY FOR INDEPENDENT PREIMPLEMENTATION CHECK; IMPLEMENTATION HOLD.
DATA: 2026-10-16.
BASE_SHA: 89cd9797bc61490a89ddec97a04abc02b40ae6e4.
BRANCH: codex/rota-preserved-facts-replan-brief.

## 1. Cel i PRODUCT_TRUTH

Jeden Task dla dwóch zgłoszeń z BOARD: ROTA-NN-REPLAN-TECHNICAL-ERROR
(CC reprodukował na Windows, main@642fdd1) i
ROTA-NIGHT-STREAK-FIXED-WINDOW-INFEASIBLE (CC potwierdził ze źródła
main@b4e75d1, bez runtime REPRO). Autor briefu potwierdził punktowo ownerów
na BASE_SHA; nie wystawia werdyktu ani nie uruchamia audytu produktu.

Źródła zachowania:
- OWNER 2026-10-16: koordynator może świadomie naruszyć reguły, Rota zachowuje
  jego decyzję w pamięci i sama przestrzega reguł przy nowych propozycjach;
  decyzja utrwalona w `tasks/ROTA-CLOUD-REVIEW-FIXES/brief.md`, O4/O5;
- `tasks/ROTA-CORRECTION-EFFECTIVE-FROM-DEFAULT/brief.md` §7/H10/H10a/H10b:
  historyczne PRIMARY+CANCELLED+NN pozostaje dokładnym faktem w dziecku,
  nie jest pracą ani pokryciem, automat nie obsadza jego przeszłego demandu;
- `tasks/ROTA-T058/brief.md` §2.3/2.3A: w pełni ustalone okno nie blokuje
  niezwiązanej przyszłości; mieszane okno z nową trzecią służbą jest HARD,
  również na obu granicach miesiąca;
- T032 oraz CLOUD-REVIEW-FIXES F1/F2: NIGHT-STREAK-01 pozostaje niezależną
  regułą dla nowych propozycji, ręczne N/N/N jest zapisywalne jako LAW;
- istniejące kontrakty T009/T017/T033: produkcyjne PLAN/Przelicz/REPLAN,
  kandydaci, akceptacja i zachowanie historii bez nowego workflow.

Ten Task doprecyzowuje NIGHT-STREAK-01 analogicznie do ustalonej granicy
T058. Nie zmienia limitu dwóch nocek, definicji nocki ani priorytetów solvera.

## 2. Wynik dla koordynatora

Przypadek NN: po „nie przepracował” za wczoraj Przelicz działa dla części,
która nadal może być planowana. Zaakceptowany kandydat zachowuje dokładny NN,
nie dopisuje po fakcie zastępstwa i nie udaje pokrycia. Rzeczywista luka
pozostaje widoczna jako COVERAGE-01/obecne odchylenie, bez TECHNICAL_ERROR
lub nowej blokującej decyzji wyłącznie z powodu tego historycznego NN.

Przypadek nocek: zapisane ręcznie N/N/N, które w całości są już stałymi
faktami wejściowymi (rozpoczęte, REALIZED lub zamrożone), pozostają bez zmian.
Same nie powodują INFEASIBLE ani nowego DECISION_REQUIRED przy przeliczaniu
niezwiązanej przyszłości. Wciąż są wykrywane i pokazywane jako naruszenie LAW.
To dotyczy też świadomie zamrożonych przyszłych służb; „stałe” nie jest
synonimem „czas już minął”. Istnienie ruchomego wpisu w starej wersji samo
w sobie nie czyni go stałym faktem.

Nowe okno mieszane, np. dwie stałe nocki i trzecia proponowana przez automat,
nadal jest zabronione. Stała trójka nie daje pracownikowi ogólnego zwolnienia
z reguły, np. przy proponowaniu czwartej nocki. Automat szuka innej legalnej
obsady albo zwraca istniejący prawdziwy wynik braku rozwiązania/reguły,
bez zgody na odstępstwo w nowym kandydacie i bez ogólnego błędu technicznego.

Odczyt: istniejący snapshot, kontekst sąsiednich miesięcy, cutover, aktualne
reguły i raport walidatora. Zapis dopiero przez obecne operacje akceptacji:
nowe dziecko, rzeczywiste odchylenia i dotychczasowy ślad decyzji; rodzic,
NN i stałe służby nie są przepisywane. Ponowne otwarcie pokazuje odchylenia.
Nie ma automatycznego potwierdzania LAW ani kasowania dawnych decyzji.
PDF/Excel/saldo korzystają z tych samych faktów i obecnych zasad. NN nadal
nie zwiększa WYK, godzin pracy, pokrycia, odpoczynku, zajętości ani fairness.

Błąd faktycznej nowej propozycji albo integralności nadal jest odrzucany
obecnymi bramkami. Nieudana akceptacja jest atomowa i pozostawia current
bez zmian; koordynator może odświeżyć i ponowić obecną operację. Bez nowego
panelu, endpointu, typu pamięci lub automatycznej zmiany danych.

## 3. Minimalne szwy i dozwolone zmiany

### A. Stałe okno NIGHT-STREAK-01

`constraints.add_max_two_consecutive_night_constraints`: nie dodawać
sprzecznego ograniczenia 3≤2 dla okna złożonego wyłącznie z ustalonych
stałych. To granica autonomii jak w `_third_shift_window_assumption`;
nie jest wyłączeniem całej reguły. Każde okno z rzeczywistą nową zmienną
decyzyjną nadal dostaje dotychczasowe HARD i truthful diagnosis.
Nie mieszać do nocek TRAINEE, NN, pracy na innym obiekcie ani nowych kryteriów N.

Spójna granica miesiąca dla constraint i `_check_night_streak`:
start trzydniowego okna w [month_start−2 dni, month_end], z kontekstem
do month_end+2 dni. Okno musi dotyczyć badanego miesiąca; nie wracać
do nieograniczonej historii naprawionej przez F2. Gdy dwa ustalone N leżą
w następnym miesiącu, solver nie może dołożyć trzeciej nocki w bieżącym.
Reguła już obowiązuje przez granicę miesiąca w T058; nie zmieniamy daty
przypisania służby ani sposobu generowania context/boundary w assemblerze.

### B. Jedna klasyfikacja zachowanych naruszeń

Mały wspólny owner `rota/planning/preserved_violations.py`, używany przez
engine i akceptację application. Przenieść/reuse obecną semantykę
`engine._is_fully_historical_third_shift`, bez rozszerzania jej do wszystkich
HARD. Reuse istniejących zbiorów `fixed_existing_assignments` i
`_historical_nn_facts` z solvera; nie kopiować reguł ustalania stałości/NN.
Solver nie importuje tego modułu — bez cyklu i bez refaktoru solver.py.

Owner rozróżnia wyłącznie:
1. istniejącą klasę ustalonego THIRD-CONSECUTIVE-SHIFT-01;
2. ustalone NIGHT-STREAK-01: naruszenie dotyczy wyłącznie niezmienionych
   faktów wejściowych/boundary, żadna nowa/ruchoma decyzja nie uczestniczy;
3. COVERAGE-01 będące dokładnie historycznym niedoborem po zachowanych NN.

NN: identyfikacja po strukturalnych demand_ids i rzeczywistych przedziałach,
nie po tekście komunikatu. Tylko PRIMARY+CANCELLED+NN już rozpoczęte według
istniejącego cutover i obecne w źródłowej wersji; kandydat zachowuje ich
pełne fakty. Nie traktować pustych assignment_ids jako automatycznego dowodu
NN. Nie zaliczać nadmiaru pokrycia ani luki innego demandu. Przy wymaganej
obsadzie wieloosobowej i częściowych przedziałach sam fakt jednego NN nie
wyjaśnia całej luki: wszystkie ignorowane przy bramce fragmenty/niedobory
muszą być dokładnie przypisane do tych NN. Wykorzystać istniejące
`coverage_segments`/atrybucję przedziałów, bez drugiego algorytmu pokrycia.
NN jest dowodem przyczyny niedoboru, nigdy realnym pokryciem.

Klasyfikacja porównuje rzeczywisty kandydat z wejściowymi faktami. Samo
podanie istniejącego assignment_id/frozen/REALIZED/NN nie uprawnia do wyjątku.
Pozostałe naruszenia i ich dotychczasowa diagnoza pozostają bez zmian.
hard_pass=False z pustą listą szczegółów nie staje się True przez pusty all().
Nie zmieniać oryginalnego raportu walidatora: historyczne naruszenia nadal
muszą być dostępne odczytom, pamięci, finalizacji i eksportowi.

### C. Engine i akceptacja używają tej samej granicy

`engine.py`: użyć wspólnej klasyfikacji przy bramce pierwszego kandydata,
alternatywach, rozróżnieniu non-load i diagnozie konfliktów. Wyłącznie
zachowane naruszenia nie zatrzymują wyniku; współistniejący nowy konflikt
(np. L4/REST/LOAD, uszkodzenie faktu) nadal podlega własnej obecnej diagnozie.
Nie wyłączać całego raportu z powodu jednego wyjaśnionego NN lub okna.

`plan_ops.select_candidate`: ten sam warunek dopuszczalności, zamiast
bezwzględnego odrzucenia każdego report.hard_pass=False. Użyć prawdziwej
źródłowej wersji i obecnej granicy cutover; czas ustalić raz i współdzielić
z istniejącą kontrolą ochrony faktów, nie tworzyć dwóch sprzecznych zegarów.
Nie osłabiać `_coerce_unproven_realized_to_planned`, cutover pre_check,
ochrony NN/rozpoczętych służb, current/version i atomowości.
Nowe dziecko zachowuje rzeczywiste odchylenia przez obecne
`materialize_deviations`, nie przez niezależny rejestr lub ogólne ack=True.
Pierwszy PLAN bez źródłowej wersji nie otrzymuje wyjątku „historia”.

## 4. Redukcja przed implementacją — jedno przejście

SOURCE/NECESSITY: istniejący kontrakt zachowania faktów wymaga odróżnienia
ich od nowej decyzji także w modelu, bramce engine i akceptacji. Jeden
wspólny klasyfikator to minimalny szew między tymi dwiema bramkami, nie nowy
walidator. Obecny validator nadal pokazuje całą prawdę o grafiku.
Nie trzeba refaktoru solvera, zmiany objective/fairness, nowych statusów,
ogólnego wyłączenia HARD, tabel, API, UI ani przeliczania historii.
Nie jest to niezależny PASS autora własnemu kontraktowi.

## 5. Minimalny dowód po implementacji

Zachować dwa pierwotne reproduktory. NN odtworzyć przez rzeczywiste
mark_not_worked → POST plan z effective_from:null, bez ręcznie spreparowanej
listy Assignments jako jedynego dowodu. N/N/N zapisać przez realną ręczną
korektę z odchyleniem/akcją, potem przeliczyć. Używać danych testowych tego
samego obiektu, nie zestawiać niezależnych seedów jako rzekomej bazy produktu.

R1. Bieżący zaakceptowany miesiąc, wczorajsze NN → Przelicz → akceptacja
→ odczyt/reload: przyszła obsada działa, dokładny NN i luka są zachowane,
rodzic bez zmian; brak TECHNICAL_ERROR wyłącznie z tego powodu. Projekcja
PDF/Excel i saldo nadal nie liczą NN jako pracy. Sprawdzić granicę start==cutover.

R2. Ręczne N/N/N w całości fixed: osobno frozen, rozpoczęte i REALIZED;
przeliczenie niezwiązanej przyszłości i akceptacja działają, odchylenia LAW
pozostają widoczne. Stały przyszły fragment i boundary są faktami, nie nową
propozycją. Istniejące potwierdzenia finalizacji/LAW pozostają bez zmian.

R3. Dwie stałe nocki + nowa trzecia oraz nowa czwarta przy stałej trójce:
automat nie daje nielegalnego kandydata. Sprawdzić początek i koniec miesiąca,
także rok/grudzień→styczeń. Odległa trójka bez związku z badanym miesiącem
nadal nie blokuje (retained F2). Bez nowej pełnej macierzy wszystkich reguł.

R4. Wąskie negatywy klasyfikacji: przyszłe NN, zwykłe CANCELLED, inny demand,
częściowo niewyjaśniony niedobór przy obsadzie >1, nadmiar pokrycia; nowy
assignment w oknie/zmiana istniejącego faktu. Żaden z nich nie dostaje
ogólnego wyjątku dla historii. Bez parsowania komunikatów/zgody z samego id.

R5. Historia plus niezależne nowe L4/REST/LOAD albo uszkodzona referencja:
nowy problem nadal wykrywany i prawidłowo diagnozowany. Zastosować te same
reguły do każdego istniejącego wariantu, retry/wider-search i ścieżki
akceptacji web/Excel, które używają wspólnego ownera. Jedna wspólna
parametryzacja bramki + rzeczywisty pion, bez kopiowania pełnego kontraktu
każdego wrappera. Sfałszowany kandydat usuwający/zmieniający NN lub stałą
służbę jest odrzucany; nieudany zapis nie zmienia current ani pamięci.

Nowy test `tests/test_preserved_facts_replan.py`; reuse celowanych przypadków
`tests/test_historical_service_correction.py`, `tests/test_t058.py`,
`tests/test_t032_soft_ranking.py`, `tests/test_cloud_review_schedule_fixes.py`.
Zmiana starego testu wyłącznie gdy wymaga niedozwolonej teraz blokady
ustalonej historii lub dawnego niesymetrycznego okna nocek; wskazać TRACE.
Nie osłabiać dowodu zachowania nowego HARD, fixed facts i rzeczywistego pokrycia.

Pytest przez `.venv\Scripts\python.exe`; raportuje się exact SHA, warstwy
i ograniczenia. Celowane testy i właściwy pion; pełna regresja tylko po
osobnej zgodzie OWNERA z uzasadnieniem ryzyka, nie automatycznie w tym Tasku.
Precheck briefu nie uruchamia produktu, testów ani mapy całego kodu.
FAIL po dostawie wymaga TRACE + OWNERSHIP + niezależnego REPRO.

## 6. Granice i zakres

Nie jest to refaktor zakazanych do dzielenia dużych plików. Dopuszczone są
tylko wąskie poprawki nazwanych ownerów. STOP, jeśli potrzeba szerszej
zmiany modelu czasu, objective, generowania demandów lub lifecycle.
OUT_OF_SCOPE: nowe wyjątki dla innych reguł, retroaktywne obsadzanie NN,
uznanie NN za pracę, automatyczne ack, nowa pamięć, zmiana schematu, budżetu
solvera, wag/fairness, UI/API, benchmarki i pozostałe tematy ODLOZONE.

WHERE_MAP:
- MODE: REQUIRED
- TARGETS: rota/planning/constraints.py --symbol add_max_two_consecutive_night_constraints; rota/planning/validator_checks_patterns.py --symbol _check_night_streak; rota/planning/engine.py --symbol _gating_hard_pass; rota/planning/engine.py --symbol _split_frozen_violations; rota/application/plan_ops.py --symbol select_candidate
- REASON: ta sama granica zachowanych faktów w modelu, walidacji i rzeczywistej akceptacji, również dla alternatyw i sąsiednich miesięcy.

Po zamrożeniu scope: where.py dla nazwanych plików i symboli; po zmianie
również nowy preserved_violations.py i rzeczywiście dodane publiczne symbole.
Odczytać trafienia przed wnioskiem; nie rozszerzać mapy na cały solver/repo.

TASK_SCOPE:
- tasks/ROTA-PRESERVED-FACTS-REPLAN/brief.md
- tasks/ROTA-PRESERVED-FACTS-REPLAN/repo_before.hash
- tasks/ROTA-PRESERVED-FACTS-REPLAN/round_01/
- rota/planning/constraints.py
- rota/planning/validator_checks_patterns.py
- rota/planning/engine.py
- rota/planning/preserved_violations.py
- rota/application/plan_ops.py
- tests/test_preserved_facts_replan.py
- tests/test_historical_service_correction.py
- tests/test_t058.py
- tests/test_t032_soft_ranking.py
- tests/test_cloud_review_schedule_fixes.py

KONIEC TASK_SCOPE.

Niezależny precheck Codexa i ocena merytoryczna CC przed implementacją.
Autor nie wystawia niezależnego PASS. Po dostawie nowy raport
`round_01/tests/tests_r<n>.txt`, bez nadpisywania; merge i deploy tylko OWNER.

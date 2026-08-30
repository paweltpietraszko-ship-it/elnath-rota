# ROTA-T044 — Symulator Koordynatora Wariant B (prawdziwa zmienność zachowania)

Status: **CC AUTOR (OWNER 2026-08-30) — DO AUDYTU CODEX, POTEM DO TASKU CZATGPT**

Pipeline dla tego Tasku, ustalony wprost przez OWNERA: CC pisze ten brief →
Codex audytuje → ChatGPT pisze Task na jego podstawie → **CC dostanie na końcu
wyraźne polecenie "adwokata diabła" i ma podważyć gotowy Task do podłogi**,
zanim cokolwiek zostanie zaimplementowane. To jest świadome odwrócenie
zwykłego zakazu self-review: zamiast liczyć, że CC przypadkiem nie będzie
bronić własnej roboty, CC dostaje wprost zadanie ją atakować.

Base: `main@1b6bfbf` (po merge ROTA-T043).

## 0. Skąd to się wzięło

ROTA-T043 dało **Wariant A**: Symulator Koordynatora, deterministyczny, stały
zestaw 20 obiektów (seedy 0-19). OWNER, po przejrzeniu realnych wyników,
zidentyfikował to jako **czujnik regresji**, wartościowy, ale niewystarczający
do testowania programu w szerszym sensie — bo zawsze daje ten sam wynik.
Wariant A **zostaje bez zmian**, ten Task go nie dotyka.

Rozmowa z OWNER (2026-08-30), która doprowadziła do tego briefu — cytaty
dosłowne, bo to są rozstrzygnięcia, nie streszczenia:

> "Ta wersja może byc tylko jako wariant A wykrywający regresję [...]. Ale do
> testowania programu musi być generatorem scenariuszy obsada/obiekt."

> "CC, codex miał jasno powiedziane, że ja nie chce odtwarzania scenariuszy
> przez Symulator [...]. Jesli damy generatorowi pełną swobodę to zacznie tak
> jak benchmarki klikać obiekty 5 osobowe a do obsady użyje znowu 8 osób."

> "Nie rozumiem, gdzie powiedziałem, że obsada 5/10 jest sztywna. Ona miała
> wynikać z kalkulatora godzin, który miał być w Symulatorze A, jest?"

(Odpowiedź: NIE JEST. `tests/property/coordinator_simulator.py:212`:
`employee_count = 5 * layer_count  # R4 frozen rule -- never derived from
workload`. Żaden kalkulator obsady nie istnieje w Wariancie A — to jest
sztywna tabela, nie liczenie. Zweryfikowane wprost w kodzie, nie z pamięci.)

> "Kalkulator to podstawa [...]. Jeśli kalkulator godzin i obsady będzie
> zły/nieużywany przez Hypothesis, to dostaniemy stos bzdurnych grafików jak w
> benchmarkach. Wpisze 8 osób na obiekt 5 osobowym i wesoło napisze, że
> wszystko jest zielone."

> "To ja chyba nie rozumiem ptaszków. Bo ja myślałem, że wystarczy odhaczyć
> dostepność w dni tygdnia w obiekcie i przy obsadzie i masz taki rytm pracy
> jaki chcesz." — potwierdzone: `frontend/src/screens/SiteShiftCatalog.tsx`
> ma dokładnie to, checkbox per dzień tygodnia per wiersz zmiany. Produkt jest
> w porządku. Wariant A tego mechanizmu po prostu nie używa swobodnie —
> wybiera z 3 gotowych, nazwanych kombinacji (`_CATALOG_ROWS`,
> `coordinator_simulator.py:93-97`: `D_N_12H`, `SINGLE_24H`,
> `WEEKDAY_12H_WEEKEND_24H`), zamiast naprawdę zaznaczać/odznaczać każdy
> checkbox z osobna.

> "No w końcu. Sama nazwa mówi o co chodzi to Symulator zachowania
> koordynatora w programie, a wy napisaliście 20 testowych przejść przez
> solver."

> "Ok, przesadziłem, klikalne ekrany odłożymy na inny Symulator, bo sie
> zakopiemy w kodzie." — pełny UI/przeglądarka (Playwright + eksploracja
> wszystkich ekranów) świadomie POZA zakresem tego Tasku, zostaje na osobny,
> przyszły Symulator.

## 1. Co Wariant B ma naprawdę zmienić

Trzy niezależne poprawki, wszystkie konieczne, żadna sama nie wystarcza:

### 1.1 Prawdziwy kalkulator obsady, nie sztywna tabela

`employee_count = 5 * layer_count` znika. W jego miejsce: funkcja, która
liczy minimalną legalną obsadę z RZECZYWISTEGO wzoru zapotrzebowania
(wygenerowanego przez 1.2 niżej) — nie naiwnym dzieleniem
godziny/etat (to był błąd T038 v1: `ceil(monthly_hours_needed / 160)`
ignorował wymogi odpoczynku), tylko biorąc pod uwagę realne ograniczenia
odpoczynku między zmianami dla tej samej osoby (patrz `rota/planning/
constraints.py`, `rota/planning/eligibility.py` dla tego, co produkt
faktycznie egzekwuje — READ ONLY, ten Task nie zmienia `rota/**`, tylko czyta
je żeby wiedzieć, jakie ograniczenia kalkulator ma respektować).

Kalkulator musi mieć **własne, ręcznie zweryfikowane przypadki kontrolne**
(ten sam wzorzec co T043's `POLISH_2026_HOLIDAYS` + kontrole 160h/176h) —
np. "jedna ciągła warstwa 24/7 pokrywana D/N 12h wymaga dokładnie 5 osób,
sprawdzone ręcznie", "warstwa tylko-weekendowa (16h/tydzień) wymaga dokładnie
N osób, sprawdzone ręcznie" — zanim cokolwiek losowego zostanie do niego
podłączone.

**Twardy, zawsze uruchamiany warunek (nie punkt startowy, sprawdzenie po
KAŻDYM wygenerowanym przypadku)**: `zadeklarowana_liczba_osób ==
kalkulator(wygenerowany_wzór_zapotrzebowania) == faktycznie_użyta_liczba_osób
_w_gotowym_grafiku`. Rozjazd na którymkolwiek z tych trzech miejsc jest
FAIL narzędzia, nie ciekawostką do raportu. To jest bezpośrednia odpowiedź
na obawę OWNERA: "wpisze 8 osób na obiekt 5 osobowym i wesoło napisze, że
wszystko jest zielone" — to ma być niemożliwe do przeoczenia.

### 1.2 Swobodne generowanie wzoru zapotrzebowania, nie gotowe kształty

Zamiast wyboru z `_CATALOG_ROWS`'s trzech nazwanych kombinacji: generator
losuje NIEZALEŻNIE, dla każdego rodzaju zmiany (D/N/24h) i każdego dnia
tygodnia z osobna, czy ta zmiana w ogóle występuje tego dnia, i o jakich
godzinach (w granicach sensownych/legalnych czasów startu). To ma naturalnie
wytwarzać "tylko weekend", "tylko dni robocze", "tylko noce", i kombinacje,
których nikt nie nazwał z osobna — bez enumerowania ich jako oddzielne
"kształty". Struktura danych katalogu zmian (`kind, start, end,
required_primary_count, active_weekdays`) już to obsługuje —
`SiteShiftCatalog.tsx`'s checkboxy per dzień tygodnia to dokładnie ten sam
mechanizm w prawdziwym UI, potwierdzone działające.

Nie każda kombinacja wylosowanych dni/godzin/rodzajów zmian jest sensowna czy
legalna (np. zero pokrycia w ogóle, albo nakładające się zmiany bez
kontynuacji tej samej osoby — znany, świadomie nieobsługiwany przypadek z
T038/T039, patrz `coordinator_simulator.py:77-98`). Generator ma odrzucać/
ponownie losować niesensowne kombinacje, nie próbować budować dla nich
obiektu i potem tłumaczyć crasha jako "znaleziony błąd produktu" — to
rozróżnienie (odrzuć niesensowny wzór PRZED budową obiektu vs. zachowaj
realny błąd produktu PO próbie budowy sensownego obiektu) musi być jawne w
implementacji.

### 1.3 Hypothesis (stateful), prawdziwa zmienność między uruchomieniami

Zamiast `for seed in range(20)` (Wariant A, zostaje bez zmian, osobny plik/
funkcja): silnik oparty o Hypothesis (`RuleBasedStateMachine` albo
odpowiednik), który przy KAŻDYM pełnym uruchomieniu losuje NOWY zestaw
obiektów/sekwencji działań koordynatora (buduj obiekt → ustaw target →
zgłoś absencję → PLAN → ewentualny REPLAN → ...), sprawdzając po każdym
kroku niezmienniki takie jak ten z 1.1, oraz te już istniejące w Wariancie A
(B1 "zamknięty świat", B2 "produkcyjny validate", brief T043 sekcja 5).
Gdy Hypothesis znajdzie naruszenie, ma automatycznie skrócić je do
najmniejszego reproduktora (to jest wbudowana funkcja Hypothesis, "shrinking"
— nie trzeba jej implementować od zera).

Reprodukcja KONKRETNEGO znalezionego naruszenia nadal musi być deterministyczna
(zapisany seed/przykład, który da się odtworzyć) — to nie jest sprzeczne z
"prawdziwą zmiennością": zmienność dotyczy tego, co się bada PRZY KAŻDYM
uruchomieniu; reprodukcja dotyczy JEDNEGO konkretnego znaleziska, które chcesz
odtworzyć później.

## 2. Co NIE wchodzi w zakres tego Tasku

- **Pełny UI/przeglądarka** (wszystkie klikalne ekrany, wykrywanie "ścian" w
  nawigacji) — świadomie odłożone przez OWNERA na osobny, przyszły Symulator.
  Ten Task zostaje na poziomie API (`TestClient` + prawdziwy backend), jak
  Wariant A.
- **Evaluator sprawiedliwości jako funkcja produktu** — osobny, już zgłoszony
  temat (patrz `arch/REQUEST_SYMULATOR_WARIANT_B_2026-08-30.md`'s sekcja
  "Osobny problem"), nie mieszać z tym Taskiem. Wariant B może dalej używać
  istniejącego evaluatora z Wariantu A (`compute_fairness_facts`,
  `evaluate_fairness`) do raportowania faktów, ale decyzja "czy to ma być
  produkt" jest gdzie indziej.
- **Wariant A sam w sobie** — zostaje jako czujnik regresji, bez zmian. Ten
  Task go nie modyfikuje, nie zastępuje, nie usuwa.
- **Rozliczenie z Codexem** za wcześniejsze zignorowanie instrukcji o
  replay — OWNER świadomie to odpuszcza w tym briefie ("już mi wyjaśnił,
  zostawmy to").
- Wszystko, co T043 sekcja 9 już zakazywało (`rota/**`, `api/**`,
  `frontend/src/**`, `benchmarks/**`, drugi solver/validator, Cross-Site,
  wsparcie przed pierwszym PLAN, własny rachunek urlopu/L4, sieć w runtime) —
  te zakazy nie wygasły, obowiązują też tutaj.

## 3. Zamrożone decyzje z Wariantu A, które nadal obowiązują

Wariant B zmienia SPOSÓB generowania wejść, nie unieważnia żadnej z
zamrożonych decyzji T043 sekcja 2: prawdziwe produkcyjne ścieżki API (bez
monkeypatchowania PLAN/REPLAN/validate/analityki), target_hours jako
prawdziwe wejście (nie udział z workloadu), nieobecności przez prawdziwy
endpoint, testowa ścieżka EXTERNAL wyłącznie po realnym `DECISION_REQUIRED`
z zachowanym porządkiem zapisów (create-person niesie decision id, kolejne
zapisy null), zły grafik jako wynik badania (nie sygnał do zmiany wejścia),
granica twierdzeń o prawie (produkcyjny `validate()` to stan HARD
zaimplementowany w produkcie, nie certyfikat całego Kodeksu pracy).

## 4. PREIMPLEMENTATION REDUCTION GATE

| Element | Źródło | Konieczność | Redukcja |
|---|---|---|---|
| prawdziwy kalkulator obsady | OWNER 2026-08-30, zastępuje T043's sztywną tabelę | bez tego cały generator testuje fikcyjne obiekty | jedna funkcja + własne ręcznie zweryfikowane przypadki kontrolne |
| asercja deklaracja=kalkulacja=użycie | OWNER 2026-08-30 wprost | zapobiega "8 osób na obiekcie 5-osobowym, wesoło zielone" | jedno sprawdzenie, uruchamiane po każdym przypadku |
| swobodne dni tygodnia/rodzaj zmiany | OWNER 2026-08-30, potwierdzone że mechanizm produktu (checkboxy) już to obsługuje | usuwa ukryte założenie "gotowego kształtu" | losowanie niezależne per (dzień, rodzaj zmiany), reużywa istniejącą strukturę katalogu |
| Hypothesis stateful | OWNER 2026-08-30 + T043 brief.md sekcja 7 (odłożone "na potem" -- to jest teraz) | prawdziwa zmienność między uruchomieniami | jeden stateful engine, reużywa produkcyjne helpery z Wariantu A (`build_object`, `run_plan`, `external_support_reaction` itd.) |

Nie powstają: pełny UI/Playwright-eksploracja wszystkich ekranów, evaluator
sprawiedliwości jako produkt, drugi solver/validator, zmiana Wariantu A.

## 5. TASK_SCOPE (wstępna propozycja CC — ChatGPT pisze finalny Task, może to zawęzić/rozszerzyć z uzasadnieniem)

TASK_SCOPE:
- `tests/property/coordinator_simulator.py` (nowe funkcje: kalkulator,
  swobodny generator wzoru zapotrzebowania — Wariant A's istniejące funkcje
  pozostają nietknięte/reużywane, nie kasowane)
- `tests/property/test_coordinator_simulator_variant_b.py` (nowy plik —
  Wariant B jako osobny plik testowy, nie mieszany z Wariantu A istniejącym
  `test_coordinator_simulator.py`, żeby nie zagrozić już działającemu
  czujnikowi regresji)
- `tasks/ROTA-T044/brief.md`
- `tasks/ROTA-T044/round_01/tests/**`

Zabronione: `rota/**`, `api/**`, `frontend/src/**`, `benchmarks/**`,
modyfikacja istniejących plików Wariantu A (`tests/property/
coordinator_simulator.py`'s już istniejące funkcje, `tests/property/
test_coordinator_simulator.py`) poza dodaniem nowych, addytywnych funkcji
które Wariant B reużywa.

## 6. Warunki zatrzymania

Implementer zatrzymuje się i zgłasza problem, jeżeli:
- kalkulator obsady nie da się zweryfikować ręcznie na małym zestawie
  przypadków kontrolnych przed podłączeniem go do losowania;
- asercja deklaracja=kalkulacja=użycie wymagałaby zmiany produktu
  (`rota/**`/`api/**`) żeby zadziałać;
- Hypothesis stateful wymaga symulowania czegoś, co dziś nie ma
  odpowiednika w prawdziwym produkcyjnym API (patrz T043 sekcja 12, te same
  zasady);
- odróżnienie "odrzuć niesensowny wzór przed budową" od "zachowaj realny
  błąd produktu po próbie" okazuje się niejednoznaczne dla jakiejś klasy
  wygenerowanych wzorów — zgłosić, nie zgadywać.

## 7. Pytania do niezależnego audytu Codexa

1. Czy kalkulator obsady faktycznie liczy z ograniczeń odpoczynku, nie samą
   naiwną arytmetyką godziny/etat (dokładnie błąd T038 v1)?
2. Czy asercja deklaracja=kalkulacja=użycie jest uruchamiana dla KAŻDEGO
   wygenerowanego przypadku, nie tylko przy starcie?
3. Czy swobodne losowanie dni tygodnia/rodzaju zmiany faktycznie może
   wyprodukować "tylko weekend"/"tylko noc"/"tylko dni robocze" bez ich
   enumerowania jako osobne nazwane kształty?
4. Czy dwa kolejne pełne uruchomienia bez wspólnego seeda dają WIDOCZNIE
   różne zestawy obiektów (nie tylko różne w teorii)?
5. Czy Wariant A pozostaje nietknięty i nadal działa jako czujnik regresji?
6. Czy rozróżnienie "niesensowny wzór odrzucony przed budową" vs. "realny
   błąd produktu zachowany po próbie" jest jawnie zaimplementowane, nie
   domyślne?

Do zamknięcia audytu: **implementacja czeka na PASS Codexa na tym briefie,
potem na Task napisany przez ChatGPT, potem na jawne polecenie "adwokat
diabła" dla CC przed jakimkolwiek kodowaniem.**

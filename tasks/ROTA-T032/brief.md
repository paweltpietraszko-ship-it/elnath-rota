# ROTA-T032 — SOFT ranking, max 2 N pod rząd i budżet planowania

Status: **READY FOR CODEX PREIMPLEMENTATION RE-AUDIT — CC READ-ONLY UNTIL PASS**

ARCHITECT_INPUT_SHA: `7d61f19831940f5cf5045e4a4d55a87e362dab57`
BASE_MAIN_SHA: `3be4ed37e735766a80ca2259c7d1b6981d22dbb5`
R1_AUDIT: `tasks/ROTA-T032/round_01/tests/tests_r1.txt`
R2_AUDIT: `tasks/ROTA-T032/round_01/tests/tests_r2.txt`
R3_AUDIT: `tasks/ROTA-T032/round_01/tests/tests_r3.txt`
OWNER_CORRECTED: 2026-08-25

Ta wersja jest konsolidacją po R3. Usuwa dwie nadmiarowe konstrukcje z poprzedniego kontraktu:

- **nie powstaje `continue_plan_search()`, incumbent protocol, solution-hint/no-good protocol ani nowa operacja application-layer**;
- **T028 nie implementuje trzeciego licznika NIGHT-STREAK** — jego istniejący obowiązek wywołania produkcyjnego `validate()` jest wystarczającym bezpiecznikiem po wdrożeniu nowego HARD.

T032 domyka tylko:

1. HARD: maksymalnie dwie kolejne N;
2. TARGET equity jako dodatkowy SOFT po zachowaniu TARGET-01;
3. reward D → N → wolne → wolne;
4. jeden budżet 180 s dla publicznego planowania;
5. minimalny sygnał `optimization_complete` i przyszły UX loader/retry.

Nie powstaje nowy model grafiku, nowy persisted state, job queue, background worker, solver session, procentowy progress ani nowy PlanningStatus.

---

## 1. WYNIK PRODUKTOWY

### 1.1 HARD

Ten sam pracownik **nigdy nie może dostać więcej niż dwóch kolejnych zmian N**.

`N / N` — legalne.

`N / N / N` — niedozwolone.

To jest `NIGHT-STREAK-01` HARD, nie fairness, score, warning ani wyjątek do zaakceptowania.

### 1.2 SOFT

Po spełnieniu HARD solver preferuje:

- jak najmniejsze istniejące łączne odchylenie od effective targetów (`TARGET-01`);
- przy tym samym udowodnionym optimum TARGET-01 — bardziej równomierny procent realizacji indywidualnych effective targetów;
- więcej okien `D → N → wolne → wolne`;
- istniejące weekend/holiday/DAY_SHIFT_OFF/LEAVE_PLAN SOFT pozostają aktywne.

### 1.3 Czas

Jedna publiczna operacja planowania może pracować maksymalnie **180 sekund**.

Jeżeli po 180 s istnieje pełny kandydat zgodny z HARD, może zostać pokazany jako `FEASIBLE` z `optimization_complete=False`, zgodnie z §6.

---

## 2. OWNERZY — BEZ NOWYCH RÓWNOLEGŁYCH MECHANIZMÓW

Pozostają istniejący ownerzy:

- `rota/planning/constraints.py` — CP-SAT HARD;
- `rota/planning/solver.py` — model, fazy, objective i remaining time;
- `rota/planning/validator.py` — niezależny mirror każdego HARD;
- `rota/planning/fairness.py` — helpery SOFT;
- `_effective_targets(state)` — canonical effective target;
- istniejąca arytmetyka TARGET-01 — canonical actual hours;
- `rota.planning.shift_catalog.classify_demand` — jedyny owner D/N;
- `rota/application/plan_ops.py::plan_month()` i istniejący `replan()` — publiczne application operations.

T032 **nie dodaje nowej publicznej operacji dalszego szukania**. Retry reuse istniejącego `plan_month()` na aktualnym CURRENT WORKING ScheduleVersion.

Po pierwszym `replan()` utworzony child jest CURRENT WORKING; kolejne „Szukaj dalej” wywołuje zwykłe PLAN na tym childzie, a nie `replan()` ponownie.

---

## 3. HARD `NIGHT-STREAK-01`

### 3.1 Semantyka

Dla jednego pracownika nie może istnieć trójka kolejnych **dat startu** `(d, d+1, d+2)`, na których finalny target-Site grafik zawiera non-CANCELLED PRIMARY N tego pracownika na każdej z trzech dat.

- D nie liczy się jako N;
- TRAINEE nie tworzy N dla tej reguły;
- CANCELLED nie tworzy N;
- N rozpoznaje wyłącznie produkcyjny `classify_demand`, nigdy godzina startu ani długość Assignmentu.

### 3.2 Fakty

Reguła widzi:

- nowo wybierane PRIMARY (`x`);
- non-CANCELLED fixed existing target-Site PRIMARY pozostające w solve/replan;
- istniejące target-Site `boundary_assignments` z jednoznacznie matching `boundary_shift_demands`.

Nie widzi:

- `other_site_assignments`;
- TRAINEE jako N;
- redistributable baseline drugi raz.

Fixed/boundary Assignment bez matching demand nie jest zgadywany jako D/N.

### 3.3 Granica miesiąca

Max-2-N obowiązuje przez granicę miesiąca/roku, jeżeli potrzebny target-Site boundary fact już istnieje w canonical state.

Przykład zakazany przy planowaniu października:

- 30.09 — persisted PRIMARY N;
- 01.10 — N;
- 02.10 — N.

Bez nowego history store, DTO i persistence.

### 3.4 Solver + validator

W `constraints.py` powstaje jeden CP-SAT HARD, np. `add_max_two_consecutive_night_constraints(...)`, podpięty przez `solver.py`.

Zakazane są:

- `night_streak_excess_count`;
- NIGHT_STREAK weight;
- soft phase;
- override tego HARD.

`validator.py` niezależnie od solverowego helpera powtarza tę regułę od zera na finalnych Assignmentach + canonical boundary facts.

Violation/raw code: `NIGHT-STREAK-01`.

To obowiązkowy anti-drift mirror HARD, nie powielenie produktu.

### 3.5 DECISION_REQUIRED

Jeżeli brak automatycznego pełnego grafiku wynika z `NIGHT-STREAK-01`, wynik ma trafić do istniejącej ścieżki `DECISION_REQUIRED`, nie zostać nazwany `REST-01` ani `TECHNICAL_ERROR`.

`DecisionRequiredPayload` pozostaje jedynym DTO.

W `decision_guidance.py` dochodzi wyłącznie tekst:

`NIGHT-STREAK-01` → `Koliduje z limitem dwóch nocek pod rząd`.

Nie dodawać opcji zaakceptowania trzeciej N.

### 3.6 24h

T032 **nie dodaje specjalnej logiki 24h do NIGHT-STREAK**.

Istniejący HARD odpoczynku po służbie 24h jest jedynym ownerem wymaganej 24h przerwy i sam uniemożliwia N następnego dnia. Nie duplikować tej ochrony.

---

## 4. TARGET EQUITY

### 4.1 Jeden owner godzin

Dla każdego pracownika z istniejącego `target_by_employee`:

- `effective_target` = dokładnie `_effective_targets(state)`;
- `actual_hours` = dokładnie expression już używany przez TARGET-01;
- T032 nie przelicza absencji ani godzin drugim kodem.

Solver wyprowadza actual hours i absolutne odchylenia raz i reuse je w TARGET-01 oraz equity.

### 4.2 Metryka

Dla `effective_target > 0`:

`completion_pct = floor(100 * actual_hours / effective_target)`.

Bez capu na 100%.

Dla co najmniej dwóch dodatnich effective targetów:

`target_equity_spread = max(completion_pct) - min(completion_pct)`.

Mniejszy spread jest lepszy.

`effective_target == 0` wyłącza pracownika wyłącznie z ratio; TARGET-01 nadal liczy jego odchylenie od 0.

### 4.3 TARGET-01 ma pierwszeństwo

Po istniejących silniejszych fazach REPLAN-MIN i — gdy aktywna — exceptional-N solver najpierw optymalizuje:

`total_target_deviation = sum(|actual_hours - effective_target|)`.

Jeżeli uzyska `OPTIMAL`, blokuje tę wartość i dopiero wtedy uruchamia equity oraz pozostałe finalne SOFT.

**Equity nigdy nie może świadomie kupić gorszego udowodnionego TARGET-01.**

Jeżeli 180 s kończy się podczas fazy TARGET-01 po znalezieniu FEASIBLE, lecz przed `OPTIMAL`, solver zwraca ten HARD-poprawny incumbent jako partial FEASIBLE i **nie przechodzi już do equity/rhythm**, ponieważ optimum TARGET-01 nie zostało udowodnione.

### 4.4 Helper

W `fairness.py`:

`TARGET_EQUITY_WEIGHT = 1`.

`TARGET_DEVIATION_WEIGHT = 100` pozostaje bez zmiany.

`add_target_equity_fairness(...)` dostaje już wyprowadzone actual hours i effective targets; nie czyta WorkBalance/Availability/persistence.

---

## 5. REWARD `D → N → WOLNE → WOLNE`

To wyłącznie same-month SOFT.

`DN_RHYTHM_REWARD_WEIGHT = 1`.

Dla okna czterech kolejnych dat startu `(d, d+1, d+2, d+3)` całkowicie wewnątrz `state.month` trafienie istnieje tylko gdy:

1. w `d` startuje dokładnie jeden non-CANCELLED Assignment pracownika i jest PRIMARY D;
2. w `d+1` startuje dokładnie jeden non-CANCELLED Assignment i jest PRIMARY N;
3. w `d+2` nie startuje żaden non-CANCELLED Assignment tego pracownika;
4. w `d+3` nie startuje żaden non-CANCELLED Assignment tego pracownika.

N kończąca się rano w `d+2` nie psuje tego wzorca. „Wolne” oznacza tutaj brak nowego startu; odpoczynek godzinowy pozostaje wyłącznie własnością REST/WEEKLY-REST.

Fixed target-Site facts uczestniczą. Redistributable baseline nie jest liczony drugi raz. Other-Site nie uczestniczy.

Reward = suma trafień wszystkich pracowników. Brak wspólnej fazy brygady i brak cross-month rewardu.

---

## 6. JEDEN BUDŻET 180 S

### 6.1 Deadline

`PLANNING_OPERATION_BUDGET_SECONDS = 180`.

Deadline powstaje raz na początku publicznego `plan(state)` z monotonicznego zegara.

Każdy wewnętrzny CP-SAT solve, fallback, faza leksykograficzna i search wariantów dostaje wyłącznie **pozostały czas** do tego samego deadline.

Nie resetować pełnych 180 s per solve/faza.

Testy używają fake clock albo małego test budgetu; nie śpią 180 s.

### 6.2 Istniejące silniejsze fazy pozostają fail-closed

T032 nie rozluźnia REPLAN-MIN ani exceptional-N.

Jeżeli deadline kończy się przed udowodnieniem wymaganego `OPTIMAL` którejkolwiek z tych istniejących silniejszych faz:

- brak partial FEASIBLE;
- `TECHNICAL_ERROR + optimization_complete=False`.

### 6.3 Partial FEASIBLE

Po ukończeniu aktywnych silniejszych faz:

- timeout podczas TARGET-01 z FEASIBLE incumbent → zwróć incumbent, nie uruchamiaj późniejszych SOFT;
- timeout podczas finalnego SOFT po udowodnionym TARGET optimum → zwróć najlepszy znaleziony incumbent.

W obu przypadkach:

- status `FEASIBLE`;
- independent validator musi PASS;
- `optimization_complete=False`.

Jeżeli wszystkie wymagane fazy/objective są udowodnione w czasie → `optimization_complete=True`.

Jeżeli do deadline nie ma HARD-poprawnego kandydata ani dowodu normalnego `DECISION_REQUIRED` → `TECHNICAL_ERROR + optimization_complete=False` z czytelnym komunikatem o wyczerpaniu czasu.

Udowodniony przed deadline `DECISION_REQUIRED` pozostaje zwykłym kompletnym wynikiem.

### 6.4 Minimalne DTO

Do końca `PlanningResult`:

`optimization_complete: bool = True`.

Bez nowego statusu `PARTIAL`, solver score DTO, job ID i persisted session.

---

## 7. „SZUKAJ DALEJ” — REUSE ISTNIEJĄCEGO PLAN

### 7.1 Bez nowej komendy

Po `FEASIBLE + optimization_complete=False` koordynator może wybrać:

- `Użyj tego grafiku` — istniejący `select_candidate`;
- `Szukaj dalej` — ponowne wywołanie istniejącego PLAN na tym samym CURRENT WORKING version.

Nie dodawać `continue_plan_search()`.

Dla REPLAN:

1. pierwsze `replan()` tworzy jeden WORKING child;
2. jeżeli koordynator chce szukać dalej, **nie wywołuje się drugi raz `replan()`**;
3. używa się zwykłego `plan_month()` na już istniejącym CURRENT WORKING child.

Poprzedni poprawny kandydat pozostaje po stronie UI dostępny jako fallback i nie jest automatycznie persystowany ani usuwany.

### 7.2 Jedyny nowy parametr retry

Istniejący PLAN dostaje opcjonalny, nietrwały parametr:

`search_attempt: int = 0`.

Semantyka:

- pierwszy przebieg: `search_attempt=0`, zachowuje dotychczasowy deterministyczny przebieg;
- każde `Szukaj dalej`: frontend zwiększa wartość (`1`, `2`, ...);
- parametr wpływa wyłącznie na **CP-SAT search seed/order**, nie na model, HARD, objective ani PlanningState;
- nie jest persystowany i nie jest częścią ScheduleVersion.

Solver ma użyć wartości attempt do uruchomienia rzeczywiście innego przebiegu wyszukiwania (np. przez wspierane przez CP-SAT ustawienia random seed/search randomization). Nie wolno ponownie uruchamiać identycznego `seed=0` i nazywać tego „szukaniem dalej”.

Nie jest gwarantowane znalezienie innego grafiku. Jeżeli kolejny przebieg zwróci tę samą konfigurację albo nic lepszego/innego nie znajdzie w budżecie, UI zachowuje poprzedni kandydat i może poinformować, że nie znaleziono innej konfiguracji.

### 7.3 Bez comparatora i bez incumbent protocol

T032 nie dodaje:

- payloadu poprzedniego kandydata do backendu;
- solution hintu między requestami;
- no-good/diversity cutu między requestami;
- post-hoc kalkulatora pełnej objective;
- persistent search state.

Dlatego przycisk nazywa się **`Szukaj dalej`**, a nie obiecuje, że następny wynik będzie matematycznie lepszy.

---

## 8. UX I TIMEOUT TRANSPORTOWY — BINDING DLA CC

### 8.1 Loader

Podczas trwającego PLAN/REPLAN/retry koordynator ma widzieć:

- spinner albo indeterminate progress bar;
- tekst np. `Układam grafik — to może potrwać do 3 minut`;
- zablokowanie podwójnego uruchomienia;
- brak wymyślonego procentu postępu.

### 8.2 Timeout frontendu

Obecny globalny `REQUEST_TIMEOUT_MS = 20000` pozostaje dla zwykłych krótkich endpointów.

Docelowy PLAN/REPLAN/retry musi używać per-request override:

`PLANNING_REQUEST_TIMEOUT_MS = 195000`.

To 180 s backend budget + 15 s marginesu transportu/serializacji.

Nie podnosić globalnego timeoutu wszystkich requestów.

### 8.3 Wynik w UI

`FEASIBLE + optimization_complete=False`:

- pokaż znaleziony grafik normalnie;
- komunikat: `Znaleziono poprawny grafik. Szukać dalej?`;
- akcje: `Użyj tego grafiku` / `Szukaj dalej`.

`optimization_complete=True`:

- brak automatycznego pytania o dalsze szukanie.

`TECHNICAL_ERROR + optimization_complete=False` bez kandydata:

- czytelny komunikat o upływie 3 minut;
- możliwość ponowienia;
- bez stack trace.

### 8.4 Granica branchu

T032 nie tworzy nieistniejącego jeszcze ekranu/routera Planowanie tylko po to, aby zamknąć UX.

Binding future seam jest jednak jednoznaczny: per-request 195 s timeout, loader, `optimization_complete`, opcjonalny `search_attempt` i akcja `Szukaj dalej`.

---

## 9. T028 — BEZ TRZECIEGO OWNERA NIGHT-STREAK

T028 **nie dostaje własnego algorytmu wykrywania serii N**.

Po wdrożeniu T032 produkcyjny validator ma niezależnie od solvera odrzucać każdy finalny kandydat z `NIGHT-STREAK-01`.

T028 już ma obowiązek wywołać produkcyjny `validate()` dla każdego FEASIBLE kandydata. To wystarcza: jeśli solver kiedykolwiek przepuści N/N/N, validator odrzuci kandydat i istniejący poligon uzna przypadek za FAIL.

Nie dodawać:

- `QUALITY_FAIL` liczonego lokalnie z serii N;
- lokalnego `classify_demand` loop tylko dla T028;
- trzeciej implementacji max-2-N.

Po integracji T032 należy uruchomić istniejący T028 jako regresję. Można dodać scenariusz wejściowy zwiększający szansę ekspozycji N-streak, ale oracle pozostaje produkcyjny validator + istniejące generic checks T028.

---

## 10. SCOPE

### Production — dozwolone

- `rota/planning/constraints.py` — HARD `NIGHT-STREAK-01`;
- `rota/planning/solver.py` — wiring HARD, target/equity/rhythm, operation deadline, `search_attempt` → search seed/order;
- `rota/planning/validator.py` — niezależny mirror HARD;
- `rota/planning/fairness.py` — equity + rhythm;
- `rota/planning/engine.py` — deadline/partial disposition i poprawna diagnoza NIGHT-STREAK;
- `rota/planning/engine_types.py` — wyłącznie `PlanningResult.optimization_complete`;
- `rota/planning/decision_guidance.py` — wyłącznie label `NIGHT-STREAK-01`;
- `rota/application/plan_ops.py` — wyłącznie przekazanie opcjonalnego `search_attempt` przez istniejący `plan_month()`; bez nowej operacji.

### Testy

- `tests/test_t032_soft_ranking.py`;
- opcjonalnie `tests/test_t032_night_streak.py` dla czytelności;
- istniejące regresje ownerów, w tym T028 po integracji.

### Zakazane

- `continue_plan_search()` lub inna nowa publiczna komenda retry;
- incumbent/hint/no-good protocol między requestami;
- persistence/job queue/background worker;
- solver score/comparator DTO;
- nowy PlanningStatus;
- trzeci NIGHT-STREAK owner w T028;
- specjalna logika NIGHT-STREAK dla 24h;
- cross-Site night streak;
- cross-month rhythm reward;
- nowe REST/WEEKLY/LOAD semantics;
- nowy model absencji/targetu;
- sztywny grafik brygadowy;
- nowy override HARD.

---

## 11. MINIMALNA MACIERZ ODBIORU

### NIGHT-STREAK-01

T32-N1 — N/N legalne; N/N/N niedozwolone.

T32-N2 — persisted N poprzedniego miesiąca + N/N bieżącego jest zablokowane.

T32-N3 — D/N/N i N/wolne/N nie są trójką N.

T32-N4 — fixed target-Site PRIMARY uczestniczy; redistributable baseline bez double count.

T32-N5 — TRAINEE/CANCELLED nie tworzą N; other-Site nie uczestniczy.

T32-N6 — validator odrzuca wstrzyknięty N/N/N także przez boundary kodem `NIGHT-STREAK-01`.

T32-N7 — infeasible przez ten HARD trafia do `DECISION_REQUIRED` z właściwą przyczyną, nie jako `REST-01`.

T32-N8 — 24h rest pozostaje jedynym ownerem przerwy po 24h; brak special-case w NIGHT-STREAK.

### TARGET EQUITY

T32-A1 — przy tym samym TARGET-01 mniejszy completion spread wygrywa.

T32-A2 — różne targety: proporcjonalność wygrywa nad równymi surowymi godzinami przy tej samej wcześniejszej jakości.

T32-A3 — effective target uwzględnia canonical absence_hours.

T32-A4 — target=0 nie powoduje dzielenia/model invalid; TARGET-01 nadal działa.

T32-A5 — surplus >100% nie jest capowany.

T32-A6 — real `solve()` z ≥4 równymi targetami i równomiernie rozdzielalnym shortage daje równy rozkład godzin.

### D/N RHYTHM

T32-B1 — więcej D→N→wolne→wolne trafień wygrywa przy tej samej wcześniejszej jakości.

T32-B2 — wiele trafień/wielu pracowników sumuje się bez wspólnej fazy.

T32-B3 — N kończąca się rano dnia wolnego nie niszczy start-day rhythm.

T32-B4 — fixed target-Site facts uczestniczą; TRAINEE może zająć dzień wolny, ale nie spełnia D/N.

T32-B5 — reward nie przechodzi przez granicę miesiąca.

### BUDŻET

T32-T1 — jeden fake 180 s deadline jest współdzielony przez wszystkie wewnętrzne solve; brak resetu.

T32-T2 — timeout podczas REPLAN-MIN/exceptional-N pozostaje fail-closed.

T32-T3 — timeout podczas TARGET-01 po FEASIBLE, przed OPTIMAL → partial FEASIBLE, validator PASS, bez uruchomienia equity/rhythm.

T32-T4 — timeout podczas finalnego SOFT po target OPTIMAL → partial FEASIBLE, validator PASS.

T32-T5 — pełne zakończenie → `optimization_complete=True`.

T32-T6 — brak kandydata/proof decision → `TECHNICAL_ERROR + optimization_complete=False`.

T32-T7 — normalny `DECISION_REQUIRED` nie jest maskowany timeoutem.

T32-T8 — default `optimization_complete=True` zachowuje stare konstruktory.

### RETRY / REUSE

T32-C1 — pierwsze PLAN używa `search_attempt=0`; retry istniejącym `plan_month()` na tym samym CURRENT WORKING używa `search_attempt>0`.

T32-C2 — po pierwszym REPLAN retry nie tworzy drugiego child; używa PLAN na aktualnym WORKING child.

T32-C3 — różny `search_attempt` rzeczywiście zmienia CP-SAT search seed/order, ale nie model/HARD/objective.

T32-C4 — `search_attempt` nie jest persystowany i nie zmienia ScheduleVersion.

T32-C5 — brak incumbent payload, hintu, no-good cutu i nowego application command.

### FUTURE UI/API CONTRACT

T32-U1 — planning request ma per-request 195000 ms timeout; globalny default pozostaje 20000 ms.

T32-U2 — loader/spinner przez cały request; brak fake %.

T32-U3 — partial FEASIBLE pokazuje grafik + `Użyj tego grafiku` / `Szukaj dalej`; retry zachowuje poprzedni wynik po stronie UI.

Te punkty są binding dla przyszłego ekranu/routera, ale nie wymagają tworzenia scaffoldu na T032.

### Regresja

T32-R1 — REST/WEEKLY/LOAD/coverage/eligibility pozostają zielone.

T32-R2 — weekend/holiday fairness, DAY_SHIFT_OFF, LEAVE_PLAN, REPLAN-MIN i exceptional-N zachowują swoje role.

T32-R3 — żaden timeout nie omija independent validator przed publicznym FEASIBLE.

T32-R4 — po integracji T032 istniejący T028 FAILuje każdy FEASIBLE kandydat odrzucony przez produkcyjny validator; brak lokalnej kopii NIGHT-STREAK.

---

## 12. PREIMPLEMENTATION RE-AUDIT

Independent Codex audituje exact HEAD wyłącznie pod R3 i tę redukcję architektury.

Required checks:

1. Czy R3-1 jest zamknięty per-request timeoutem 195 s bez zmiany globalnego 20 s defaultu?
2. Czy R3-2 jest zamknięty przez reuse istniejącego `plan_month()` + nietrwały `search_attempt`, bez nowej operacji, incumbent protocol, hint/no-good i bez kolejnego REPLAN child?
3. Czy `search_attempt` rzeczywiście zmienia przebieg CP-SAT, ale nie zmienia modelu/rankingu produktu?
4. Czy R3-3 zachowuje fail-closed REPLAN-MIN/exceptional-N, a partial FEASIBLE zaczyna się dopiero później?
5. Czy timeout podczas nieudowodnionego TARGET-01 zwraca incumbent bez uruchamiania equity/rhythm, dzięki czemu equity nie może kupić gorszego targetu?
6. Czy NIGHT-STREAK pozostaje jednym HARD w solverze + obowiązkowym independent validator mirror, bez trzeciego ownera w T028 i bez special-case 24h?
7. Czy T028 może polegać na swoim istniejącym obowiązku `validate()` zamiast lokalnie powielać regułę?
8. Czy scope nie tworzy job queue, persistence solvera, comparatora, fake progress ani nowego modelu planowania?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` z numerowanymi pozostałymi defektami kontraktu.

Do PASS: **CC READ-ONLY / NOT READY FOR IMPLEMENTATION**.

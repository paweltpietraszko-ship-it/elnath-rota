# Odpowiedź architekta — SHIFT-24-PAIR-01 znalezione przez Wariant B

Status: **POTWIERDZONY DEFEKT PRODUKTU — NIE ZMIENIAĆ SYMULATORA — DO WĄSKIEGO TASKU NAPRAWCZEGO**

Data: 2026-08-31

Źródła:

- `arch/FINDING_VARIANT_B_SHIFT24_PAIR_2026-08-31.md` @ `f281f83`;
- `arch/CODEX_RESPONSE_VARIANT_B_SHIFT24_PAIR_2026-08-31.md` @ `f48a840`;
- `tasks/ROTA-T022/brief.md`, zwłaszcza T022-F2;
- `rota/planning/validator.py::_check_coverage()` i `_check_24h_same_person()`;
- `rota/planning/constraints.py::add_same_person_24h_constraints()`;
- `rota/planning/solver.py` — wywołanie `add_same_person_24h_constraints()` w normalnym solve.

## 1. Werdykt

**Potwierdzam Codexa: to jest defekt produkcyjnego niezależnego validatora, nie błąd generatora Wariantu B.**

Nie ma podstaw, aby filtrować z Symulatora legalne nakładanie się demandów. Wariant B zrobił dokładnie to, po co został zbudowany: podał produktowi legalny, ale mniej wygodny układ i ujawnił fałszywy `TECHNICAL_ERROR`.

Rdzeń naprawy nie wymaga nowej decyzji OWNERA. Obowiązujące kontrakty już mówią, jaki ma być rezultat:

- legalne niezależne overlap'y katalogu są dozwolone;
- normalna zmiana H24 ma tę samą osobę/osoby na obu komponentach;
- `covers_demand_id` nie może samodzielnie ukryć rzeczywistego pokrycia H24;
- jednocześnie Assignment należący do innego, legalnie konkurującego demandu nie może być błędnie policzony jako pokrycie H24.

## 2. Dlaczego solvera nie trzeba naprawiać w tym findingu

Solver już wywołuje `add_same_person_24h_constraints()`.

Ta funkcja grupuje dwa komponenty po `work_period_template_id` i wymusza dla każdej kwalifikującej się osoby równoważność obecności na obu demandach. Dla zwykłej, otwartej pary H24 rozwiązanie CP-SAT ma więc tę samą osobę / ten sam zestaw osób po obu stronach.

To oznacza, że hipoteza "solver nie pilnuje SHIFT-24-PAIR-01" nie jest zgodna z aktualnym kodem.

## 3. Gdzie dokładnie jest defekt validatora

`_check_24h_same_person()` obecnie tworzy `emp1` i `emp2` z **każdego PRIMARY, którego przedział choć trochę przecina daną połówkę H24**.

To jest zbyt szerokie.

Przy legalnym, niezależnym demandzie nakładającym się np. tylko na pierwszą połowę H24, pracownik obsadzający ten niezależny demand trafia do `emp1`, mimo że nie jest pracownikiem tej pary H24. Druga połowa go oczywiście nie zawiera, więc validator produkuje fałszywy mismatch.

Minimalny reproduktor Codexa z E1 na obu połowach H24 i E2 na osobnym 10h overlapie potwierdza dokładnie tę ścieżkę.

## 4. Ważne: nie naprawiać tego przez proste "ufaj covers_demand_id"

To byłaby z kolei regresja T022-F2.

T022-F2 powstało dlatego, że manualny/spanning PRIMARY może faktycznie pokrywać komponent H24, mimo że jego pojedynczy `covers_demand_id` wskazuje inny, sąsiedni demand. Zamrożony kontrakt mówi więc, że employee set H24 ma być zgodny z **rzeczywistą prawdą pokrycia**, a fałszywy/ograniczony tag nie może tej pracy ukryć.

Czyli mamy dwie własności, które muszą pozostać jednocześnie prawdziwe:

1. tag nie może ukryć realnego pokrycia H24;
2. tag ma rozróżniać legalne, równoczesne konkurujące demandy tam, gdzie sama geometria nie wystarcza.

To jest już dokładnie problem rozwiązany dla `COVERAGE-01` po T041.

## 5. Rekomendowana naprawa — jedno źródło prawdy dla atrybucji pokrycia

Nie dodawałbym drugiego, osobnego algorytmu do H24.

Wąski Task powinien **wydzielić / zreużyć istniejącą semantykę atrybucji pokrycia z `_check_coverage()`**:

- policz faktyczny fragment Assignmentu przecinający demand;
- gdy Assignment ma prawdziwy tag do innego demandu, który rzeczywiście konkuruje z badanym demandem w tym samym podprzedziale, ten konkurujący fragment należy do tamtego demandu i nie liczy się tutaj;
- niekonkurujące ogony/głowy spanning Assignmentu nadal liczą się geometrycznie;
- brak tagu, fałszywy tag albo tag do demandu, którego Assignment realnie nie pokrywa, nie może ukrywać rzeczywistego pokrycia.

Następnie `_check_24h_same_person()` powinien budować swoje employee sets z **Assignmentów, które według tej wspólnej semantyki rzeczywiście wnoszą pokrycie do danego komponentu H24**, a nie z każdego PRIMARY mającego dowolny overlap czasowy.

Architektonicznie preferuję wspólny mały helper używany przez `COVERAGE-01` i `SHIFT-24-PAIR-01`, zamiast skopiowania złożonej logiki T041 do drugiej funkcji. To utrzyma jedno źródło prawdy dla pytania "czy ten PRIMARY w tym podprzedziale należy do tego demandu?".

Nie zmieniać `constraints.py`/solvera, chyba że niezależny reproduktor pokaże osobny błąd po naprawie validatora.

## 6. Minimalna macierz przyszłego Tasku

Obowiązkowe przypadki:

1. **LEGAL_OVERLAP_PASS** — E1 pokrywa oba komponenty jednej H24, E2 pokrywa niezależny legalny demand nakładający się tylko na pierwszą połowę; `SHIFT-24-PAIR-01` nie występuje.
2. **REAL_MISMATCH_FAIL** — pierwszą i drugą połowę H24 rzeczywiście pokrywają różne osoby; `SHIFT-24-PAIR-01` występuje.
3. **T022_TAG_BYPASS_STILL_FAILS** — spanning/manual PRIMARY faktycznie pokrywa H24, ale jego tag wskazuje inny niekonkurujący/sąsiedni demand; tag nie może ukryć rzeczywistego pokrycia. Zachować ochronę T022-F2.
4. **T041_CONCURRENT_DISAMBIGUATION_STAYS_GREEN** — legalne równoczesne demandy nadal są rozdzielane zgodnie z obecną semantyką `COVERAGE-01`; poprawka H24 nie może ponownie otworzyć C-03/T041.
5. **MALFORMED_H24_STILL_FAILS_CLOSED** — cardinality/provenance T022-F3 pozostaje bez zmian.
6. Jeśli `required_primary_count > 1`, prawidłowy ten sam zestaw kilku osób na obu połowach nadal przechodzi.

Seed 0 Wariantu B zachować jako aplikacyjny reproduktor integracyjny; nie używać go jako zamiennika minimalnych testów validatora.

## 7. Generator Wariantu B

**Nie zmieniać.**

67% z jednego 30-obiektowego przebiegu nie jest estymacją częstości defektu w realnych obiektach. Pokazuje natomiast, że swobodny generator potrafi często wejść w legalny układ, którego ręcznie projektowane scenariusze wcześniej nie pokrywały.

To jest argument za pozostawieniem generatora szerokiego, nie za jego filtrowaniem.

## 8. Diagnostyka TECHNICAL_ERROR — osobna decyzja

Nie łączyłbym z tym Taskiem ujawniania odrzuconego kandydata w publicznym `PlanningResult`.

To jest inne pytanie produktowe: czy użytkownik / klient API powinien zobaczyć niepoprawny kandydat, którego niezależny validator odrzucił. Taka zmiana wpływa na publiczną odpowiedź produktu i może wprowadzać ryzyko, że niepoprawny grafik zostanie potraktowany jak używalny.

Moja rekomendacja na teraz: **nie zmieniać tego w ramach naprawy SHIFT-24-PAIR-01**. Obecny reproduktor i komunikat wystarczają do naprawienia potwierdzonego false-positive. Jeśli po evaluatorze nadal będzie realna potrzeba lepszej diagnostyki TECHNICAL_ERROR, otworzyć osobną decyzję OWNERA/Task.

## 9. Proces

To powinien być mały corrective Task produktu, nie kolejny projekt Symulatora.

`WHERE_MAP: REQUIRED`, bo zmieniamy ownera reguły HARD i współdzieloną semantykę pokrycia. Przed zamrożeniem Tasku należy objąć mapą co najmniej:

- `rota/planning/validator.py` — `_check_coverage`, `_check_24h_same_person`, ewentualny nowy shared helper;
- `rota/planning/constraints.py` — `add_same_person_24h_constraints` jako niezależny solver owner do potwierdzenia, nie domyślnej zmiany;
- testy/regresje T022-F2/F3 oraz T041 concurrent coverage.

Po kontrakcie: PRE_IMPLEMENTATION_REDUCTION_GATE, implementacja wąska, niezależny exact-SHA audit. Bez pełnej regresji repo, jeśli scope pozostanie lokalny i nie pojawi się nowy powód.

## 10. Odpowiedź na pytania z findingu

1. SHIFT-24-PAIR-01 **już jest** twardym ograniczeniem solvera i powinno nim pozostać; niezależny validator również powinien pozostać jako anti-drift check.
2. Generator B **nie potrzebuje** nowej reguły sensowności dla tego przypadku.
3. 67% nie jest reprezentatywną miarą produkcji; nie potrzeba jej do dowodu defektu.
4. Jeden mały Task produktu dotyczący validatora/atrybucji pokrycia. Bez Tasku Symulatora.
5. Diagnostyka odrzuconego kandydata przy TECHNICAL_ERROR — osobny temat, poza tym Taskiem.

---

**ARCHITECT VERDICT: CONFIRMED PRODUCT DEFECT — FIX VALIDATOR COVERAGE ATTRIBUTION, KEEP VARIANT B GENERATOR UNCHANGED.**

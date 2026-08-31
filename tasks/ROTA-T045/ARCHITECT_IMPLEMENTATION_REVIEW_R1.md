# ROTA-T045 — architect implementation review R1

Status: **PASS — IMPLEMENTATION ARCHITECTURALLY CLOSED — READY FOR OWNER MERGE DECISION**

Data: 2026-08-31
Branch: `task/T045-shift24-pair-01`
Audytowany exact implementation SHA: `4fec4ac398828c188587d835aaf0c7578d8174a2`
Kontrakt z niezależnym PASS: `7d9b4468f136068622900ce6fe69076cdf0cc139`
Niezależny audyt implementacji: `tasks/ROTA-T045/round_01/tests/tests_r3.txt` @ `d97df930b47acc899aadfda5027cf5ec848c12dd` — PASS na exact implementation SHA `4fec4ac398828c188587d835aaf0c7578d8174a2`.

## 1. Werdykt

**PASS — T045 realizuje zamrożony corrective contract bez poszerzenia produktu.**

Naprawa usuwa false-positive `SHIFT-24-PAIR-01` dla legalnego, niezależnego demandu nakładającego się na jedną połówkę H24, a jednocześnie zachowuje wcześniejsze zabezpieczenia T022-F2/F3 oraz semantykę `COVERAGE-01` zamrożoną przez T041.

Nie ma otwartej decyzji OWNERA wymaganej do poprawności tej implementacji. Nie wykonuję merge; decyzja o merge pozostaje po stronie OWNERA.

## 2. Scope — PASS

Diff kontrakt `7d9b446...` → implementacja `4fec4ac...` zmienia produkcyjnie wyłącznie:

- `rota/planning/validator.py`;

oraz dodaje dwa testy w:

- `tests/test_t022_planning_integrity.py`.

Nie zmieniono:

- `rota/planning/constraints.py`;
- `rota/planning/solver.py`;
- Symulatora Wariantu B;
- API / `PlanningResult` / diagnostyki `TECHNICAL_ERROR`;
- generatora katalogów.

To jest zgodne z `TASK_SCOPE` i z wcześniejszym werdyktem architekta: finding był defektem niezależnego validatora, nie solvera ani Symulatora.

## 3. Wspólny owner atrybucji pokrycia — PASS

Nowy `_attributed_overlap_intervals()` nie wprowadza nowej reguły. Jest mechanicznym wydzieleniem dokładnej logiki, która przed T045 żyła wewnątrz `_check_coverage()`:

1. wyznacza geometryczne przecięcie PRIMARY z badanym demandem;
2. jeżeli `covers_demand_id` wskazuje inny istniejący demand, który realnie konkuruje czasowo z badanym demandem, i Assignment rzeczywiście pokrywa swój tagowany demand, wycina wyłącznie konkurujący podprzedział;
3. niekonkurujące ogony/głowy spanning/manual Assignmentu pozostają geometrycznym pokryciem;
4. brak tagu, tag nieistniejący albo tag, którego Assignment realnie nie pokrywa, nie ukrywa rzeczywistego pokrycia.

`_check_coverage()` po refaktorze tylko wykonuje `overlapping.extend(_attributed_overlap_intervals(...))`; algorytm `coverage_segments()` i warunek dokładnej liczby PRIMARY nie zostały zmienione.

Architektonicznie jest to właściwy kierunek: jedno źródło prawdy dla pytania „jaki fragment tego PRIMARY należy do tego demandu?”, zamiast drugiego algorytmu dla H24.

## 4. `SHIFT-24-PAIR-01` — PASS

Przed T045 `_check_24h_same_person()` wkładał do `emp1` / `emp2` każdego PRIMARY z dowolnym overlapem czasowym. To powodowało false-positive, gdy E2 legalnie obsadzał inny demand nakładający się tylko na pierwszą połówkę H24.

Po T045 oba employee sets powstają wyłącznie z PRIMARY, dla których wspólny helper zwraca rzeczywiste, przypisane pokrycie danego komponentu H24.

Daje to prawidłowe rozróżnienie:

- E1 obsadzający obie połówki H24 pozostaje w obu zbiorach;
- E2 poprawnie tagowany do niezależnego concurrent demandu nie jest sztucznie doliczany do H24 na konkurującym podprzedziale;
- spanning/manual PRIMARY z brakiem/fałszywym/niekonkurującym tagiem nadal liczy się według realnej geometrii i nie może obejść T022-F2.

Nie zmieniono fail-closed cardinality/provenance przed porównaniem employee sets, więc T022-F3 pozostaje niezależną ochroną.

## 5. Macierz regresji — PASS na dostępnych niezależnych dowodach

Codex R3 na exact `4fec4ac...` niezależnie uruchomił siedem celowanych przypadków obejmujących wszystkie istotne klasy tego Tasku:

- nowy `LEGAL_OVERLAP_PASS`;
- nowy `MULTI_PRIMARY_H24`;
- prawdziwy mismatch dwóch połówek H24;
- T022-F2: wrong/false tag nie ukrywa realnego pokrycia;
- malformed H24 fail-closed;
- T041: legal concurrent demand disambiguation;
- T041/T022: spanning/manual PRIMARY przez sąsiednie demandy.

Wynik: `7 passed`.

Dodatkowo realny pion `run_full_scenario_b(... seed=0 ...)` przez produkcyjne API/backend i SQLite `:memory:` zakończył się `FEASIBLE`, bez poprzedniego fałszywego `TECHNICAL_ERROR`.

R3 wykonał również wymagany `WHERE_MAP` dla `_attributed_overlap_intervals`, `_check_coverage` i `_check_24h_same_person` i potwierdził jedną definicję helpera oraz użycie wyłącznie przez dwa zamierzone HARD checks w `validator.py`.

Uwaga dowodowa: R3 nie twierdzi, że ponownie uruchomił całe pliki retained-regression ani pełną suitę repo. Nie przypisuję mu takiego wyniku. Dla niezależnego audytu AGENTS.md wymaga pokrycia pełnej klasy błędu i realnego pionu, a jednocześnie mówi, by nie powtarzać mechanicznie wszystkich testów implementera; R3 pokrywa wszystkie klasy macierzy T045 i pion integracyjny. Nie ma reprodukowanego regresyjnego failure, który uzasadniałby FAIL przez DEFECT_GATE.

## 6. Dwie kluczowe ochrony zachowane

### T022-F2

Naprawa **nie ufa wyłącznie `covers_demand_id`**. Helper używa tagu tylko do rozdzielenia rzeczywiście konkurującego podprzedziału. Dlatego manual/spanning PRIMARY nadal może ujawnić realne pokrycie H24 mimo innego tagu.

### T041 / COVERAGE-01

Naprawa **nie wraca do czystej geometrii**. Legalny concurrent demand z prawdziwym tagiem nadal jest odseparowany na wspólnym podprzedziale, więc nie wraca false `COVERAGE-01 excess` z AUDIT-1 C-03.

To jest najważniejsza merytoryczna własność T045: obie pozornie przeciwne reguły pozostają prawdziwe jednocześnie dzięki jednemu wspólnemu ownerowi atrybucji.

## 7. Out of scope — zachowane

T045 nie rozwiązuje i nie powinno rozwiązywać:

- ujawniania odrzuconego kandydata przy `TECHNICAL_ERROR`;
- zmiany solvera;
- filtrowania legalnych overlapów w Symulatorze;
- nowej „sensowności” generatora;
- zmian publicznego API.

Brak diagnostyki odrzuconego kandydata pozostaje osobnym potencjalnym tematem OWNERA i nie blokuje tego validator fix.

## 8. Finalna ocena

Nie znalazłem konkretnej sprzeczności z PRODUCT_TRUTH, nie znalazłem regresji ownership ani ukrytego rozszerzenia produktu.

Kod na `4fec4ac398828c188587d835aaf0c7578d8174a2` jest zgodny z zamrożonym kontraktem T045 i wcześniejszym kierunkiem architektonicznym.

---

**ARCHITECT IMPLEMENTATION VERDICT: PASS — READY FOR OWNER MERGE DECISION.**

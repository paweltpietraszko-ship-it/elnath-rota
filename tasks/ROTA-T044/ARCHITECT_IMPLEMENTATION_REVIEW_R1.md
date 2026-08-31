# ROTA-T044 — architect implementation review R1

Status: **FAIL — IMPLEMENTATION NOT YET ARCHITECTURALLY CLOSED**

Data: 2026-08-31
Branch: `task/ROTA-T044`
Audytowany exact implementation SHA: `e80103d10e7d980a1d38b3572ecac25731a464b8`
Niezależny raport pomocniczy: `tasks/ROTA-T044/round_01/tests/tests_r12.txt` @ commit `1d9625685c2caff07e17e0513b0f5424110580d5` — PASS wyłącznie R11-01.

## 1. Zakres tej oceny

To nie jest powtórzenie `tests_r12.txt`. R12 sprawdzał tylko poprawkę przechwycenia wyjątku innego niż `AssertionError`.

Ta ocena sprawdza merytorycznie, czy dostarczony Wariant B robi to, co zamrożono w całym kontrakcie T044:

- `brief.md` R8;
- `TASK_CHATGPT.md`;
- `TASK_CHATGPT_CORRECTION_R1.md`;
- `TASK_CHATGPT_CORRECTION_R2.md`;
- `ARCHITECT_FINAL_PREIMPLEMENTATION_GATE.md`.

Nie zmieniam kodu produktu ani Symulatora.

## 2. Co jest zgodne z planem

### 2.1 Scope / ownership — PASS

Diff od finalnego preimplementation gate do `e80103d` pozostaje w dozwolonym zakresie:

- `tests/property/coordinator_simulator.py` — addytywny Wariant B;
- `tests/property/test_coordinator_simulator_variant_b.py`;
- `pyproject.toml` — `hypothesis`;
- artefakty T044.

Brak zmian `rota/**`, `api/**`, `frontend/src/**`, `benchmarks/**` i brak zmiany Wariantu A.

### 2.2 Kalkulator obsady — PASS

`layered_headcount_b()` implementuje zamrożone:

`max_m(sum_k(ceil(layer_hours(k,m) / norm(m))))`

czyli nie łączy maksimów z różnych miesięcy. Kontrolne oracle pozostają 5/10/9/4. Kalkulator używa tylko arytmetyki wejściowej i nie zna wyniku PLAN/REPLAN.

### 2.3 Generator — PASS

`random_atoms_b()` generuje swobodnie per `(kind, weekday)`:

- obecność/brak wpisu;
- różne godziny startu;
- różne długości, w tym 24h;
- `required_primary_count` w `{1,2}`;
- wielokrotne legalne wpisy/overlap.

Jedynym generator-side odrzuceniem pozostaje zero coverage.

### 2.4 Absencje — PASS

- urlop jest policzony jako dokładnie 10/5 realnych dni roboczych;
- `1 LOCAL` dostaje jeden blok 10 dni;
- `>=2 LOCAL` dostaje dokładnie dwa bloki 10+5 dla dwóch osób;
- L4 jest losowane raz na obiekt, ~25%, 5 dni kalendarzowych, LOCAL-only;
- `apply_absences_b()` jest wykonywane w initial setup przed PLAN;
- po PLAN state machine nie ma transition dopisującego/rozszerzającego absencję.

### 2.5 Prawdziwy backend / EXTERNAL — PASS

- każdy przykład ma świeżą SQLite `:memory:` i nowy Site;
- pierwszy PLAN używa LOCAL;
- EXTERNAL powstaje dopiero po realnym, niepustym `DECISION_REQUIRED`;
- create-person niesie decision id, membership/window przekazują `null`;
- pętla zachowuje pierwszy wynik i wszystkie retry;
- limit EXTERNAL = początkowy `employee_count`;
- nie ma reaktywnego dodawania LOCAL ani ręcznych Assignmentów.

### 2.6 HEADCOUNT / CLOSED WORLD — PASS

HEADCOUNT jest sprawdzany względem kanonicznego kalkulatora. CLOSED WORLD obejmuje wszystkie candidates w FEASIBLE oraz zachowane wyniki REPLAN, nie tylko `candidates[0]`.

### 2.7 R11-01 — PASS

Na `e80103d` setup/plan/select/replan/invariant przechwytują `Exception`, zapisują snapshot przez jeden `_write_and_reraise()` i ponownie zgłaszają pierwotny wyjątek. `tests_r12.txt` niezależnie potwierdza RuntimeError → failure JSON + re-raise.

## 3. ARCH-R1-01 — BLOCKER: normalne wyniki badania nie są trwale zapisywane

### TRACE

Wiążący kontrakt mówi jednocześnie:

1. `TASK_CHATGPT.md` OWNER-06: **każdy etap musi pozostać w raporcie**;
2. OWNER-07: surowe dane wyniku solvera **należy zapisać**, bez budowania własnego evaluatora;
3. OWNER-08: Wariant B **zapisuje maszynowo czytelny komplet danych potrzebny do późniejszej diagnozy**;
4. `brief.md` 1.6: Symulator ma zapisywać kompletne surowe dane w formacie, który późniejszy zewnętrzny evaluator będzie mógł skonsumować; raport JSON ma być kompletny i czytelny maszynowo.

To jest kluczowa granica produktu badawczego: Wariant B celowo NIE ocenia fairness/jakości grafiku, więc wartość badania zależy od zachowania surowych wyników do późniejszej diagnozy.

### IMPLEMENTACJA NA `e80103d`

Trwały JSON powstaje tylko przez:

- `_write_failure_json_b(...)`;
- wywołany z `_write_and_reraise(...)`;
- `_write_and_reraise()` jest osiągalny wyłącznie wtedy, gdy setup/plan/select/replan/invariant rzuci wyjątek.

`teardown()` tylko usuwa dependency override i zamyka połączenie.

Nie ma ścieżki zapisującej kompletny raport po zwykłym zakończeniu przykładu.

Dodatkowo `_KNOWN_PLAN_STATUSES` jawnie traktuje jako prawidłowe słownictwo m.in.:

- `FEASIBLE`;
- `DECISION_REQUIRED`;
- `TECHNICAL_ERROR`;
- `NO_ALTERNATIVE`;
- `NARROW_SEARCH_EXHAUSTED`;
- `SEARCH_INCOMPLETE`.

`do_plan()` jedynie sprawdza, czy status należy do tego zbioru. Status produktowy `TECHNICAL_ERROR`, końcowy `DECISION_REQUIRED` po wyczerpaniu EXTERNAL albo FEASIBLE z bardzo złym, ale formalnie dozwolonym rozkładem nie musi rzucić żadnego wyjątku. Przykład może więc zakończyć się zielonym pytest/Hypothesis, a jego stan znika po `teardown()`.

### SKUTEK

To łamie sens Wariantu B.

Przykład:

- Hypothesis generuje nowy obiekt;
- solver zwraca formalnie FEASIBLE, ale grafik wygląda podejrzanie i ma być później oceniony przez człowieka/zewnętrzny evaluator;
- Wariant B zgodnie z kontraktem nie może sam uznać go za FAIL;
- obecna implementacja nie zapisuje tego grafiku ani run id;
- po zakończeniu przykładu baza `:memory:` znika;
- nie ma czego później przeanalizować i nie wiadomo nawet, jaki seed odtworzyć.

Analogicznie `TECHNICAL_ERROR` może zostać zaakceptowany jako znany status i nie wygenerować failure artifactu.

To nie jest propozycja nowego evaluatora. To brak wymaganej telemetrii/artefaktu surowego badania.

### WYMAGANA KOREKTA

Bez zmiany produktu i bez rozszerzenia roli Symulatora dodać jeden wspólny, neutralny report path dla zakończonego przykładu/scenariusza.

Raport nie ma oceniać solvera. Ma wyłącznie utrwalić fakty.

Dla każdego realnie wykonanego przykładu, który doszedł do PLAN, powinien zachować co najmniej:

- run/seed potrzebny do odtworzenia;
- miesiąc, regime i wygenerowany katalog/atoms;
- wynik kalkulatora i zadeklarowany roster;
- targety i absencje;
- kolejność działań;
- pierwszy PLAN;
- wszystkie DECISION_REQUIRED i wszystkie reakcje EXTERNAL/retry;
- select, jeśli nastąpił;
- wszystkie REPLAN results;
- wszystkie zwrócone candidates/Assignmenty zawarte w tych wynikach;
- istotny readback/analitykę dostępną z produktu, bez własnego oracle;
- gotową komendę reprodukcji.

Failure path może dalej używać tego samego snapshotu i dalej re-raise'ować wyjątek.

Nie wymagam nowego endpointu, modelu produktu ani drugiego evaluatora. To ma pozostać w `tests/**` / `tasks/ROTA-T044/round_01/tests/**`.

### KLASYFIKACJA

**BLOCKER — T044 nie jest jeszcze gotowe do finalnego zamknięcia/merge.**

Nie wymaga decyzji OWNERA: obowiązek zapisu surowego raportu jest już zamrożony.

## 4. ARCH-R1-02 — NON_BLOCKING: REPLAN candidate nie ma ścieżki akceptacji w state machine

### FACT

Produkcja mówi wprost, że `replan()` tworzy WORKING child i **nigdy nie zapisuje automatycznie zwróconego kandydata**.

Wariant B:

- `do_select_candidate()` może wybrać wyłącznie `self.final_result` z pierwszego PLAN/EXTERNAL;
- `do_replan()` dopisuje PlanningResult do `self.replan_results`;
- kandydat FEASIBLE z REPLAN nie staje się źródłem kolejnego `select_candidate`;
- kolejne REPLAN-y mogą być wykonywane bez zaakceptowania poprzedniego kandydata.

### OCENA

To jest realna luka pokrycia zachowania koordynatora, ale **nie blokuję T044 tym punktem**, bo frozen Task wymaga `select candidate / REPLAN` przy poprawnych preconditions, lecz nie mówi jednoznacznie, że każdy FEASIBLE REPLAN musi być następnie zaakceptowany.

Proste wyjaśnienie dla OWNERA:

> Po pierwszym PLAN Symulator umie zatwierdzić grafik. Gdy później naciska REPLAN i program pokazuje nowy grafik, Symulator tego nowego grafiku nigdy nie zatwierdza — tylko zapisuje odpowiedź i może nacisnąć REPLAN ponownie.

Jeśli celem przyszłego rozszerzenia jest badanie pełnej ścieżki „REPLAN → wybieram nowy grafik → dalej pracuję”, należy otworzyć osobny mały kontrakt albo jawnie rozszerzyć T044. Nie dokładam tego teraz po cichu.

## 5. TECHNICAL_ONLY — `observe` może zużywać kroki przed PLAN

`observe()` jest zawsze dostępne, także przed `do_plan()`. To było dodane, aby Hypothesis nie zgłaszał `InvalidDefinition` po terminalnym wyniku produktu, i samo nie zmienia stanu.

Skutek uboczny: część kroków może zostać zużyta na no-op zanim nastąpi PLAN. Przy małym profilu `8 × 4` obniża to efektywną liczbę realnych działań.

Nie jest to blocker kontraktu i nie wymaga decyzji OWNERA. Technicznie można kiedyś zawęzić precondition `observe` do stanów terminalnych, jeśli daje to lepsze wykorzystanie profilu bez zmiany semantyki.

## 6. Relacja do `tests_r12.txt`

Nie podważam PASS R12 w jego deklarowanym zakresie.

`tests_r12.txt` poprawnie potwierdza tylko R11-01:

- RuntimeError zapisuje failure JSON;
- stage/seed są właściwe;
- pierwotny wyjątek dalej propaguje.

R12 sam mówi, że jego zakres to **wyłącznie poprawka R11-01** i że nie otwiera ponownie wcześniejszych obszarów. Dlatego jego PASS nie dowodzi kompletności merytorycznej całego Wariantu B.

## 7. Następny gate

1. CC poprawia wyłącznie `ARCH-R1-01` w TASK_SCOPE, bez evaluatora i bez zmian produktu.
2. Doda celowany test pokazujący, że zwykły zakończony przebieg (nie wyjątek) zapisuje kompletny raw report.
3. Obowiązkowy przypadek graniczny: wynik `TECHNICAL_ERROR` jako normalny PlanningResult ma zostać utrwalony, ale nie zamieniony przez harness na własny błąd/fairness verdict.
4. Drugi przypadek: FEASIBLE z candidates ma zostać utrwalony wraz z Assignmentami, bez oceny jakości.
5. Po poprawce niezależny audyt exact SHA.
6. `ARCH-R1-02` pozostaje osobną, nieblokującą decyzją o przyszłym pokryciu; nie mieszać jej do poprawki blockera bez jawnej decyzji OWNERA.

---

**ARCHITECT IMPLEMENTATION VERDICT: FAIL — ONE BLOCKER (`ARCH-R1-01`).**

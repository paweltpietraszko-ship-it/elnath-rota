# ROTA-T032 — SOFT ranking, max 2 N pod rząd i budżet optymalizacji

Status: **READY FOR CODEX PREIMPLEMENTATION RE-AUDIT — CC READ-ONLY UNTIL PASS**

ARCHITECT_INPUT_SHA: `7d61f19831940f5cf5045e4a4d55a87e362dab57`
BASE_MAIN_SHA: `3be4ed37e735766a80ca2259c7d1b6981d22dbb5`
R1_AUDIT: `tasks/ROTA-T032/round_01/tests/tests_r1.txt`
R2_AUDIT: `tasks/ROTA-T032/round_01/tests/tests_r2.txt`
R3_AUDIT: `tasks/ROTA-T032/round_01/tests/tests_r3.txt`
OWNER_CORRECTED: 2026-08-25

T032 domyka:

1. równomierność godzin względem istniejącego effective targetu;
2. preferencję rytmu D → N → wolne → wolne;
3. absolutny HARD: **ten sam pracownik nie może mieć więcej niż dwóch kolejnych N**;
4. jedną publiczną granicę czasu planowania: **180 sekund na całą operację**;
5. działający seam dalszego szukania po nieukończonej optymalizacji, bez job queue i bez trwałej sesji solvera.

R3 dodatkowo zamraża dwie pionowe granice: przyszły request PLAN/REPLAN nie może zostać ucięty przez obecny globalny 20-sekundowy timeout frontendu, a akcja dalszego szukania nie może uruchamiać identycznego deterministycznego solve od zera bez poprzedniego kandydata.

Nie powstaje procentowy progress liczony z sufitu, nowy status planowania, persistence solvera ani background worker.

---

## 1. WYNIK PRODUKTOWY

Po istniejących silniejszych fazach REPLAN-MIN i — gdy aktywna — exceptional-N:

1. każdy automatyczny kandydat musi spełniać wszystkie dotychczasowe HARD oraz `NIGHT-STREAK-01`;
2. solver w pozostałym budżecie optymalizuje istniejący TARGET-01 i dalsze SOFT;
3. przy tej samej jakości targetu preferuje bardziej wyrównaną relację `actual_hours / effective_target`;
4. w finalnym SOFT rankingu preferuje więcej okien D → N → wolne → wolne, obok istniejących weekend/holiday/DAY_SHIFT_OFF/LEAVE_PLAN terms.

`NIGHT-STREAK-01` jest HARD. Nie jest score, warningiem ani fairness termem.

**Owner rule:** nie może być trzeciej kolejnej nocki tego samego pracownika. Koniec.

Brak rozwiązania przez ten HARD trafia do istniejącej ścieżki `DECISION_REQUIRED`, nie do częściowego FEASIBLE ani do `TECHNICAL_ERROR`.

Po 24h służbie T032 nie dodaje osobnej logiki nocnej. Istniejący HARD odpoczynku po 24h już wymusza 24h wolnego i uniemożliwia N następnego dnia; drugi owner tej samej ochrony jest zakazany.

---

## 2. OWNERZY I JEDNO ŹRÓDŁO PRAWDY

Pozostają:

- `rota/planning/solver.py` — CP-SAT, fazy, objective i remaining budget;
- `rota/planning/constraints.py` — CP-SAT HARD;
- `rota/planning/validator.py` — niezależny mirror HARD (anti-drift rule 12);
- `rota/planning/fairness.py` — helpery SOFT;
- `_effective_targets(state)` — canonical `max(0, target_hours - absence_hours)`;
- istniejący expression godzin TARGET-01 — canonical actual hours;
- `rota/planning.shift_catalog.classify_demand` — jedyny owner klasyfikacji D/N;
- `rota/application/plan_ops.py` — publiczne PLAN/REPLAN oraz nowy nietrwały seam dalszego szukania na tym samym WORKING version.

T032 nie tworzy drugiej definicji godzin, D/N, absencji, odpoczynku ani targetu.

---

## 3. HARD `NIGHT-STREAK-01` — MAKSYMALNIE DWIE KOLEJNE N

### 3.1 Semantyka

Dla jednego pracownika nie może istnieć żadna trójka kolejnych **dat startu** `(d, d+1, d+2)`, na których finalny target-Site grafik zawiera PRIMARY N tego pracownika na każdej z trzech dat.

- N / N — legalne;
- N / N / N — niedozwolone;
- N / wolne / N — legalne dla tej reguły;
- D nie liczy się jako N;
- TRAINEE i CANCELLED nie tworzą N.

N klasyfikować wyłącznie `classify_demand`.

### 3.2 Fakty widziane przez regułę

Reguła widzi:

- nowo wybierane PRIMARY (`x`);
- non-CANCELLED fixed existing target-Site PRIMARY pozostające w solve/replan;
- target-Site `boundary_assignments` z jednoznacznie matching `boundary_shift_demands`.

Nie widzi:

- `other_site_assignments`;
- TRAINEE jako N;
- redistributable baseline drugi raz.

Fixed/boundary Assignment bez matching demand nie jest zgadywany jako D/N.

### 3.3 Granica miesiąca

Max-2-N obowiązuje również przez granicę miesiąca/roku, jeśli sąsiedni target-Site fakt istnieje w canonical boundary state.

Zakazane przy planowaniu października:

- 30.09 — persisted target-Site PRIMARY N;
- 01.10 — N;
- 02.10 — N.

Bez nowego history store/DTO. Użyć istniejących boundary facts.

### 3.4 Solver / constraints

Dodać jeden CP-SAT HARD owner, np. `add_max_two_consecutive_night_constraints(...)`, w `constraints.py` i podpiąć w `solver.py`.

Zakazane: `night_streak_excess_count`, NIGHT_STREAK weight, soft phase albo override tej reguły.

Jeżeli HARD uczestniczy w niewykonalności, diagnoza ma zachować raw code `NIGHT-STREAK-01` i istniejącą ścieżkę `DECISION_REQUIRED`; nie nazywać go automatycznie `REST-01`.

### 3.5 Validator

Validator niezależnie, od zera, na finalnej liście Assignmentów + canonical boundary facts powtarza tę samą semantykę.

Violation code: `NIGHT-STREAK-01`.

Nie importuje solverowego helpera CP-SAT.

### 3.6 Coordinator-facing diagnosis

`DecisionRequiredPayload` pozostaje jedynym DTO.

W `decision_guidance.py` tylko tłumaczenie:

`NIGHT-STREAK-01` → `Koliduje z limitem dwóch nocek pod rząd`.

Brak opcji akceptacji/wyłączenia HARD.

---

## 4. CHECKPOINT A — TARGET EQUITY

### 4.1 Jeden expression godzin

Dla każdego pracownika z istniejącego `target_by_employee`:

- `effective_target` = `_effective_targets(state)`;
- `actual_hours` = ten sam expression, którego TARGET-01 już używa;
- absencja i hours scope nie są przeliczane drugi raz.

Solver wyprowadza actual hours i absolutne odchylenie raz i reuse je przez TARGET-01 oraz equity.

### 4.2 Metryka

Dla `effective_target > 0`:

`completion_pct = floor(100 * actual_hours / effective_target)`.

Bez capu na 100.

Dla co najmniej dwóch dodatnich effective targetów:

`target_equity_spread = max(completion_pct) - min(completion_pct)`.

Mniejszy spread jest lepszy.

`effective_target == 0` wyłącza pracownika tylko z ratio; TARGET-01 nadal liczy `|actual_hours - 0|`.

### 4.3 TARGET-01 przed equity

Equity nie może świadomie kupić gorszej łącznej wartości TARGET-01.

Po ukończeniu istniejących silniejszych faz solver dąży do minimum `total_target_deviation`; jeśli udowodni je w budżecie, blokuje optimum przed finalną objective.

Jeżeli budżet kończy się już na etapie jakości (TARGET-01/final SOFT), HARD-poprawny incumbent może wrócić jako `FEASIBLE + optimization_complete=False`; nie wolno wtedy twierdzić, że target optimum zostało udowodnione.

### 4.4 Finalny term

`TARGET_EQUITY_WEIGHT = 1` w `fairness.py`.

`TARGET_DEVIATION_WEIGHT = 100` bez zmiany.

`add_target_equity_fairness(...)` dostaje już wyprowadzone `actual_hours` i effective targets. Nie czyta persistence ani nie liczy absencji.

---

## 5. CHECKPOINT B — REWARD D → N → WOLNE → WOLNE

Reward jest SOFT i niezależny od HARD max-2-N.

`DN_RHYTHM_REWARD_WEIGHT = 1`.

Każde pełne trafienie obniża finalną objective o 1.

### 5.1 Okno

Tylko cztery kolejne daty startu `(d, d+1, d+2, d+3)` całkowicie wewnątrz `state.month`.

Cross-month dotyczy HARD N-streak, nie rewardu rytmu.

### 5.2 Trafienie

`pattern_match(employee, d) = 1` tylko gdy:

1. w `d` startuje dokładnie jeden non-CANCELLED Assignment i jest PRIMARY D;
2. w `d+1` startuje dokładnie jeden non-CANCELLED Assignment i jest PRIMARY N;
3. w `d+2` nie startuje żaden non-CANCELLED Assignment tego pracownika;
4. w `d+3` nie startuje żaden non-CANCELLED Assignment tego pracownika.

N kończąca się rano w `d+2` nie psuje wzorca; „wolne” oznacza tu brak nowego startu. Odpoczynek godzinowy pozostaje własnością REST/WEEKLY-REST.

Fixed target-Site facts uczestniczą; redistributable baseline nie jest liczony drugi raz; other-Site nie uczestniczy.

---

## 6. EQUITY — WYMAGANY DOWÓD PIONOWY

Live `192 / 180 / 180 / 120 / 48` przy targetach `160` pozostaje sygnałem produktu, nie oracle przyczyny.

T032 dowodzi:

1. kontrolowany tie TARGET-01 → mniejszy completion spread wygrywa;
2. realny `solve()` na małym stanie: ≥4 osoby, równe dodatnie effective targety, pula 12h demandów poniżej sumy targetów, HARD pozwala idealnie równo rozdzielić zmiany → pierwszy FEASIBLE kandydat ma `max(actual_hours)-min(actual_hours) == 0`.

Jeśli fixture sam tworzy HARD przeszkadzający równości, fixture jest błędny.

---

## 7. OWNER TIME BUDGET — 180 S NA CAŁĄ OPERACJĘ

### 7.1 Jeden deadline

Jedna publiczna operacja `plan(state)` ma:

`PLANNING_OPERATION_BUDGET_SECONDS = 180`.

Deadline powstaje raz z monotonicznego zegara. Każdy wewnętrzny solve/fallback/faza/search alternatyw dostaje tylko pozostały czas do tego samego deadline. Nie resetować 180 s per faza.

Testy używają fake clock/małego test budgetu; nie śpią 180 s.

### 7.2 R3-3 — które fazy wolno zakończyć partial FEASIBLE

**Partial FEASIBLE NIE rozluźnia istniejących silniejszych faz REPLAN-MIN ani exceptional-N.**

Jeżeli deadline kończy się zanim któraś z tych pre-existing phases udowodni swoje wymagane `OPTIMAL`, zachowuje się ich dotychczasowy fail-closed contract: publicznie brak kandydata / `TECHNICAL_ERROR + optimization_complete=False`.

Dopiero po udowodnieniu wszystkich aktywnych pre-existing stronger phases można zastosować timeout fallback z §7.3 do faz jakości: TARGET-01, equity, rhythm, weekend/holiday i pozostałej finalnej objective.

To zachowuje wcześniejsze frozen gwarancje zamiast po cichu dopuszczać większy reshuffle albo nieudowodnione użycie exceptional-N.

### 7.3 Wynik po wyczerpaniu budżetu

A. Po ukończeniu silniejszych faz, jeśli istnieje pełny HARD-poprawny incumbent:

- status `FEASIBLE`;
- independent validator musi PASS;
- `optimization_complete=False`;
- nie nazywać nieudowodnionego SOFT optimum błędem technicznym.

B. Wszystkie wymagane fazy/objective udowodnione w budżecie:

- zwykły wynik;
- `optimization_complete=True`.

C. Brak kandydata i brak proof `DECISION_REQUIRED` do deadline:

- brak wymyślonego FEASIBLE;
- `TECHNICAL_ERROR` może pozostać publiczną klasą nierozstrzygnięcia;
- `optimization_complete=False`;
- czytelny komunikat o upływie 3 minut i możliwości ponowienia.

D. `DECISION_REQUIRED` udowodniony przed deadline jest kompletnym normalnym wynikiem.

### 7.4 DTO

Do `PlanningResult` na końcu:

`optimization_complete: bool = True`.

Bez nowego statusu `PARTIAL`, job ID ani persisted solver session.

---

## 8. DZIAŁAJĄCY SEAM „SZUKAJ DALEJ”

### 8.1 Publiczna operacja application-layer

Dodać w `rota/application/plan_ops.py` cienką operację, nazwa przykładowa:

`continue_plan_search(conn, *, site_id: str, month: date, coordinator_id: str, incumbent_candidate: list[Assignment]) -> PlanningResult`

Kontrakt:

1. wymaga aktywnego kontekstu i istniejącego CURRENT `WORKING` ScheduleVersion;
2. **nie tworzy nowego ScheduleVersion ani kolejnego REPLAN child**;
3. składa fresh canonical PlanningState dla tego samego CURRENT WORKING version;
4. niezależnie waliduje `incumbent_candidate` względem tego fresh state; invalid/stale incumbent = request rejected, nie hint;
5. przekazuje incumbent nietrwale do engine/solver;
6. niczego nie zapisuje, dopóki koordynator później nie użyje zwykłego `select_candidate`.

Dla pierwszego PLAN retry pracuje na już utworzonym current WORKING version. Dla REPLAN retry pracuje na tym samym child, który utworzył pierwszy `replan()`; **nie wolno ponownie wywołać `replan()` tylko po to, żeby szukać dalej**.

### 8.2 Incumbent jest obowiązkowy i zmienia przebieg

Retry bez incumbent jest niedozwolony.

Solver mapuje mutable PRIMARY część incumbent na istniejące `x` i:

- używa pełnej sygnatury incumbent jako obowiązkowego CP-SAT solution hintu;
- dodaje no-good/diversity cut wykluczający dokładnie tę samą mutable PRIMARY signature z nowego wyniku.

Dzięki temu identyczny `PlanningState + seed=0` nie uruchamia po prostu tego samego przebiegu kończącego się tym samym kandydatem.

Fixed facts nie są częścią diversity cut jako „wybór”, bo nie mogą się zmienić.

Każdy nowy kandydat ponownie przechodzi independent validator.

### 8.3 Uczciwa semantyka „lepszy”

T032 **nie dodaje drugiego post-hoc kalkulatora pełnego canonical objective** tylko po to, aby porównywać dwa zakończone grafiki.

Dlatego UI nie może twierdzić, że drugi znaleziony grafik jest matematycznie lepszy, jeżeli backend tego nie udowodnił.

Owner-facing flow:

- pytanie po timeout pozostaje: **„Znaleziono poprawny grafik. Szukać lepszej konfiguracji?”**;
- akcja wykonawcza na przycisku nazywa się **„Szukaj dalej”**;
- podczas retry poprzedni kandydat pozostaje widoczny/dostępny jako fallback;
- jeśli backend znajdzie inny HARD-poprawny kandydat, UI pokazuje oba (`Dotychczasowy` / `Nowy znaleziony`) i nie opisuje nowego jako „lepszy” bez dowodu;
- koordynator może wybrać dowolny przez istniejący `select_candidate` albo ponowić `Szukaj dalej` z wybranym bieżącym incumbentem.

Jeżeli po no-good cut nie ma innego rozwiązania w budżecie, poprzedni incumbent pozostaje dostępny. Nie wolno go usuwać ani automatycznie zapisywać.

Brak persistence solvera i brak zachowania obiektu `CpSolver` między requestami.

---

## 9. OBOWIĄZKOWY UX + TIMEOUT TRANSPORTOWY — POLECENIE DLA CC

To binding OWNER UX requirement.

### 9.1 Loader

Podczas trwającego PLAN/REPLAN/`continue_plan_search` koordynator widzi:

- spinner **lub** indeterminate progress bar;
- tekst np. `Układam grafik — to może potrwać do 3 minut`;
- zablokowanie podwójnego uruchomienia;
- brak fałszywego procentu postępu.

Ekran nie może wyglądać jak zawieszony.

### 9.2 R3-1 — planning request nie używa globalnego 20 s timeoutu

Obecne `frontend/src/api/client.ts` abortuje każdy `req()` przez globalne `REQUEST_TIMEOUT_MS = 20000`. To jest za krótko dla zaakceptowanego budżetu 180 s.

Gdy powstaje docelowy seam PLAN/REPLAN/search dalej:

- `req()` ma obsługiwać **per-request timeout override**;
- zwykłe krótkie endpointy nadal używają istniejącego 20 s defaultu;
- wyłącznie PLAN/REPLAN/`continue_plan_search` używają `PLANNING_REQUEST_TIMEOUT_MS = 195000` (180 s budżetu backendu + 15 s marginesu transportu/serializacji);
- frontend nie może abortować requestu przed 180 s backend deadline;
- loader trwa do faktycznej odpowiedzi/abortu, nie do lokalnego timera 20 s.

Nie podnosić globalnego timeoutu wszystkich endpointów.

### 9.3 Po odpowiedzi

`FEASIBLE + optimization_complete=False`:

- pokaż znaleziony grafik;
- pytanie z §8.3;
- `Użyj tego grafiku` oraz `Szukaj dalej`.

`optimization_complete=True`:

- brak automatycznego pytania o dalsze szukanie.

`TECHNICAL_ERROR + optimization_complete=False` bez kandydata:

- czytelny komunikat o wyczerpaniu budżetu;
- możliwość ponowienia;
- bez stack trace.

### 9.4 Granica branchu

Na bazie T032 nadal nie ma kompletnego docelowego ekranu Planowanie miesiąca ani routera PLAN/REPLAN. T032 nie tworzy sztucznego UI/API scaffoldu.

Ale contract dla późniejszego seam jest binding: ekran/API nie przejdą owner review bez per-request 195 s timeoutu, loadera i flow `Szukaj dalej`.

Backend T032 implementuje już `optimization_complete` i application seam `continue_plan_search`; późniejszy router ma je tylko przenieść 1:1.

---

## 10. T028 QUALITY GATE

T028 pozostaje osobnym taskiem/branchem.

Companion correction T028 ma traktować każdy FEASIBLE kandydat z >2 kolejnymi PRIMARY N jako `QUALITY_FAIL` poligonu. Po OWNER_CORRECTED jest to niezależny bezpiecznik regresji; produkcyjny solver/validator powinny już taki wynik uniemożliwić.

T028 nie implementuje reguły.

---

## 11. SCOPE

### Production dozwolone

- `rota/planning/constraints.py` — `NIGHT-STREAK-01`;
- `rota/planning/solver.py` — wiring HARD, objective, deadline, incumbent hint/no-good retry;
- `rota/planning/validator.py` — mirror HARD;
- `rota/planning/fairness.py` — equity + D/N rhythm;
- `rota/planning/engine.py` — operation budget, timeout disposition, incumbent retry seam;
- `rota/planning/engine_types.py` — tylko `PlanningResult.optimization_complete`;
- `rota/planning/decision_guidance.py` — tylko label `NIGHT-STREAK-01`;
- `rota/application/plan_ops.py` — `optimization_complete` pass-through + `continue_plan_search` bez nowej wersji/persistence solvera.

### Tests

- `tests/test_t032_soft_ranking.py`;
- opcjonalnie `tests/test_t032_night_streak.py`;
- istniejące regressions ownerów bez zmian.

### Nie implementować na tym branchu

- nowego ekranu Planowanie/routera, którego baza jeszcze nie ma;
- frontend scaffoldu tylko dla testu T032;
- persistence/job queue/background worker;
- procentowego progressu;
- nowego PlanningStatus;
- cross-Site night streak;
- cross-month rhythm reward;
- zmian REST/WEEKLY/LOAD;
- specjalnej logiki NIGHT-STREAK dla 24h;
- nowego modelu absencji/targetu;
- sztywnej brygady;
- nowego manual override HARD.

---

## 12. MINIMALNA MACIERZ ODBIORU

### NIGHT-STREAK-01

T32-N1 — N/N legalne; N/N/N niedozwolone.

T32-N2 — persisted N poprzedniego miesiąca + N/N bieżącego zablokowane.

T32-N3 — D/N/N i N/wolne/N nie są trójką N.

T32-N4 — fixed current-Site PRIMARY uczestniczy; redistributable baseline bez double count.

T32-N5 — TRAINEE/CANCELLED nie tworzą N; other-Site nie uczestniczy.

T32-N6 — validator odrzuca wstrzyknięty N/N/N także przez boundary kodem `NIGHT-STREAK-01`.

T32-N7 — solve blokowany przez tę regułę trafia do `DECISION_REQUIRED`, nie udaje REST-01.

T32-N8 — istniejący 24h rest sam uniemożliwia 24h → N następnego dnia; brak drugiego NIGHT-STREAK special-case.

### TARGET EQUITY

T32-A1 — tie TARGET-01: mniejszy completion spread wygrywa.

T32-A2 — różne targety: proporcjonalność > równe surowe godziny przy tej samej wcześniejszej jakości.

T32-A3 — effective target po absence_hours.

T32-A4 — target=0 bez dzielenia/model invalid; TARGET-01 nadal działa.

T32-A5 — surplus >100% niecapowany.

T32-A6 — real solve ≥4 równych targetów, równomiernie rozdzielalny shortage → równe actual hours.

### D/N RHYTHM

T32-B1 — więcej D→N→wolne→wolne trafień wygrywa przy równej wcześniejszej jakości.

T32-B2 — suma wielu trafień/wielu pracowników, bez wspólnej fazy.

T32-B3 — N kończąca się rano dnia wolnego nie niszczy start-day rhythm.

T32-B4 — fixed target-Site facts uczestniczą; TRAINEE może zająć wolny dzień, ale nie spełnia D/N.

T32-B5 — reward nie przechodzi przez granicę miesiąca.

### BUDŻET

T32-T1 — jeden fake 180 s deadline współdzielony przez wszystkie solve; brak resetu per faza.

T32-T2 — timeout podczas REPLAN-MIN lub exceptional-N zachowuje fail-closed: brak partial FEASIBLE.

T32-T3 — timeout dopiero po ukończeniu stronger phases + HARD-valid incumbent → `FEASIBLE`, `optimization_complete=False`, validator PASS.

T32-T4 — pełne udowodnienie → `optimization_complete=True`.

T32-T5 — timeout bez kandydata/proof decision → `TECHNICAL_ERROR`, `optimization_complete=False`, czytelny message.

T32-T6 — normalny udowodniony `DECISION_REQUIRED` nie jest maskowany timeoutem.

T32-T7 — default `optimization_complete=True` zachowuje stare konstruktory/testy.

### CONTINUE SEARCH

T32-C1 — `continue_plan_search` używa tego samego CURRENT WORKING version; nie tworzy nowego ScheduleVersion/REPLAN child.

T32-C2 — incumbent jest obowiązkowy, fresh-validator PASS wymagany przed użyciem jako hint.

T32-C3 — retry mapuje incumbent do x, daje solution hint i no-good cut wykluczający dokładną mutable signature; identyczny deterministic solve nie może po prostu zwrócić tej samej signature.

T32-C4 — fixed facts nie są traktowane jako zmienny diversity choice; każdy nowy kandydat validator PASS.

T32-C5 — poprzedni incumbent nie jest persystowany/usuwany przez retry i pozostaje możliwy do późniejszego `select_candidate`.

T32-C6 — bez działającego canonical post-hoc comparatora flow używa label `Szukaj dalej`; UI nie twierdzi, że nowy kandydat jest lepszy i zachowuje oba.

### FUTURE UI/API SEAM CONTRACT

T32-U1 — planujące requesty używają per-request 195000 ms timeoutu, zwykłe endpointy pozostają przy 20000 ms.

T32-U2 — loader/spinner jest widoczny przez cały request; brak wymyślonego %.

T32-U3 — partial FEASIBLE pokazuje incumbent + pytanie i `Szukaj dalej`; retry zachowuje poprzedni wynik.

Te trzy są contract tests dla późniejszego ekranu/routera, nie powodem tworzenia nieistniejącego frontendu na T032.

### Regresja

T32-R1 — REST/WEEKLY/LOAD/coverage/eligibility zielone.

T32-R2 — weekend/holiday fairness, DAY_SHIFT_OFF, LEAVE_PLAN, REPLAN-MIN i exceptional-N zachowują swoje role.

T32-R3 — żaden timeout/retry nie omija independent validator przed publicznym FEASIBLE.

---

## 13. PREIMPLEMENTATION RE-AUDIT

Independent Codex audituje exact corrected HEAD wyłącznie pod konsekwencje R3 i regresje wprowadzone korektą.

Required checks:

1. Czy R3-1 jest zamknięty per-request timeoutem 195 s bez zmiany globalnego 20 s defaultu?
2. Czy R3-2 ma realny application seam na tym samym WORKING version, mandatory incumbent, hint + no-good cut i bez kolejnego REPLAN child?
3. Czy UI contract uczciwie używa `Szukaj dalej` i zachowuje oba wyniki, skoro T032 nie dodaje canonical post-hoc comparatora?
4. Czy R3-3 jednoznacznie zachowuje fail-closed REPLAN-MIN/exceptional-N, a partial FEASIBLE dotyczy dopiero późniejszej optymalizacji jakości?
5. Czy NIGHT-STREAK pozostaje literalnym HARD z boundary i bez specjalnej logiki 24h?
6. Czy equity/rhythm nie tworzą drugiego ownera hours/D-N?
7. Czy 180 s nadal jest jednym backend deadline i wszystkie partial candidates przechodzą validator?
8. Czy scope nie tworzy job queue, persistence solvera, fake progress ani nieistniejącego ekranu?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` z numerowanymi pozostałymi defektami kontraktu.

Do PASS: **CC READ-ONLY / NOT READY FOR IMPLEMENTATION**.

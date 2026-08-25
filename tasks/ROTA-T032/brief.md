# ROTA-T032 — SOFT ranking, max 2 N pod rząd i budżet optymalizacji

Status: **READY FOR CODEX PREIMPLEMENTATION RE-AUDIT — CC READ-ONLY UNTIL PASS**

ARCHITECT_INPUT_SHA: `7d61f19831940f5cf5045e4a4d55a87e362dab57`
BASE_MAIN_SHA: `3be4ed37e735766a80ca2259c7d1b6981d22dbb5`
R1_AUDIT: `tasks/ROTA-T032/round_01/tests/tests_r1.txt`
R2_AUDIT: `tasks/ROTA-T032/round_01/tests/tests_r2.txt`
OWNER_CORRECTED: 2026-08-25

T032 domyka trzy rzeczy ujawnione przez live testing planowania OCHRONA:

1. równomierność godzin względem istniejącego effective targetu;
2. preferencję rytmu D → N → wolne → wolne;
3. absolutny limit właściciela: **ten sam pracownik nie może mieć więcej niż dwóch kolejnych N**.

R2 dodatkowo zamraża zachowanie czasu: jedna operacja PLAN/REPLAN dostaje **3 minuty** na szukanie/ulepszanie rozwiązania. Po wyczerpaniu budżetu poprawny HARD kandydat ma pierwszeństwo przed udowadnianiem idealnego SOFT optimum.

Nie zmienia to UI produktu poza obowiązkową informacją o trwającej pracy i pytaniem, czy po 3 minutach szukać lepszego układu. Nie powstaje system zadań w tle, procentowy progress liczony z sufitu ani trwała sesja solvera.

---

## 1. WYNIK PRODUKTOWY

Po istniejących silniejszych fazach REPLAN-MIN i — gdy aktywna — exceptional-N:

1. każdy automatyczny kandydat musi spełniać wszystkie dotychczasowe HARD oraz nowy `NIGHT-STREAK-01`;
2. solver w dostępnym czasie dąży do minimalnej osiągalnej łącznej wartości istniejącego TARGET-01 `sum(|actual_hours - effective_target|)`;
3. przy tej samej jakości TARGET-01 preferuje bardziej wyrównaną relację `actual_hours / effective_target`;
4. w finalnym SOFT rankingu preferuje więcej okien D → N → wolne → wolne, obok istniejących weekend/holiday/DAY_SHIFT_OFF/LEAVE_PLAN terms.

`NIGHT-STREAK-01` jest HARD. To nie jest score, warning ani fairness term.

**Owner rule:** nie może być trzeciej kolejnej nocki tego samego pracownika. Koniec. Solver nie może zwrócić takiego kandydata jako FEASIBLE tylko dlatego, że poprawiałby target, weekendy, święta albo inny SOFT.

Brak rozwiązania przez `NIGHT-STREAK-01` jest normalną granicą autonomii i ma trafić do istniejącej ścieżki `DECISION_REQUIRED`, nie do częściowego FEASIBLE ani do `TECHNICAL_ERROR`.

---

## 2. OWNERZY I JEDNO ŹRÓDŁO PRAWDY

Pozostają bez zmian:

- `rota/planning/solver.py` — składa CP-SAT, fazy i objective;
- `rota/planning/constraints.py` — owner ograniczeń CP-SAT;
- `rota/planning/validator.py` — niezależny owner ponownego wyprowadzenia HARD (anti-drift rule 12);
- `rota/planning/fairness.py` — helpery jakości/fairness SOFT;
- `_effective_targets(state)` — canonical effective target `max(0, target_hours - absence_hours)`;
- istniejący expression godzin TARGET-01 — nowo wybierane PRIMARY + te same target-Site fixed PRIMARY;
- `rota/planning/shift_catalog.classify_demand` — jedyny owner klasyfikacji D/N.

T032 nie tworzy drugiej definicji godzin, D/N, absencji, odpoczynku ani targetu.

---

## 3. HARD `NIGHT-STREAK-01` — MAKSYMALNIE DWIE KOLEJNE N

### 3.1 Semantyka

Dla jednego pracownika nie może istnieć żadna trójka kolejnych **dat startu** `(d, d+1, d+2)`, na których finalny target-Site grafik zawiera PRIMARY N tego pracownika na każdej z trzech dat.

Czyli:

- N / N — legalne;
- N / N / N — niedozwolone;
- N / N / N / N — niedozwolone;
- N / wolne / N — legalne z punktu widzenia tej jednej reguły;
- D nie liczy się jako N;
- TRAINEE nie tworzy N dla `NIGHT-STREAK-01`;
- CANCELLED nie tworzy N.

Każdą N klasyfikować produkcyjnym `classify_demand`; nie rozpoznawać N po godzinie startu ani po długości Assignmentu.

### 3.2 Finalny target-Site kandydat

Reguła widzi:

- nowo wybierane PRIMARY (`x`);
- non-CANCELLED fixed existing target-Site PRIMARY pozostające w bieżącym solve/replan;
- target-Site `boundary_assignments` z jednoznacznie matching `boundary_shift_demands`, jeżeli są już znanym persisted faktem.

Nie widzi:

- `other_site_assignments`;
- TRAINEE jako N;
- redistributable baseline drugi raz.

Fixed/boundary Assignment bez matching demand może zajmować czas dla innych istniejących reguł, ale nie wolno zgadywać z niego D/N.

### 3.3 Granica miesiąca

Limit dwóch N obowiązuje również przez granicę miesiąca/roku, o ile potrzebny sąsiedni target-Site fakt już istnieje w canonical boundary state.

Przykład zakazany przy planowaniu października:

- 30.09 — persisted target-Site PRIMARY N;
- 01.10 — N;
- 02.10 — N.

Nie dodawać nowego history store ani cross-month DTO. Użyć istniejących `boundary_assignments` / `boundary_shift_demands`.

Analogicznie, jeżeli przy planowaniu wcześniejszego miesiąca istnieje już znany future boundary fakt, nie wolno stworzyć trójki z nim. Jeżeli przyszły miesiąc jeszcze nie istnieje, późniejsze planowanie tego miesiąca sprawdzi regułę względem poprzedniej granicy.

### 3.4 Solver / constraints

Dodać jeden CP-SAT HARD owner, np. `add_max_two_consecutive_night_constraints(...)`, w `constraints.py` i podpiąć go w `solver.py`.

Nie dodawać `night_streak_excess_count`, wagi NIGHT_STREAK ani fazy minimalizującej liczbę trójek. To zostało odrzucone przez OWNER_CORRECTED.

Jeżeli ten HARD uczestniczy w niewykonalności, solver musi zachować informację potrzebną do istniejącej diagnozy `DECISION_REQUIRED` zamiast błędnie nazywać każdy cross-demand konflikt `REST-01`.

Do surowej diagnozy używać kodu `NIGHT-STREAK-01`.

### 3.5 Validator

Validator niezależnie, od zera, na finalnej liście Assignmentów + canonical boundary facts powtarza tę samą semantykę.

Violation code: `NIGHT-STREAK-01`.

To obowiązkowy anti-drift mirror HARD, a nie drugi scorer.

`validator.py` nie może importować solverowego helpera CP-SAT ani odpytywać jego wyniku.

### 3.6 Coordinator-facing DECISION_REQUIRED

Jeżeli `NIGHT-STREAK-01` jest przyczyną braku automatycznego pełnego grafiku, istniejący `DecisionRequiredPayload` pozostaje jedynym DTO.

W `decision_guidance.py` dodać wyłącznie tłumaczenie raw condition:

`NIGHT-STREAK-01` → `Koliduje z limitem dwóch nocek pod rząd`.

Nie dodawać automatycznego „obejścia” tej reguły ani opcji jej zaakceptowania. Jeżeli przy obecnej obsadzie i ograniczeniach nie ma rozwiązania, istniejące ogólne `Brak automatycznego rozwiązania...` pozostaje poprawną końcową opcją.

T032 nie zmienia ogólnej polityki ręcznej korekty ScheduleVersion; ten task dotyczy automatycznego candidate admissibility + niezależnego HARD validatora. Nie wymyślać w T032 nowego workflow override.

---

## 4. CHECKPOINT A — TARGET EQUITY

### 4.1 Jeden expression godzin

Dla każdego pracownika obecnego w istniejącym `target_by_employee`:

- `effective_target` = dokładnie `_effective_targets(state)`;
- `actual_hours` = dokładnie ten sam expression, którego TARGET-01 już używa;
- absencja nie jest przeliczana drugi raz;
- scope godzin nie jest rozszerzany.

Solver wyprowadza `actual_hours` oraz absolutne odchylenie raz i reuse przez istniejący TARGET-01 i equity.

### 4.2 Metryka

Dla `effective_target > 0`:

`completion_pct = floor(100 * actual_hours / effective_target)`.

Nie capować na 100.

Dla co najmniej dwóch dodatnich effective targetów:

`target_equity_spread = max(completion_pct) - min(completion_pct)`.

Mniejszy spread jest lepszy.

Pracownik z `effective_target == 0` jest wyłączony tylko z ratio; istniejący TARGET-01 nadal liczy jego `|actual_hours - 0|`.

### 4.3 TARGET-01 ma pierwszeństwo

Equity nie może świadomie kupić gorszej łącznej wartości TARGET-01.

Jeżeli budżet czasu pozwala udowodnić optimum `total_target_deviation`, blokuje się to optimum przed finalną objective.

Jeżeli budżet kończy się wcześniej, patrz §7: poprawny incumbent może wrócić z `optimization_complete=False`. Nie wolno wtedy twierdzić, że TARGET-01 optimum zostało udowodnione.

### 4.4 Finalny term

`TARGET_EQUITY_WEIGHT = 1` w `fairness.py`.

`TARGET_DEVIATION_WEIGHT = 100` pozostaje bez zmiany.

`add_target_equity_fairness(...)` dostaje już wyprowadzone `actual_hours` i effective targets. Nie czyta `PlanningState`, WorkBalance, Availability ani persistence.

---

## 5. CHECKPOINT B — REWARD D → N → WOLNE → WOLNE

Reward pozostaje SOFT i jest niezależny od nowego HARD max-2-N.

### 5.1 Waga

`DN_RHYTHM_REWARD_WEIGHT = 1`.

Każde pełne trafienie obniża finalną objective o 1.

### 5.2 Okno

Tylko cztery kolejne daty startu `(d, d+1, d+2, d+3)` całkowicie wewnątrz `state.month`.

T032 nie tworzy cross-month rewardu rytmu. Cross-month dotyczy tylko HARD `NIGHT-STREAK-01`.

### 5.3 Trafienie

`pattern_match(employee, d) = 1` tylko gdy:

1. w `d` startuje dokładnie jeden non-CANCELLED Assignment pracownika i jest PRIMARY D;
2. w `d+1` startuje dokładnie jeden non-CANCELLED Assignment i jest PRIMARY N;
3. w `d+2` nie startuje żaden non-CANCELLED Assignment tego pracownika;
4. w `d+3` nie startuje żaden non-CANCELLED Assignment tego pracownika.

N kończąca się rano w `d+2` nie psuje wzorca; „wolne” tutaj oznacza brak nowego startu Assignmentu. Odpoczynek godzinowy nadal należy do REST/WEEKLY-REST.

Fixed target-Site facts uczestniczą; redistributable baseline nie jest liczony drugi raz; other-Site nie uczestniczy.

Reward to suma trafień wszystkich pracowników. Nie ma wspólnej fazy brygady.

---

## 6. KOREKTA DIAGNOZY LIVE — WYMAGANY DOWÓD PIONOWY

Live `192 / 180 / 180 / 120 / 48` przy targetach `160` pozostaje sygnałem produktu, nie matematycznym oracle przyczyny.

T032 musi dowieść equity dwoma poziomami:

1. kontrolowany tie: dwie target-equivalent dystrybucje → mniejszy completion spread wygrywa;
2. realny `solve()` na małym wieloosobowym stanie: co najmniej 4 osoby, równe dodatnie effective targety, pula 12h demandów poniżej sumy targetów, HARD pozwala idealnie równo rozdzielić liczbę zmian → pierwszy FEASIBLE kandydat ma `max(actual_hours)-min(actual_hours) == 0`.

Jeżeli fixture sam tworzy HARD przeszkadzający równości, fixture jest zły; nie obniżać oczekiwania.

Nie zamrażać literalnego live wektora ani nazw osób/demand IDs.

---

## 7. OWNER TIME BUDGET — 3 MINUTY NA CAŁĄ OPERACJĘ

### 7.1 Jedna granica czasu

Usunąć produktowe znaczenie obecnego `SOLVER_TIME_LIMIT_SECONDS = 30.0`.

Jedna publiczna operacja `plan(state)` dostaje jeden budżet:

`PLANNING_OPERATION_BUDGET_SECONDS = 180`.

Deadline powstaje raz na początku operacji z monotonicznego zegara.

Każdy wewnętrzny solve — fallback stage, faza leksykograficzna, final objective i search alternatyw — dostaje wyłącznie **pozostały** czas do tego samego deadline. Pełne 180 s nie resetuje się per faza ani per retry.

Testy nie mogą realnie spać 180 s; deadline/clock ma być testowalny przez wstrzyknięty/fake monotonic clock albo mały test budget bez zmiany produkcyjnej wartości 180.

### 7.2 Co zwracamy po wyczerpaniu budżetu

A. Jeżeli solver ma co najmniej jednego pełnego kandydata i niezależny validator potwierdza wszystkie HARD:

- publiczny status pozostaje `FEASIBLE`;
- kandydat/kandydaci mogą zostać pokazani i wybrani;
- `PlanningResult.optimization_complete = False`;
- nie nazywać tego `TECHNICAL_ERROR` tylko dlatego, że nie udowodniono najlepszego SOFT optimum.

B. Jeżeli wszystkie wymagane fazy i finalna objective zostały udowodnione w budżecie:

- zwykły wynik;
- `optimization_complete = True`.

C. Jeżeli do deadline nie znaleziono żadnego HARD-poprawnego kandydata i nie ma też dowodu normalnego `DECISION_REQUIRED`:

- nie wolno wymyślać FEASIBLE;
- istniejący status `TECHNICAL_ERROR` może pozostać publiczną klasą braku rozstrzygnięcia;
- `optimization_complete = False`;
- `error_message` ma jasno mówić, że w 3 min nie znaleziono ani nie udowodniono wyniku i można uruchomić dalsze szukanie.

D. Jeżeli przed deadline solver udowodni normalne `DECISION_REQUIRED`, ten wynik jest kompletny; nie ma sensu „szukać lepszego SOFT”, dopóki nie zmienią się wejścia/świadoma decyzja.

### 7.3 Minimalna zmiana DTO

Do istniejącego `PlanningResult` dodać na końcu:

`optimization_complete: bool = True`.

Default `True` zachowuje kompatybilność istniejących konstruktorów/testów.

Nie dodawać nowego statusu `PARTIAL`, tabeli, job ID ani persisted solver session.

### 7.4 „Szukaj lepszej konfiguracji”

Gdy frontend otrzyma `FEASIBLE` + `optimization_complete=False`, pokazuje najlepszy znaleziony poprawny grafik i pyta:

**„Znaleziono poprawny grafik. Szukać lepszej konfiguracji?”**

Akcje:

- `Użyj tego grafiku` — zwykły istniejący wybór kandydata;
- `Szukaj lepszej konfiguracji` — uruchamia kolejny 3-minutowy przebieg na tych samych aktualnych wejściach.

Poprzednio znaleziony kandydat ma pozostać widoczny/dostępny jako fallback podczas kolejnego wyszukiwania; nie wolno go automatycznie zapisać ani wyrzucić na samym początku retry.

Nie jest wymagane zachowanie wewnętrznego obiektu `CpSolver` między requestami ani background job. Implementacja może rozpocząć nowy solve. Wcześniejszy kandydat może zostać użyty jako solution hint, jeżeli robi się to bez tworzenia nowego trwałego stanu; hint nie zmienia HARD ani rankingu.

Jeżeli kolejny przebieg nie przyniesie lepszego rezultatu albo również zakończy się `optimization_complete=False`, koordynator nadal może wybrać poprzedni poprawny grafik albo ponowić szukanie.

---

## 8. OBOWIĄZKOWY UX DLA DŁUGIEGO PLANOWANIA — POLECENIE DLA CC

To jest binding OWNER UX requirement, nie sugestia.

Podczas trwającego requestu PLAN/REPLAN koordynator musi widzieć, że program pracuje.

Minimalny dopuszczalny projekt:

- kręcąca się ikona **lub** indeterminate progress bar;
- tekst np. `Układam grafik — to może potrwać do 3 minut`;
- przycisk uruchamiający planowanie jest w tym czasie zablokowany przed podwójnym kliknięciem;
- ekran nie może wyglądać jak zawieszony;
- nie pokazywać wymyślonego procentu `37%/82%`, bo backend nie zna rzeczywistego procentu przeszukanej przestrzeni.

Po odpowiedzi `FEASIBLE + optimization_complete=False` UI pokazuje grafik normalnie oraz pytanie/akcję z §7.4.

Po `optimization_complete=True` nie pokazuje pytania o dalsze szukanie tylko z przyzwyczajenia.

Jeżeli brak kandydata po 3 minutach (`TECHNICAL_ERROR + optimization_complete=False`), UI ma pokazać czytelny komunikat, że limit czasu minął bez gotowego grafiku, oraz umożliwić ponowne szukanie. Nie może pokazać technicznego stack trace.

### Granica branchu

Na bazie T032 nie ma jeszcze kompletnego ekranu Planowanie miesiąca ani jego docelowego routera PLAN/REPLAN. Dlatego T032 **nie ma tworzyć sztucznego frontendowego scaffoldu tylko po to, żeby zamknąć ten punkt**.

Jednocześnie CC dostaje jawny obowiązek: kiedy implementuje/aktualizuje ekran Planowanie miesiąca i jego API seam, musi przenieść `optimization_complete` 1:1 oraz zrealizować powyższy loader + pytanie „Szukaj lepszej konfiguracji?”. Ekran nie przejdzie owner review bez tego zachowania.

Backend T032 ma już dostarczyć semantyczny sygnał potrzebny UI; frontend nie może zgadywać timeoutu z własnego zegara.

---

## 9. T028 QUALITY GATE

T028 pozostaje osobnym branchem/taskiem. T032 nie cherry-pickuje jego narzędzia.

Po implementacji T032 companion correction T028 ma traktować każdy FEASIBLE kandydat zawierający >2 kolejne PRIMARY N jako `QUALITY_FAIL` poligonu.

Po OWNER_CORRECTED jest to dodatkowy bezpiecznik regresji: produkcyjny solver/validator powinny już uniemożliwić taki FEASIBLE.

T028 nie implementuje reguły; tylko niezależnie wykrywa jej regresję na wynikach poligonu.

---

## 10. SCOPE

### Production — dozwolone

- `rota/planning/constraints.py` — CP-SAT HARD `NIGHT-STREAK-01`;
- `rota/planning/solver.py` — wiring HARD, objective, deadline/remaining budget;
- `rota/planning/validator.py` — niezależny mirror `NIGHT-STREAK-01`;
- `rota/planning/fairness.py` — target equity + D/N rhythm reward;
- `rota/planning/engine.py` — operation-wide budget propagation, timeout disposition, poprawna diagnoza NIGHT-STREAK conflict;
- `rota/planning/engine_types.py` — wyłącznie `PlanningResult.optimization_complete`;
- `rota/planning/decision_guidance.py` — wyłącznie polska etykieta `NIGHT-STREAK-01`;
- `rota/application/plan_ops.py` — tylko jeśli potrzebne jest 1:1 zachowanie `optimization_complete` na publicznej operacji; nie dodawać persistence solvera.

### Tests

- `tests/test_t032_soft_ranking.py`;
- można dodać osobny mały `tests/test_t032_night_streak.py`, jeżeli jeden plik stałby się nieczytelny;
- istniejące regressions właścicieli pozostają bez zmian.

### Poza zakresem produkcyjnego kodu T032

- nowe persistence/table/job queue/background worker;
- nowy PlanningStatus;
- UI/API scaffolding nieobecnego jeszcze ekranu Planowanie;
- cross-Site night streak;
- cross-month **reward** rytmu D/N;
- zmiana REST/WEEKLY/LOAD;
- nowy model absencji/targetu;
- sztywny grafik brygadowy;
- zmiana ogólnego manual-correction workflow;
- nowa decyzja kadrowa.

---

## 11. MINIMALNA MACIERZ ODBIORU

### NIGHT-STREAK-01 HARD

T32-N1 — current-month N/N legalne, N/N/N niewykonalne dla tej samej osoby.

T32-N2 — boundary: persisted N poprzedniego miesiąca + N/N bieżącego miesiąca jest zablokowane.

T32-N3 — D/N/N nie jest trójką N; N/wolne/N nie jest trójką N.

T32-N4 — fixed current-Site PRIMARY uczestniczy; redistributable baseline nie jest liczony podwójnie.

T32-N5 — TRAINEE i CANCELLED nie tworzą night-day; other-Site nie uczestniczy.

T32-N6 — validator odrzuca ręcznie wstrzyknięty final candidate z N/N/N, także przez boundary, kodem `NIGHT-STREAK-01`.

T32-N7 — solve, którego jedyną nową przyczyną niewykonalności jest limit N, trafia do `DECISION_REQUIRED`, a coordinator-facing blocker nie nazywa go REST-01.

### TARGET EQUITY

T32-A1 — kontrolowany remis TARGET-01: mniejszy completion spread wygrywa.

T32-A2 — różne targety: proporcjonalne wypełnienie wygrywa nad równymi surowymi godzinami przy tej samej wcześniejszej jakości.

T32-A3 — effective target po absence_hours, nie raw target.

T32-A4 — target=0: brak dzielenia/model invalid; osoba nadal podlega TARGET-01.

T32-A5 — surplus >100% nie jest capowany.

T32-A6 — pionowy real `solve()` z ≥4 równymi targetami i równomiernie rozdzielalnym shortage kończy z równymi actual hours.

### D/N RHYTHM

T32-B1 — więcej D→N→wolne→wolne trafień wygrywa przy równej wcześniejszej jakości.

T32-B2 — reward sumuje wiele trafień i wielu pracowników bez wspólnej fazy.

T32-B3 — N kończąca się rano pierwszego dnia „wolne” nie niszczy start-day rhythm.

T32-B4 — fixed target-Site facts uczestniczą; TRAINEE może zająć dzień wolny, lecz nie spełnia D/N.

T32-B5 — reward nie przechodzi przez granicę miesiąca.

### BUDŻET / PARTIAL OPTIMIZATION

T32-T1 — jeden fake 180s deadline jest współdzielony przez wszystkie wewnętrzne solve; pełny limit nie resetuje się między fazami/fallbackami.

T32-T2 — budget expires po znalezieniu HARD-poprawnego incumbent → `FEASIBLE`, candidate obecny, `optimization_complete=False`, validator PASS.

T32-T3 — pełne udowodnienie w budżecie → `optimization_complete=True`.

T32-T4 — budget expires bez kandydata i bez proof DECISION_REQUIRED → brak wymyślonego FEASIBLE, `TECHNICAL_ERROR`, `optimization_complete=False`, czytelny error_message.

T32-T5 — istniejący normalny `DECISION_REQUIRED` udowodniony przed deadline pozostaje normalnym wynikiem, nie jest maskowany timeoutem.

T32-T6 — default `optimization_complete=True` nie łamie istniejących konstruktorów `PlanningResult` ani regresji.

### Regresja

T32-R1 — istniejące REST/WEEKLY/LOAD/coverage/eligibility regressions zielone.

T32-R2 — weekend/holiday fairness, DAY_SHIFT_OFF, LEAVE_PLAN, REPLAN-MIN i exceptional-N pozostają w swoich dotychczasowych rolach.

T32-R3 — żaden timeout/partial path nie omija niezależnego validatora przed publicznym FEASIBLE.

---

## 12. PREIMPLEMENTATION RE-AUDIT

Independent Codex audituje exact corrected HEAD, nie otwierając ponownie zamkniętych R1 decyzji poza ich konsekwencją dla R2.

Required checks:

1. Czy `NIGHT-STREAK-01` jest teraz literalnym HARD max-2-N, nie score/fazą, i obejmuje boundary target-Site?
2. Czy solver i validator mają niezależnych ownerów tej samej reguły bez cross-Site rozszerzenia?
3. Czy brak rozwiązania przez N-streak może trafić do `DECISION_REQUIRED` z poprawną przyczyną zamiast REST-01/TECHNICAL_ERROR?
4. Czy equity nadal reuse canonical effective target/hours i nie może świadomie pogarszać udowodnionego TARGET-01 optimum?
5. Czy D→N→wolne→wolne pozostaje osobnym same-month SOFT rewardem?
6. Czy 180 s jest jednym budżetem całej operacji i nie resetuje się per solve/faza?
7. Czy HARD-poprawny incumbent po timeout może wrócić jako FEASIBLE wyłącznie po independent validator PASS i z `optimization_complete=False`?
8. Czy brak incumbent po timeout jest jawnie odróżniony od normalnego FEASIBLE/DECISION_REQUIRED bez nowego statusu?
9. Czy obowiązek UI loadera/pytania jest zapisany bez sztucznego frontend scaffoldu na branchu, który nie ma jeszcze docelowego ekranu Planowanie?
10. Czy test matrix obejmuje boundary NNN, real solve equity oraz budget recovery bez 180-sekundowych test sleeps?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` z numerowanymi pozostałymi defektami kontraktu.

Do PASS: **CC READ-ONLY / NOT READY FOR IMPLEMENTATION**.

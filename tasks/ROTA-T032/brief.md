# ROTA-T032 — SOFT ranking: rytm D/N/wolne/wolne + równomierność względem targetu

Status: **READY FOR CODEX PREIMPLEMENTATION AUDIT — CC READ-ONLY UNTIL PASS**

ARCHITECT_INPUT_SHA: `7d61f19831940f5cf5045e4a4d55a87e362dab57`
BASE_MAIN_SHA: `3be4ed37e735766a80ca2259c7d1b6981d22dbb5`
Pochodzenie: live testing T031 przez Pawła, 2026-08-24/25 (OCHRONA).

T032 jest czysto silnikowym domknięciem już istniejącego `arch/spec.md` SECTION 3 SOFT RANKING. Nie zmienia UI/API, HARD ani produktu kadrowego.

## 1. WYNIK PRODUKTOWY

Solver ma dodatkowo preferować:

1. grafiki z większą liczbą wystąpień rytmu **D → N → wolne → wolne**;
2. przy nierównym rozłożeniu pracy — grafiki, w których relacja wykonanych godzin do indywidualnego effective targetu jest bardziej wyrównana między pracownikami.

Oba mechanizmy są wyłącznie SOFT rankingiem. Nie mogą zmienić eligibility, coverage, REST, WEEKLY-REST, LOAD ani żadnego innego HARD.

Nie powstaje sztywny grafik brygadowy, wspólna faza pracowników, nowy status planowania ani nowa decyzja koordynatora.

## 2. ISTNIEJĄCY KANON I OWNERZY

Pozostają bez zmian:

- `rota/planning/solver.py` — składa CP-SAT i jedną funkcję celu;
- `rota/planning/fairness.py` — owner pomocniczych SOFT fairness terms;
- `_effective_targets(state)` — jedyny target używany przez solver: `max(0, target_hours - absence_hours)`;
- `TARGET_DEVIATION_WEIGHT = 100` — istniejący bezwzględny TARGET-01;
- `WEEKEND_FAIRNESS_WEIGHT = 1`, `HOLIDAY_FAIRNESS_WEIGHT = 1`, `SOFT_PENALTY_WEIGHT = 1` — istniejące SOFT;
- `validator.py` — niezależny validator HARD, nie scorer jakości kandydata.

T032 nie tworzy drugiego ownera score i nie zmienia `PlanningResult`/`ValidationReport`.

## 3. KOREKTA DIAGNOZY LIVE

Live wynik `192 / 180 / 180 / 120 / 48` przy deklarowanych targetach `160` był sygnałem problemu, ale sam nie dowodzi, że obecny wzór TARGET-01 jest jego jedyną przyczyną.

Dla tego konkretnego wektora część osób jest ponad targetem, więc suma `|target-actual|` nie jest matematycznie stała. Nie wolno zamrozić w T032 twierdzenia, że sam dodatkowy fairness term musi odtworzyć i wyjaśnić dokładnie ten live wynik.

Strukturalny brak jest jednak realny i niezależny od tego przykładu: gdy rozważane warianty mają tę samą sumę bezwzględnych odchyleń od targetów — typowo przy niedoborze rozłożonym między osoby pozostające poniżej targetu albo analogicznym nadmiarze — obecny TARGET-01 może nie rozstrzygać, na kim skupić różnicę. T032 dodaje jawny tie/quality signal dla tej klasy.

Test odbioru ma dowodzić tej własności na kontrolowanym stanie, a nie zakładać przyczyny live przykładu.

## 4. CHECKPOINT A — TARGET EQUITY

### 4.1 Semantyka

Dla każdego pracownika obecnego w istniejącym `target_by_employee`:

- `effective_target` = dokładnie wynik istniejącego `_effective_targets(state)`;
- `actual_hours` = dokładnie ten sam expression godzin, który obecny TARGET-01 porównuje z targetem: nowo wybierane PRIMARY + te same target-Site fixed PRIMARY;
- T032 nie zmienia hours scope, nie przelicza absencji i nie wciąga nowej semantyki cross-Site.

Jeżeli `effective_target > 0`, zdefiniuj całkowitoliczbowy procent realizacji:

`completion_pct = floor(100 * actual_hours / effective_target)`.

Nie capować wartości na 100: 120% i 150% to różne wyniki. Dzięki temu fairness działa zarówno przy niedoborze, jak i przy nadmiarze godzin.

Dla co najmniej dwóch pracowników z `effective_target > 0`:

`target_equity_spread = max(completion_pct) - min(completion_pct)`.

Minimalizowanie spreadu preferuje bardziej proporcjonalne wykorzystanie różnych targetów. Przykładowo przy targetach `160` i `80`, wynik `80/40` jest equity-lepszy od `60/60`, jeśli pozostała część funkcji celu jest równa.

### 4.2 effective_target == 0

Pracownik z `effective_target == 0` nie uczestniczy w `target_equity_spread` — relacja `actual/target` jest dla niego niezdefiniowana.

Nie oznacza to darmowej pracy: istniejący bezwzględny TARGET-01 nadal liczy jego `|actual_hours - 0|` z wagą 100. Nie dodawać fallback denominatora `1`, specjalnego etatu ani drugiego targetu.

Jeżeli mniej niż dwóch pracowników ma dodatni effective target, equity term = brak termu / 0.

### 4.3 Waga

Nowa stała w `fairness.py`:

`TARGET_EQUITY_WEIGHT = 1`.

Do objective trafia:

`TARGET_EQUITY_WEIGHT * target_equity_spread`.

`TARGET_DEVIATION_WEIGHT = 100` pozostaje bez zmian i nadal liczy dotychczasowe `sum(|actual-target|)`.

T032 nie wprowadza nowej fazy leksykograficznej. Equity jest dodatkowym SOFT termem w tej samej istniejącej funkcji celu, tak jak weekend/holiday fairness.

### 4.4 Implementacja ownership

Nowa funkcja w `rota/planning/fairness.py`, np. `add_target_equity_fairness(...)`, ma dostać już wyprowadzone przez solver:

- per-employee expression `actual_hours`;
- `effective_targets`.

`fairness.py` nie może sam czytać `PlanningState`, WorkBalance, Availability ani repozytoriów.

Solver powinien wyprowadzić expression godzin raz i reuse go dla istniejącego TARGET-01 oraz nowego equity, zamiast utrzymywać dwie kopie arytmetyki godzin.

## 5. CHECKPOINT B — D/N/WOLNE/WOLNE

### 5.1 Waga

Nowa stała w `fairness.py`:

`DN_RHYTHM_REWARD_WEIGHT = 1`.

Każde prawidłowe trafienie obniża objective o 1:

`-DN_RHYTHM_REWARD_WEIGHT * pattern_match`.

To jest zwykły SOFT reward. Przy pozostałych czynnikach równych więcej trafień zawsze rankingowo wygrywa.

Nie zmieniać istniejących wag innych SOFT w T032.

### 5.2 Okno temporalne

Rozpatruj wyłącznie okna czterech kolejnych **dat startu grafiku**:

`(d, d+1, d+2, d+3)`

w których wszystkie cztery daty należą do planowanego `state.month`.

T032 nie liczy rytmu przez granicę miesiąca/roku i nie dodaje historii poprzedniego ani przyszłego miesiąca. To ranking miesięcznego solve; cross-month continuity nie jest w tym tasku zamrożonym wymaganiem.

N kończąca się rano w `d+2` nie psuje wzorca. „Wolne” w tej preferencji oznacza brak Assignmentu **startującego** tego dnia, zgodnie z dzienną reprezentacją grafiku; rzeczywiste odpoczynki godzinowe nadal należą wyłącznie do istniejących HARD REST/WEEKLY-REST.

### 5.3 Dokładne trafienie dla jednego pracownika

`pattern_match(employee, d) = 1` tylko wtedy, gdy finalna treść target-Site grafiku w tym solve spełnia równocześnie:

1. w `d` startuje dokładnie jeden non-CANCELLED Assignment tego pracownika i jest to PRIMARY na demandzie sklasyfikowanym jako `ShiftKind.D`;
2. w `d+1` startuje dokładnie jeden non-CANCELLED Assignment tego pracownika i jest to PRIMARY na demandzie sklasyfikowanym jako `ShiftKind.N`;
3. w `d+2` nie startuje żaden non-CANCELLED Assignment tego pracownika;
4. w `d+3` nie startuje żaden non-CANCELLED Assignment tego pracownika.

„Dokładnie jeden” zapobiega uznaniu złożonego dnia z więcej niż jednym startem pracy za prosty element rytmu D/N.

D/N spełnia wyłącznie PRIMARY z jednoznacznym matching demandem. TRAINEE lub fixed Assignment bez matching `covers_demand_id` może blokować „wolne”, ale nie może być zgadywany jako D albo N.

### 5.4 Fakty fixed / REPLAN

Reward ma oceniać finalny kandydat, nie tylko nowe zmienne `x`.

Dlatego dla target-Site należy uwzględnić:

- nowo wybierane PRIMARY (`x`);
- te same non-CANCELLED fixed existing Assignments, które pozostają w grafiku podczas solve/replan.

Redistributable baseline PRIMARY nie jest fixed i jest reprezentowany przez ponownie rozwiązywane `x`, więc nie wolno policzyć go drugi raz.

T032 nie dodaje do rytmu `other_site_assignments` ani nowej cross-Site semantyki. Istniejące cross-Site REST/LOAD pozostają bez zmian.

### 5.5 Agregacja

Reward to suma wszystkich `pattern_match(employee, d)` dla wszystkich rozpatrywanych pracowników i okien.

Nie ma wspólnej fazy między pracownikami, limitu jednego trafienia na osobę ani dodatkowego bonusu „każdy ma przynajmniej jeden”. Zamrożona decyzja właściciela jest prostsza: więcej trafień łącznie = lepszy ranking, przy pozostałych SOFT równych.

## 6. VALIDATOR — DECYZJA ARCHITEKTA

`rota/planning/validator.py` pozostaje **POZA T032**.

Powód:

- jego kontraktem jest niezależne ponowne wyprowadzenie HARD violations;
- istniejące `warnings` są zdarzeniowymi informacjami o konkretnych już istniejących SOFT/exception paths, nie ogólnym raportem jakości objective;
- weekend fairness, holiday fairness i TARGET-01 nie mają mirror-score w validatorze;
- rytm D/N i target equity nie tworzą naruszenia, które koordynator musi zaakceptować.

Dodanie score/warning za „pogorszenie rytmu” przy ręcznej korekcie stworzyłoby nowy produktowy komunikat i drugi owner rankingu. T032 tego nie robi.

Solver i validator nadal muszą zgadzać się w HARD; T032 nie zmienia żadnego HARD.

## 7. JEDEN TASK, DWA CHECKPOINTY

T032 pozostaje jednym taskiem, ponieważ oba checkpointy zmieniają tę samą funkcję celu i mają tych samych ownerów (`fairness.py` + `solver.py`).

Implementacja i testy mają być logicznie rozdzielone na:

- Checkpoint A — target equity;
- Checkpoint B — D/N rhythm.

Awaria jednego checkpointu nie upoważnia do rozszerzenia drugiego ani do zmian validatora.

## 8. SCOPE

Production files dozwolone:

- `rota/planning/fairness.py`;
- `rota/planning/solver.py`.

Testy:

- `tests/test_t032_soft_ranking.py`.

Nie modyfikować bez literalnego niezależnego audit blockera:

- `rota/planning/validator.py`;
- constraints/REST/LOAD/WEEKLY;
- eligibility;
- assembler/persistence/domain;
- UI/API;
- WorkBalance/absence accounting;
- `arch/spec.md` — wymagane SOFT już są tam zapisane.

Nie dodawać nowego DTO/statusu/deviation/warning ani trwałego stanu.

## 9. MINIMALNA MACIERZ ODBIORU

### Checkpoint A — equity

T32-A1 — kontrolowany tie obecnego TARGET-01: dwóch lub więcej pracowników z dodatnimi targetami i stałą pulą godzin, warianty o tej samej sumie `|actual-target|`; solver wybiera wariant z mniejszym spreadem `completion_pct`.

T32-A2 — różne targety: przy pozostałych SOFT równych ranking preferuje proporcjonalne wypełnienie targetów, nie równe surowe godziny.

T32-A3 — `effective_target` po absence_hours, nie raw target: pracownik z obniżonym canonical targetem jest porównywany do wartości po absencji.

T32-A4 — `effective_target == 0`: brak dzielenia przez zero/model invalid; osoba jest wyłączona tylko z equity ratio, lecz istniejący TARGET-01 nadal działa.

T32-A5 — przypadek nadmiaru: dwie target-optimalne dystrybucje powyżej targetów; mniejszy spread `actual/target` wygrywa, co dowodzi braku capu na 100%.

### Checkpoint B — rytm

T32-B1 — dwaj kandydaci z identycznym HARD i pozostałym SOFT: większa liczba pełnych D→N→wolne→wolne trafień wygrywa.

T32-B2 — więcej niż jedno trafienie i więcej niż jeden pracownik: reward jest sumą trafień, bez wspólnej fazy.

T32-B3 — start-day semantics: N z `d+1` kończąca się w `d+2` nadal pozwala traktować `d+2` jako wolne, jeżeli nic nowego tego dnia nie startuje.

T32-B4 — REPLAN/fixed: fixed target-Site Assignment uczestniczy w klasyfikacji dnia; redistributable baseline nie jest liczony podwójnie.

T32-B5 — TRAINEE/fixed bez matching demand blokuje free-day, lecz nie może sam spełnić D/N.

T32-B6 — miesiąc: okno wymagające daty spoza `state.month` nie daje rewardu; brak nowego cross-month inputu.

### Regresja

T32-R1 — wszystkie istniejące HARD/regresje pozostają zielone; nowy SOFT nie może zmienić biznesowej klasy wyniku FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR przez naruszenie lub osłabienie HARD.

T32-R2 — istniejące weekend/holiday fairness, DAY_SHIFT_OFF, LEAVE_PLAN, REPLAN-MIN i day_only exceptional-N zachowują swoje dotychczasowe mechanizmy; T032 nie usuwa ich z objective/phases.

Nie wymagać dokładnego odtworzenia live wektora `192/180/180/120/48` jako dowodu przyczyny. Można użyć go później jako smoke produktu, nie jako matematyczny oracle testu.

## 10. PREIMPLEMENTATION AUDIT

Independent Codex audituje exact contract HEAD i odpowiada:

1. Czy target equity reuse dokładnie effective target i worked expression obecnego TARGET-01, bez drugiego hours ownera?
2. Czy metryka `floor(100 * actual/effective_target)` + max-min działa dla różnych targetów, shortage i surplus, a target=0 jest jednoznacznie wyłączony tylko z ratio?
3. Czy `TARGET_EQUITY_WEIGHT=1` i `DN_RHYTHM_REWARD_WEIGHT=1` są spójne z istniejącą weighted objective bez zmiany innych wag lub nowych faz?
4. Czy rytm ma jednoznaczną start-day semantykę, uwzględnia fixed target-Site facts i nie dubluje redistributable baseline?
5. Czy same-month-only jest implementowalne bez assembler/persistence/boundary zmian?
6. Czy pozostawienie validatora bez zmian zachowuje jego rolę HARD safety ownera i nie gubi żadnego wymaganego produktu?
7. Czy T032 pozostaje dwoma wąskimi SOFT terms bez nowego stanu, warningów, cross-Site/cross-month mechanizmu albo UI/API?
8. Czy minimalna macierz testów dowodzi semantyki, a nie przypadkowego konkretnego harmonogramu z live testu?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` z numerowanymi defektami kontraktu.

Do PASS: **CC READ-ONLY / NOT READY FOR IMPLEMENTATION**.

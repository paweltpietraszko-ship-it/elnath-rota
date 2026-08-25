# ROTA-T032 — SOFT ranking: rytm D/N/wolne/wolne + równomierność względem targetu

Status: **READY FOR CODEX PREIMPLEMENTATION RE-AUDIT — CC READ-ONLY UNTIL PASS**

ARCHITECT_INPUT_SHA: `7d61f19831940f5cf5045e4a4d55a87e362dab57`
BASE_MAIN_SHA: `3be4ed37e735766a80ca2259c7d1b6981d22dbb5`
R1_AUDIT: `tasks/ROTA-T032/round_01/tests/tests_r1.txt`
Pochodzenie: live testing T031 przez Pawła, 2026-08-24/25 (OCHRONA).

T032 domyka istniejący `arch/spec.md` SECTION 3 SOFT RANKING. Nie zmienia UI/API, HARD, validatora ani produktu kadrowego.

R1 skorygował trzy rzeczy: nagroda D→N→wolne→wolne nie zastępuje ochrony jakości przed seriami >2 N; target equity nie może niejawnie pogarszać istniejącego optimum TARGET-01; test helpera nie wystarcza jako dowód poprawy klasy problemu live. Te trzy korekty są skonsolidowane poniżej bez nowego modelu stanu.

## 1. WYNIK PRODUKTOWY

W istniejącej hierarchii solvera, po już zamrożonych silniejszych fazach REPLAN-MIN i exceptional-N, solver ma:

1. zachować najlepszą osiągalną **łączną wartość istniejącego TARGET-01** `sum(|actual_hours - effective_target|)`;
2. wśród rozwiązań z tym samym optimum TARGET-01 preferować takie, które minimalizują wystąpienia **trzech kolejnych N** u jednego pracownika;
3. następnie w zwykłym finalnym SOFT rankingu preferować bardziej wyrównaną relację `actual_hours / effective_target` oraz większą liczbę wystąpień rytmu **D → N → wolne → wolne**, obok już istniejących weekend/holiday/DAY_SHIFT_OFF/LEAVE_PLAN terms.

Wszystko powyżej pozostaje SOFT rankingiem. Seria >2 N NIE staje się HARD, violation, Deviation ani podstawą `DECISION_REQUIRED`.

Jeżeli zero serii >2 N nie jest osiągalne przy zachowaniu wcześniejszych faz i optimum TARGET-01, solver zwraca najlepszy osiągalny FEASIBLE kandydat zamiast fałszować HARD. Osobny poligon jakości ma wtedy zgłosić `QUALITY_FAIL`; patrz §8.

Nie powstaje sztywny grafik brygadowy, wspólna faza pracowników, nowy status planowania ani nowa decyzja koordynatora.

## 2. ISTNIEJĄCY KANON I OWNERZY

Pozostają bez zmian:

- `rota/planning/solver.py` — składa CP-SAT oraz kolejność faz i finalną objective;
- `rota/planning/fairness.py` — owner pomocniczych SOFT quality/fairness terms;
- `_effective_targets(state)` — jedyny target używany przez solver: `max(0, target_hours - absence_hours)`;
- istniejący expression `actual_hours` — nowo wybierane PRIMARY + te same target-Site fixed PRIMARY;
- `TARGET_DEVIATION_WEIGHT = 100` — istniejący bezwzględny TARGET-01 w finalnej objective;
- `WEEKEND_FAIRNESS_WEIGHT = 1`, `HOLIDAY_FAIRNESS_WEIGHT = 1`, `SOFT_PENALTY_WEIGHT = 1` — istniejące SOFT;
- `validator.py` — niezależny validator HARD, nie scorer jakości kandydata.

T032 nie tworzy drugiego ownera godzin ani score i nie zmienia `PlanningResult`/`ValidationReport`.

## 3. KOREKTA DIAGNOZY LIVE I WYMAGANY DOWÓD PIONOWY

Live wynik `192 / 180 / 180 / 120 / 48` przy deklarowanych targetach `160` był sygnałem problemu, ale sam nie dowodzi, że obecny wzór TARGET-01 jest jego jedyną przyczyną.

Dla tego konkretnego wektora część osób jest ponad targetem, więc suma `|target-actual|` nie jest matematycznie stała. Nie wolno twierdzić, że sam equity helper musi odtworzyć i wyjaśnić dokładnie ten live wynik.

Strukturalny tie jest jednak realny: gdy rozważane warianty mają tę samą sumę bezwzględnych odchyleń — np. przy niedoborze rozłożonym między osoby pozostające poniżej targetu — istniejący TARGET-01 sam nie rozstrzyga, na kim skupić różnicę.

T032 musi dowieść dwóch rzeczy osobno:

- mechanicznie: equity rozstrzyga taki tie bez pogarszania optimum TARGET-01;
- pionowo: realny `solve()` na kontrolowanym wieloosobowym stanie z równymi targetami i niedoborem daje mierzalnie wyrównany finalny rozkład, gdy HARD pozwala na taki rozkład.

Minimalny pionowy oracle: skonstruować przez zwykły `PlanningState`/produkcyjny solver mały przypadek z co najmniej 4 pracownikami o równych dodatnich effective targetach oraz pulą 12h demandów mniejszą niż suma targetów, w którym HARD pozwala rozdzielić liczbę zmian dokładnie równo. Pierwszy FEASIBLE kandydat ma wtedy osiągnąć ten równy rozkład (`max(actual_hours) - min(actual_hours) == 0`). Nie zamrażać nazwisk, demand IDs ani live wektora 192/180/180/120/48.

Jeżeli fixture nie pozwala na równy rozkład przez HARD, nie jest poprawnym dowodem T32-A6 i należy go zmienić, a nie obniżać oczekiwanie.

## 4. CHECKPOINT A — TARGET EQUITY

### 4.1 Jeden expression godzin i effective target

Dla każdego pracownika obecnego w istniejącym `target_by_employee`:

- `effective_target` = dokładnie wynik istniejącego `_effective_targets(state)`;
- `actual_hours` = dokładnie ten sam expression godzin, który obecny TARGET-01 porównuje z targetem;
- T032 nie zmienia hours scope, nie przelicza absencji i nie wciąga nowej semantyki cross-Site.

Solver wyprowadza per-employee `actual_hours` oraz absolutne odchylenia raz i reuse je przez TARGET-01, fazę optimum i equity. Nie wolno utrzymywać dwóch niezależnych kopii arytmetyki godzin.

### 4.2 Semantyka equity

Jeżeli `effective_target > 0`:

`completion_pct = floor(100 * actual_hours / effective_target)`.

Nie capować wartości na 100: 120% i 150% to różne wyniki.

Dla co najmniej dwóch pracowników z `effective_target > 0`:

`target_equity_spread = max(completion_pct) - min(completion_pct)`.

Mniejszy spread jest lepszy. Przy targetach `160` i `80`, wynik `80/40` jest equity-lepszy od `60/60`, jeżeli wcześniejsze fazy i pozostałe SOFT są równe.

### 4.3 effective_target == 0

Pracownik z `effective_target == 0` nie uczestniczy w `target_equity_spread`, ponieważ `actual/target` jest niezdefiniowane.

Nie oznacza to darmowej pracy: istniejący TARGET-01 nadal liczy `|actual_hours - 0|`. Nie dodawać denominatora `1`, specjalnego etatu ani drugiego targetu.

Jeżeli mniej niż dwóch pracowników ma dodatni effective target, equity term = 0 / brak termu.

### 4.4 TARGET-01 ma pierwszeństwo przed equity

R1-4 zamyka się jednoznacznie:

**equity NIE może pogorszyć minimalnej osiągalnej łącznej wartości istniejącego TARGET-01.**

Po istniejących fazach REPLAN-MIN i — gdy aktywna — exceptional-N, solver tworzy expression:

`total_target_deviation = sum(pos_employee + neg_employee)`

z tych samych vars, które zasilają obecny TARGET-01. Następnie używa istniejącego mechanizmu faz leksykograficznych:

1. `minimize(total_target_deviation)`;
2. wymaga `OPTIMAL` zgodnie z istniejącą semantyką `_solve_lexicographic_phases`;
3. blokuje `total_target_deviation == optimum`;
4. dopiero potem przechodzi do quality/final SOFT.

To świadoma decyzja produktu: proporcjonalność godzin jest tie/quality breakerem wśród target-optimalnych rozwiązań, a nie walutą do kupowania dodatkowych godzin odchylenia.

`TARGET_DEVIATION_WEIGHT = 100` nie musi być usuwany z finalnej objective; po zablokowaniu optimum jego łączny wkład jest stały między dalszymi kandydatami. Nie zmieniać wartości tej stałej w T032.

### 4.5 Equity w finalnej objective

Nowa stała w `fairness.py`:

`TARGET_EQUITY_WEIGHT = 1`.

Do finalnej objective trafia:

`TARGET_EQUITY_WEIGHT * target_equity_spread`.

Nowa funkcja w `fairness.py`, np. `add_target_equity_fairness(...)`, dostaje już wyprowadzone przez solver `actual_hours` i `effective_targets`. Nie czyta `PlanningState`, WorkBalance, Availability ani repozytoriów.

## 5. CHECKPOINT B — D/N QUALITY + RYTM

### 5.1 Seria >2 kolejnych N — osobna semantyka od rewardu rytmu

Nagroda D→N→wolne→wolne nie jest i nie może być zamiennikiem kontroli jakości serii nocek.

Dla każdego pracownika i każdej trójki kolejnych dat startu `(d, d+1, d+2)` całkowicie wewnątrz `state.month`:

`night_triple(employee, d) = 1`

jeżeli na każdej z tych trzech dat finalny target-Site grafik zawiera co najmniej jeden non-CANCELLED PRIMARY tego pracownika startujący na demandzie sklasyfikowanym jako `ShiftKind.N`.

`night_streak_excess_count = sum(night_triple(employee, d))`.

Konsekwencje:

- N/N/N daje 1;
- N/N/N/N daje 2;
- N/N/N/N/N daje 3;
- N/N, wolne, N nie daje trafienia;
- TRAINEE nie tworzy night-day;
- fixed target-Site PRIMARY z jednoznacznym matching demandem uczestniczy;
- redistributable baseline nie jest liczony drugi raz;
- `other_site_assignments` nie uczestniczą.

T032 nie dodaje cross-month night-streak inputu. Trójka wymagająca daty spoza `state.month` nie jest liczona w tym tasku.

### 5.2 Pozycja night-streak w rankingu

Po zablokowaniu optimum `total_target_deviation` solver dodaje następną fazę leksykograficzną:

`minimize(night_streak_excess_count)`

oraz blokuje jej udowodnione optimum przed finalną objective.

Czyli:

- jeżeli zero serii >2 N jest osiągalne bez naruszenia wcześniejszych faz i optimum TARGET-01, każdy późniejszy kandydat ma zero takich serii;
- jeżeli zero nie jest osiągalne, solver zachowuje minimalną osiągalną liczbę, ale nadal może zwrócić FEASIBLE — nie jest to HARD;
- finalne equity/rhythm/weekend/holiday nie mogą kupić większej liczby serii >2 N.

Nie dodawać `NIGHT_STREAK` violation, warninga, Deviation ani statusu planowania.

### 5.3 Reward D→N→wolne→wolne

Nowa stała w `fairness.py`:

`DN_RHYTHM_REWARD_WEIGHT = 1`.

Każde prawidłowe trafienie obniża finalną objective o 1:

`-DN_RHYTHM_REWARD_WEIGHT * pattern_match`.

Przy wcześniejszych fazach i pozostałych finalnych SOFT równych więcej trafień zawsze wygrywa.

### 5.4 Okno temporalne rytmu

Rozpatruj wyłącznie okna czterech kolejnych **dat startu grafiku** `(d, d+1, d+2, d+3)`, w których wszystkie cztery daty należą do planowanego `state.month`.

N kończąca się rano w `d+2` nie psuje wzorca. „Wolne” w tej preferencji oznacza brak Assignmentu **startującego** tego dnia; rzeczywiste odpoczynki godzinowe nadal należą wyłącznie do HARD REST/WEEKLY-REST.

### 5.5 Dokładne trafienie rytmu

`pattern_match(employee, d) = 1` tylko wtedy, gdy finalna treść target-Site grafiku spełnia równocześnie:

1. w `d` startuje dokładnie jeden non-CANCELLED Assignment tego pracownika i jest to PRIMARY na demandzie `D`;
2. w `d+1` startuje dokładnie jeden non-CANCELLED Assignment i jest to PRIMARY na demandzie `N`;
3. w `d+2` nie startuje żaden non-CANCELLED Assignment tego pracownika;
4. w `d+3` nie startuje żaden non-CANCELLED Assignment tego pracownika.

D/N spełnia wyłącznie PRIMARY z jednoznacznym matching demandem. TRAINEE lub fixed Assignment bez matching `covers_demand_id` może blokować „wolne”, ale nie może być zgadywany jako D albo N.

### 5.6 Fakty fixed / REPLAN i agregacja

Night-streak i rhythm oceniają finalny kandydat target-Site, nie tylko nowe `x`.

Uwzględnić:

- nowo wybierane PRIMARY (`x`);
- te same non-CANCELLED fixed existing target-Site Assignments, które pozostają w grafiku.

Redistributable baseline jest reprezentowany przez ponownie rozwiązywane `x` i nie może być liczony drugi raz.

Rhythm reward = suma wszystkich `pattern_match(employee, d)`. Nie ma wspólnej fazy pracowników, limitu jednego trafienia na osobę ani bonusu „każdy ma jeden”.

## 6. VALIDATOR — BEZ ZMIAN

`rota/planning/validator.py` pozostaje **POZA T032**.

Powód:

- jego kontraktem jest niezależne ponowne wyprowadzenie HARD violations;
- weekend fairness, holiday fairness i TARGET-01 nie mają mirror-score w validatorze;
- target equity, night-streak quality i rytm D/N nie tworzą naruszenia wymagającego akceptacji koordynatora;
- dodanie score/warning stworzyłoby drugi owner rankingu i nowy produktowy komunikat.

Solver i validator nadal muszą zgadzać się w HARD; T032 nie zmienia żadnego HARD.

## 7. JEDEN TASK, DWA CHECKPOINTY

T032 pozostaje jednym taskiem produktowym z dwoma checkpointami w tych samych ownerach:

- Checkpoint A — target equity + zachowanie optimum TARGET-01;
- Checkpoint B — night-streak quality + D/N rhythm.

Awaria jednego checkpointu nie upoważnia do zmian validatora, HARD, UI/API ani persistence.

## 8. T028 — OBOWIĄZKOWA OSOBNA WĄSKA KOREKTA QUALITY GATE

T028 nie jest na bazie `main` T032; istnieje na osobnej gałęzi `task/ROTA-T028` (implementacja poligonu m.in. `c469190...`). T032 NIE cherry-pickuje ani nie modyfikuje jego narzędzia na tej gałęzi.

R1-2 zamyka się przez jawny companion contract dla osobnej korekty T028 po implementacji T032:

Dozwolone pliki na gałęzi T028:

- `tools/solver_scenario_lab.py`;
- `tests/test_solver_scenario_lab.py`;
- istniejący brief T028 tylko jeśli potrzebne jest wpisanie tego oracle.

Zakazane: `rota/**`, `api/**`, persistence, solver, validator.

Dla każdego `FEASIBLE` wyniku poligon nadal wykonuje dotychczasowy validator i closed-world oracle, a dodatkowo dla **każdego zwróconego kandydata** sprawdza serię N:

1. bierze kanoniczne demands z już złożonego `PlanningState`;
2. klasyfikuje matching demand produkcyjnym `rota.planning.shift_catalog.classify_demand`, zamiast zgadywać po ID/czasie;
3. dla każdego pracownika liczy kolejne kalendarzowo daty startu PRIMARY sklasyfikowanych jako `N` w planowanym miesiącu;
4. seria długości >2 w dowolnym kandydacie oznacza `QUALITY_FAIL`, case FAIL i exit 1 dla runu z takim przypadkiem;
5. failure JSON zapisuje co najmniej employee_id i daty problematycznej serii oraz zwykły replay seed/family.

`QUALITY_FAIL` jest statusem/oracle poligonu, NIE nowym `PlanningResult.status`, validator violation ani produkcyjnym HARD.

Sprawdzenie pozostaje same-month, zgodnie z T032; nie dodaje boundary/cross-month do T028.

Ta korekta T028 ma własny focused audit/implementację na swojej gałęzi. PASS implementacji T032 nie oznacza automatycznie, że T028 quality gate został dostarczony. Natomiast pierwotny live problem „poligon uznał serię 3–5 N za PASS” nie może być oznaczony jako całościowo zamknięty, dopóki companion T028 nie jest zielony.

## 9. SCOPE T032

Production files dozwolone:

- `rota/planning/fairness.py`;
- `rota/planning/solver.py`.

Testy T032:

- `tests/test_t032_soft_ranking.py`.

Nie modyfikować w T032 bez literalnego niezależnego audit blockera:

- `rota/planning/validator.py`;
- constraints/REST/LOAD/WEEKLY;
- eligibility;
- assembler/persistence/domain;
- UI/API;
- WorkBalance/absence accounting;
- `arch/spec.md`;
- `tools/solver_scenario_lab.py` i test T028 — należą do companion §8 na osobnej gałęzi.

Nie dodawać nowego DTO/statusu/deviation/warning ani trwałego stanu.

## 10. MINIMALNA MACIERZ ODBIORU T032

### Checkpoint A — equity / TARGET-01

T32-A1 — kontrolowany tie TARGET-01: co najmniej dwóch pracowników, warianty o tej samej minimalnej `total_target_deviation`; mniejszy `target_equity_spread` wygrywa.

T32-A2 — różne targety: przy tej samej minimalnej total deviation ranking preferuje proporcjonalne wypełnienie targetów, nie równe surowe godziny.

T32-A3 — `effective_target` po `absence_hours`, nie raw target.

T32-A4 — `effective_target == 0`: brak dzielenia przez zero; osoba wyłączona tylko z ratio, nadal uczestniczy w TARGET-01.

T32-A5 — surplus: przy tej samej minimalnej total deviation mniejszy spread powyżej 100% wygrywa; brak capu.

T32-A6 — **vertical real-solver shortage** z §3: co najmniej 4 osoby o równych dodatnich effective targetach, pula godzin mniejsza od sumy targetów, HARD pozwala na równy rozkład; pierwszy FEASIBLE kandydat ma `max(actual)-min(actual) == 0`.

T32-A7 — **target preservation**: kontrolowany przypadek z dwiema osiągalnymi dystrybucjami, z których equity-lepsza ma większą `total_target_deviation`; solver musi wybrać niższą total deviation. To dowodzi, że equity nie może handlować TARGET-01.

### Checkpoint B — night streak / rytm

T32-B1 — przy tym samym optimum wcześniejszych faz kandydat bez night triple wygrywa z kandydatem z N/N/N, nawet jeśli drugi ma korzystniejszy zwykły finalny fairness.

T32-B2 — liczenie okien: NNN=1, NNNN=2, NNNNN=3; przerwana seria nie daje okna przez przerwę.

T32-B3 — jeśli zero `night_streak_excess_count` jest osiągalne przy tym samym wcześniejszym optimum, finalny kandydat ma zero; jeśli nie jest osiągalne, solver minimalizuje count, ale nie zmienia wyniku w HARD/DECISION_REQUIRED.

T32-B4 — dwaj kandydaci z tym samym night-streak optimum i pozostałym SOFT: więcej pełnych D→N→wolne→wolne trafień wygrywa.

T32-B5 — więcej niż jedno trafienie i więcej niż jeden pracownik: rhythm reward jest sumą, bez wspólnej fazy.

T32-B6 — start-day semantics: N kończąca się rano w następnym dniu nie psuje późniejszego „wolne”, jeżeli nic nowego tego dnia nie startuje.

T32-B7 — REPLAN/fixed: fixed target-Site Assignment uczestniczy w night/rhythm; redistributable baseline nie jest liczony podwójnie.

T32-B8 — TRAINEE/fixed bez matching demand może blokować rhythm free-day, ale nie tworzy D/N ani night-day.

T32-B9 — month boundary: trójka/okno wymagające daty spoza `state.month` nie jest liczone; brak nowego cross-month inputu.

### Regresja

T32-R1 — wszystkie istniejące HARD/regresje pozostają zielone; T032 nie osłabia ani nie dodaje HARD.

T32-R2 — istniejące REPLAN-MIN i exceptional-N zachowują pozycję przed nowym TARGET-01 optimum phase; weekend/holiday/DAY_SHIFT_OFF/LEAVE_PLAN pozostają w finalnej objective.

T32-R3 — dodatkowe fazy nie mogą być uznane za udowodnione przy statusie tylko FEASIBLE; zachować istniejący fail-closed kontrakt faz leksykograficznych.

Nie wymagać literalnego live wektora `192/180/180/120/48` jako oracle. T32-A6 jest uogólnionym pionowym dowodem klasy problemu.

## 11. PREIMPLEMENTATION RE-AUDIT

Independent Codex audituje corrected exact contract HEAD. Re-audyt ma skupić się na R1-1..R1-4 i nie otwierać ponownie zaakceptowanych ownerów/fixed/start-day/validator/cross-month granic.

Wymagane pytania:

1. Czy `total_target_deviation` jest wyprowadzony z dokładnie tych samych target/actual vars co TARGET-01 i zablokowany jako optimum przed equity?
2. Czy equity przy target=0, shortage i surplus jest implementowalne bez drugiego hours ownera i nie może pogorszyć TARGET-01?
3. Czy night-triple phase rzeczywiście rozróżnia NNN/NNNN/NNNNN i jest niezależna od D→N→wolne→wolne rewardu?
4. Czy kolejność istniejących faz → TARGET optimum → night-streak optimum → final SOFT zachowuje wcześniejsze kontrakty i nie zamienia jakości N w HARD?
5. Czy T32-A6 jest realnym pionowym dowodem poprawy klasy nierówności, a nie samym helper testem?
6. Czy companion §8 jednoznacznie zamyka fałszywy PASS T028 bez wciągania T028 code do branchu T032 i bez zmian `rota/**` w T028?
7. Czy validator/HARD/UI/API/persistence/cross-month pozostają poza zmianą?
8. Czy dokument nie twierdzi już, że sam rhythm reward rozwiązuje serię >2 N ani że T032 sam zamyka cały problem poligonu?

Required verdict:

- `PASS — READY_FOR_IMPLEMENTATION`, albo
- `FAIL` z numerowanymi pozostałymi defektami kontraktu.

Do PASS: **CC READ-ONLY / NOT READY FOR IMPLEMENTATION**.

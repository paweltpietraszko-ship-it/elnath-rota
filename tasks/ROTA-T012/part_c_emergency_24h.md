# ROTA-T012-C — HIDDEN EMERGENCY 24h RETRY

STATUS: READY FOR IMPLEMENTATION C AFTER B PRODUCT SHA IS PRESENT ON task/ROTA-T012
PARENT_CONTRACT: tasks/ROTA-T012/brief.md
B_PRODUCT_SHA: 8adb092ec319e27993b844601c30a133a06ccd3f
DATE: 2026-08-18

## CEL

Domknąć wyłącznie zamrożoną funkcję awaryjnego 24h:

- normalny solver działa bez zmian jako pierwszy przebieg;
- dopiero gdy pierwszy capped solve ma PROVEN INFEASIBLE, drugi capped solve może użyć emergency pairing;
- emergency pairing łączy dokładnie dwie bezpośrednio kolejne zwykłe 12h tego samego employee w jeden work period dla REST/provenance;
- działa same-month oraz, zgodnie z decyzją właściciela A, przez granicę miesiąca i roku;
- użytkownik nie widzi prób pośrednich ani nowego workflow.

C NIE dodaje nowych ekranów, pytań, statusów, DecisionRecord, SiteRule, schematu DB ani bytów domenowych.
C NIE zmienia normalnego katalogowego 24h wdrożonego w B.
C NIE zmienia zasad LOAD/TARGET/fairness/REPLAN.
C NIE implementuje T013 komunikacji ani T017 wielu wariantów.

## ANTI-BUREAUCRACY / MINIMALISM

Koordynator nadal dostaje wyłącznie istniejący publiczny PlanningResult:
FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR.

Nie dodawać:
- flagi „emergency mode” do publicznego API;
- osobnego „trybu 24h” w PlanningState;
- dodatkowego approval flow;
- nowej klasy decyzji;
- nowego persistent event/audit log;
- ręcznego wyboru „uruchom drugi pass”;
- osobnego solvera, backtrackingu ani enumeracji rozwiązań poza CP-SAT;
- nowej warstwy façade/service tylko dla C.

Jeżeli istniejący kod nie potrzebuje dotknięcia autoryzowanego pliku, nie zmieniać go.

## PART C SCOPE

- rota/planning/state.py
- rota/application/assembler.py
- rota/persistence/schedule_repository.py
- rota/planning/eligibility.py
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/validator.py
- rota/planning/engine.py
- rota/planning/work_periods.py
- tests/test_t012.py

Żaden inny plik w C.
Nie powstaje żaden nowy plik.

`eligibility.py`, `schedule_repository.py` i `work_periods.py` są w scope tylko wtedy, gdy wymagane jest wąskie reuse/extension istniejącej logiki B. Nie tworzyć równoległej implementacji.

## 1. JEDNA PRAWDA O OBSADZIE

Istniejące CP-SAT `x[employee_id, demand_id]` pozostaje jedyną prawdą o tym, czy employee pokrywa demand.

Emergency pairing NIE może tworzyć drugiej warstwy coverage.

W szczególności:
- COVERAGE nadal liczy `x`;
- LOAD nadal liczy realne godziny dwóch 12h jako 12+12;
- TARGET nadal liczy realne godziny dwóch 12h;
- weekend/holiday fairness nadal liczy istniejące placementy;
- REPLAN-MIN-01 nadal liczy zmianę placementów employee↔demand;
- emergency pair nie dostaje osobnej nagrody/kary SOFT.

Para jest wyłącznie sposobem interpretacji dwóch wybranych placementów jako jednego work period dla REST i Assignment provenance.

## 2. INTERNAL PAIR LITERAL

W drugim przebiegu można dodać wewnętrzny bool:

`pair[e, first_demand_id, second_demand_id]`

dla legalnego candidate.

Pair literal:
- istnieje tylko gdy `allow_emergency_24h=True`;
- `pair <= x[e, first]`;
- `pair <= x[e, second]`;
- nie może być 1, jeżeli employee nie pokrywa obu demandów;
- dla jednego `(employee, demand)` suma pair literals obejmujących ten demand <= 1.

Ostatnia reguła jest PER EMPLOYEE, nie globalnie per demand.
Przy `required_primary_count > 1` różni employees mogą niezależnie użyć pairingu na tej samej parze demandów. Nie wolno przez to wymagać identycznego całego PRIMARY set na obu zwykłych 12h.

Dla danego employee nie może powstać D1+D2 oraz D2+D3. To zamyka 36h/48h chain bez blokowania innych employees.

## 3. STANDALONE VS PAIRED WORK-PERIOD MODE

Nie wolno kodować specjalnych wyjątków REST para-po-parze w kilku miejscach.

Rozszerzyć B-owy model candidate work periods tak, aby każda wybrana zwykła 12h była dla REST:

- standalone, jeśli jej `x=1` i nie bierze udziału w żadnym pair;
- częścią emergency 24h periodu, jeśli odpowiedni `pair=1`.

Technicznie można użyć wewnętrznego standalone literal:
`standalone[e,d] = x[e,d] - sum(pair literals involving e,d)`.

REST constraints mają operować na aktywnych work-period modes:
- ordinary standalone period;
- istniejący normalny katalogowy 24h period z B;
- emergency same-month 24h period;
- emergency cross-month 24h period;
- fixed persisted periods z B.

Nie budować drugiej funkcji REST obok `work_periods.py`/B semantics.

Po aktywacji pair zwykły component REST nie może nadal równolegle blokować okresu, bo rest po emergency 24h pochodzi z 24h capability, nie z pojedynczej 12h.

## 4. SAME-MONTH PAIR CANDIDATE

Dla employee `e` pair(first, second) może istnieć tylko gdy:

- oba demandy mają `catalog_kind=12h`;
- oba trwają dokładnie 12h;
- nie są komponentami normalnego katalogowego 24h;
- `second.start_datetime == first.end_datetime`;
- `second.shift_kind` jest przeciwne do `first.shift_kind` (D↔N);
- `first.emergency_24h_rest_hours is not None`;
- employee ma zwykły legalny SolverSlot / jest indywidualnie eligible dla first;
- employee ma zwykły legalny SolverSlot / jest indywidualnie eligible dla second;
- na mixed profile istniejąca kwalifikacja B `can_work_24h` pozwala na 24h.

Nie consultować current SiteProfile w celu wyliczenia emergency rest.
Źródłem rest jest snapshot `first.emergency_24h_rest_hours` utworzony przez A.

INNY nigdy nie jest pair candidate, także 8+16, 16+8, 8+8+8.

## 5. SAME-MONTH ASSIGNMENT PROVENANCE

Jeżeli `pair[e, first, second]=1`, solver nadal tworzy dwa zwykłe Assignment, po jednym dla każdego demandu.

Oba:
- mają tego samego employee;
- zachowują własny `covers_demand_id`;
- mają ten sam deterministyczny `work_period_id`;
- mają `required_rest_after_hours = first.emergency_24h_rest_hours`.

`work_period_id` ma być deterministyczny z employee + uporządkowanej pary demandów, bez losowego UUID i bez nowego persistent bytu.

Jeżeli pair=0, Assignment zachowuje zwykłe B provenance dla standalone 12h.

## 6. CROSS-MONTH / CROSS-YEAR — OWNER DECISION A

Pairing przez granicę powstaje wyłącznie podczas PLAN/REPLAN późniejszego miesiąca.

Przykłady obowiązkowe:
- N 31.08 17:00–01.09 05:00 + D 01.09 05:00–17:00;
- N 31.12 17:00–01.01 05:00 + D 01.01 05:00–17:00.

Wcześniejszy ScheduleVersion i jego Assignment pozostają niezmienione.

C dodaje wymagane przez Frozen Product Contract pole:

`PlanningState.boundary_shift_demands: tuple[ShiftDemand, ...]`

Są to persisted CURRENT ShiftDemand odpowiadające same-site `boundary_assignments`.
Nie jest to nowa tabela ani nowy persistent model.

Assembler ma złożyć to provenance z istniejącego persisted ScheduleVersion.
Preferowane jest reuse istniejących snapshot reads; nie tworzyć generic history service.

## 7. CROSS-MONTH PAIR CANDIDATE

Boundary Assignment może być first half tylko gdy:

- jest PRIMARY;
- nie jest CANCELLED;
- należy do poprzedniego CURRENT same-site ScheduleVersion;
- ma `work_period_id`;
- matching `boundary_shift_demand` istnieje;
- boundary demand ma `catalog_kind=12h`;
- boundary demand trwa dokładnie 12h;
- ma jawny `shift_kind`;
- ma `emergency_24h_rest_hours is not None`;
- work-period-complete persisted context pokazuje, że `(employee_id, work_period_id)` ma dokładnie jedną CURRENT komponentę;
- current demand ma `catalog_kind=12h`;
- current demand trwa dokładnie 12h;
- `current.start == boundary.end`;
- current shift_kind jest przeciwne D↔N;
- ten sam employee jest indywidualnie eligible do current demand;
- na mixed profile istniejąca kwalifikacja B `can_work_24h` pozwala na 24h.

Nie rewalidować historycznej boundary połowy przez dzisiejsze DAY_ONLY/availability/profile.
To jest persisted fact; C jej nie zmienia.

Brak boundary Assignment, matching boundary demand albo kompletnego work-period context = brak candidate.
Bez warningu, pytania i bez zgadywania.

## 8. CROSS-MONTH REST MODE

Dla cross-month pair istnieje internal pair literal związany z current `x`.

Gdy pair=0:
- boundary period zachowuje zwykłą B semantykę fixed persisted work period;
- current 12h jest zwykłym standalone periodem.

Gdy pair=1:
- boundary standalone REST mode jest wyłączony wyłącznie wewnątrz modelu REST dla tego solve;
- aktywny jest jeden combined work period od `boundary.start` do `current.end`;
- combined period ma rest `boundary_shift_demand.emergency_24h_rest_hours`;
- current Assignment reuse dokładnie persisted `boundary.work_period_id`;
- current Assignment zapisuje terminalny `required_rest_after_hours` 24h;
- boundary Assignment nie jest przepisywany.

Persisted boundary record pozostaje niezmieniony.
Period mający już 2 CURRENT komponenty nie może zostać wydłużony do trzeciej.

## 9. SOLVER TWO-PASS — MINIMAL ORCHESTRATION

Publiczne `plan(state)` nie zmienia sygnatury ani statusów.

Wewnętrzne `solve()` może dostać parametr:
`allow_emergency_24h: bool = False`.

Sekwencja:

1. `solve(state, enforce_load_cap=True, allow_emergency_24h=False)`.
2. Jeżeli jest candidate: zwykła independent validation i obecny outcome. NIE uruchamiać emergency dla lepszego SOFT.
3. Jeżeli istnieje zwykłe `unassignable_demand_ids`: użyć istniejącego DECISION_REQUIRED.
4. Jeżeli status nie jest `INFEASIBLE`: TECHNICAL_ERROR. UNKNOWN/MODEL_INVALID nie uruchamia emergency.
5. Jeżeli pierwszy capped solve jest `INFEASIBLE`: uruchomić `solve(... enforce_load_cap=True, allow_emergency_24h=True)`.
6. Jeżeli emergency capped daje candidate: independent validation + normalny final outcome.
7. Jeżeli emergency capped ma technical status: TECHNICAL_ERROR.
8. Jeżeli emergency capped jest `INFEASIBLE`: uruchomić LOAD diagnosis jako `solve(... enforce_load_cap=False, allow_emergency_24h=True)`.
9. Uncapped fallback musi używać dokładnie tego samego emergency capability/boundary context co capped emergency solve.
10. Finalny DECISION_REQUIRED powstaje dopiero po wyczerpaniu tej sekwencji.

Nie uruchamiać uncapped non-emergency solve po wejściu w C fallback.
Nie dodawać trzeciego rodzaju retry.

## 10. ENGINE / KOMUNIKACJA

C nie implementuje T013.

Nie dodawać:
- dynamicznych unblocking options;
- nowych opisów dla koordynatora;
- komunikatu „spróbowano emergency 24h”;
- nowego public warning typu emergency-used;
- przycisku/checkboxa do uruchamiania drugiego passu.

Jeżeli istniejący dokładny blocker path potrafi już bez heurystyki zachować `SHIFT-24-01`, może go zachować.
Nie budować w C nowej heurystycznej diagnostyki tylko po to, aby wyświetlić `SHIFT-24-01`.

## 11. INDEPENDENT VALIDATOR

Validator musi niezależnie potwierdzić finalne emergency provenance; nie ufa pair vars solvera.

Dla same-month emergency period z dwóch ordinary H12:
- dokładnie 2 komponenty dla employee/work_period_id;
- przeciwne D/N;
- bezpośrednia ciągłość;
- first demand ma emergency rest snapshot;
- nowo utworzone komponenty niosą poprawny emergency rest;
- employee ma can_work_24h na mixed profile;
- INNY nie występuje;
- trzecia komponenta = HARD fail.

Dla cross-month:
- dokładnie jedna persisted boundary komponenta + jedna target komponenta;
- matching boundary demand provenance istnieje;
- adjacency i D↔N;
- terminal target rest == boundary demand emergency rest;
- target reuse boundary work_period_id;
- wcześniejszy Assignment nie wymaga przepisania rest;
- period z >2 CURRENT komponentami = HARD fail.

Niepoprawna struktura work period: `SHIFT-24-PAIR-01`.
Brak kwalifikacji na mixed profile: `SHIFT-24-01`.

B-owy REST validator następnie traktuje legalną parę jako jeden work period i sprawdza rest dopiero po jego końcu.

## 12. REPLAN / FIXED FACTS

REPLAN-MIN-01 nadal operuje na employee↔demand placementach `x`.
Pair literal nie jest osobnym placementem i nie może sztucznie zwiększać/zmniejszać reshuffle count.

Emergency nie daje prawa do zmiany:
- REALIZED;
- frozen;
- TRAINEE;
- wcześniejszego ScheduleVersion;
- persisted boundary Assignment.

Może jedynie zmienić sposób REST/provenance dla legalnie wybranych placementów aktualnie rozwiązywanego miesiąca.

## 13. TESTY C — MINIMUM

Dopisać wyłącznie do istniejącego `tests/test_t012.py`.

Obowiązkowe:

A. Orkiestracja
- first capped FEASIBLE => emergency solve nie jest wołany;
- first capped UNKNOWN/MODEL_INVALID => TECHNICAL_ERROR bez retry;
- first capped INFEASIBLE => exactly one capped emergency retry;
- emergency capped INFEASIBLE => uncapped retry ma `allow_emergency_24h=True`;
- uncapped non-emergency fallback po wejściu w C nie występuje.

B. Same-month
- D→N rescue;
- N→D rescue;
- pair używa tego samego employee;
- shared work_period_id + emergency rest;
- ordinary H12 może pozostać standalone gdy pair nie jest wybrany;
- can_work_24h=false na mixed profile nie pairuje;
- INNY 8+16 / 16+8 / 8+8+8 nie pairuje;
- per-employee no-chain >2;
- required_primary_count >1: pairing per employee, bez wymuszania identycznego pełnego PRIMARY set.

C. Nie podwajać logiki godzin
- coverage nadal exact;
- LOAD dla pary = 12+12;
- target/fairness nie dostają dodatkowego emergency term;
- REPLAN reshuffle liczy placements, nie pair literal.

D. Cross-month/year real persistence
- N 31.08 + D 01.09 rescue;
- N 31.12 + D 01.01 rescue;
- current Assignment reuse boundary work_period_id;
- terminal rest pochodzi z persisted boundary demand snapshot;
- zmiana current SiteProfile po zapisie boundary nie zmienia tego rest;
- wcześniejszy ScheduleVersion/Assignment pozostaje niezmieniony;
- boundary work period z już 2 komponentami nie może dostać trzeciej;
- brak matching boundary demand => brak pair bez warningu;
- missing/incomplete boundary context => fail closed jako brak candidate.

E. Independent validation
- każdy FEASIBLE emergency candidate => HARD PASS;
- ręcznie zbudowane malformed emergency 3-component => SHIFT-24-PAIR-01;
- malformed INNY pair => SHIFT-24-PAIR-01;
- mixed profile can_work_24h=false => SHIFT-24-01.

F. Regresja
- wszystkie testy B pozostają PASS;
- ROTA-REG-001 PASS;
- full suite PASS;
- Ruff PASS;
- `python guard.py check arch/spec.md` PASS;
- `git diff --check` PASS.

## 14. FORBIDDEN IN C

- nowy plik;
- nowa tabela / schema v6;
- nowy ShiftKind;
- nowy persistent `EmergencyPair` entity;
- nowy PlanningResult status;
- nowy user approval;
- nowy command/service/workflow layer;
- własny combinatorial search poza CP-SAT;
- przebudowa B work-period semantics;
- zmiana SiteProfile/ShiftDemand persistence z A;
- zmiana normalnego H24 z B;
- T013 human communication;
- T017 multi-candidate diversity.

## GATE C

Codex audytuje dokładny PRODUCT SHA C.

Szczególnie:
- pair jest wyłącznie REST/provenance mode, a nie drugim coverage modelem;
- first-pass FEASIBLE nigdy nie uruchamia emergency;
- UNKNOWN/MODEL_INVALID nie są maskowane retry;
- LOAD fallback jest emergency-enabled;
- ordinary component REST jest naprawdę wyłączony, gdy pair jest aktywny;
- cross-month nie mutuje poprzedniego ScheduleVersion;
- rest pochodzi z persisted boundary demand snapshot, nie current profile;
- no-chain działa per employee bez błędnego globalnego blokowania required_primary_count>1;
- nie pojawiła się nowa biurokracja dla koordynatora.

Wymagany wynik:
`PASS — READY_FOR_IMPLEMENTATION_D`.

RATIO / TOTAL_LINES wracają do jawnej akceptacji dopiero na finalnym audytowanym SHA C, jeżeli backend.py zwróci WYMAGA_DECYZJI.

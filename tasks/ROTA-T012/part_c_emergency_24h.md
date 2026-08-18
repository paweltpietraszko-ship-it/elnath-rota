# ROTA-T012-C — HIDDEN EMERGENCY 24h RETRY

STATUS: BLOCKED UNTIL B PASS; T012-R1-3 CLOSED BY OWNER 2026-08-18
PARENT_CONTRACT: `tasks/ROTA-T012/brief.md`

## CEL

Dodać drugi, niewidoczny dla użytkownika przebieg CP-SAT, który może uratować pełny grafik przez potraktowanie dwóch bezpośrednio kolejnych zwykłych 12h jako jednego 24h work period uprawnionego pracownika.

Normalne katalogowe 24h z B nie jest „emergency” i istnieje już w pierwszym przebiegu.

## PART C SCOPE

- rota/domain.py
- rota/application/assembler.py
- rota/application/deviation_mapping.py
- rota/persistence/schedule_repository.py
- rota/planning/eligibility.py
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/validator.py
- rota/planning/engine.py
- rota/planning/work_periods.py
- tests/test_t012.py

Żaden inny plik w C.

## PAIR CANDIDATE — TEN SAM MIESIĄC

Awaryjna para dwóch bieżących demandów istnieje tylko gdy:

- oba demandy są zwykłym `catalog_kind=12h`, nie normalnymi componentami katalogowego 24h;
- każdy trwa dokładnie 12h;
- `second.start_datetime == first.end_datetime`;
- shift_kind są przeciwne D↔N;
- first.emergency_24h_rest_hours jest jawnie snapshotowane i nie-None;
- employee może indywidualnie pokryć oba demandy według wszystkich HARD poza internal REST pomiędzy tymi dwoma;
- mixed profile: membership.can_work_24h=true;
- all-24 profile nie potrzebuje emergency pairingu, bo normalne 24h jest jedynym katalogiem; drugi pass nie ma tworzyć dodatkowej alternatywnej semantyki na takim profilu.

INNY nie jest pair candidate nawet jeśli dwie/trzy pozycje sumują się do 24h.

## T012-R1-3 — OWNER DECISION A: CROSS-MONTH EMERGENCY 24h

**DECYZJA WŁAŚCICIELA 2026-08-18: TAK.** Awaryjne 24h może łączyć dwie bezpośrednio kolejne zwykłe 12h także wtedy, gdy pierwsza należy do poprzedniego `ScheduleVersion.month`, a druga do aktualnie planowanego miesiąca. Dotyczy identycznie granicy roku.

Przykłady obowiązkowe:

- N 31.08 17:00–01.09 05:00 + D 01.09 05:00–17:00;
- N 31.12 17:00–01.01 05:00 + D 01.01 05:00–17:00.

### Reprezentacja techniczna

T012 NIE rozszerza jednego ScheduleVersion na dwa miesiące i NIE mutuje wcześniejszego ScheduleVersion.

Cross-month emergency pair jest tworzony podczas PLAN/REPLAN **późniejszego miesiąca**:

1. `PlanningState.boundary_assignments` zawiera persisted CURRENT Assignment z poprzedniego miesiąca jak dotychczas.
2. T012 dodaje `PlanningState.boundary_shift_demands: tuple[ShiftDemand, ...]` dla demandów pokrywanych przez te boundary Assignment. Assembler/repository pobierają je z tego samego persisted CURRENT ScheduleVersion; current SiteProfile nie służy do rekonstrukcji ich catalog/emergency provenance.
3. Boundary candidate może być pierwszą połową emergency 24h tylko gdy:
   - jest PRIMARY i nie-CANCELLED;
   - matching boundary ShiftDemand ma `catalog_kind=12h`, dokładnie 12h, jawny `shift_kind` oraz `emergency_24h_rest_hours is not None`;
   - boundary work period jest standalone: jego `work_period_id` ma dokładnie jedną CURRENT komponentę w work-period-complete boundary context;
   - bieżący demand jest zwykłym `catalog_kind=12h`, dokładnie 12h, zaczyna się dokładnie na końcu boundary Assignment i ma przeciwny D/N;
   - ten sam employee jest eligible do bieżącego demandu i — na mixed profile — ma `can_work_24h=true`.
4. Jeżeli solver wybiera cross-month pair, tworzy tylko Assignment należący do późniejszego miesiąca. Ten Assignment:
   - ma tego samego employee co boundary Assignment;
   - **reuse** `work_period_id` boundary Assignment;
   - ma `required_rest_after_hours = boundary_shift_demand.emergency_24h_rest_hours`.
5. Boundary Assignment i jego wcześniejszy ScheduleVersion pozostają byte-for-byte/semantycznie niezmienione; nie wolno przepisywać jego `required_rest_after_hours`, statusu, frozen ani historii.
6. Dla rozszerzonego cross-month work period wcześniejsza wartość `required_rest_after_hours` na boundary Assignment staje się wartością nieterminalnej komponenty i NIE jest ścianą odpoczynku pomiędzy połówkami. Odpoczynek po całym 24h okresie bierze się z **terminalnej, późniejszej komponenty**.
7. Work-period normalization musi być boundary-complete: jeżeli boundary Assignment ma `work_period_id`, assembler/repository dołączają wszystkie CURRENT komponenty tego samego employee/work_period_id potrzebne do ustalenia span i liczby komponentów. Work period mający już 2 komponenty nie może zostać ponownie rozszerzony; to zamyka 36h/48h chain także na kolejnej granicy miesiąca.
8. Jeżeli poprzedniego CURRENT Assignment lub matching boundary ShiftDemand nie ma w LocalStore, program nie zgaduje cross-month emergency capability i nie tworzy z tego osobnego warning/DECISION_REQUIRED; po prostu ta cross-month para nie jest dostępna.
9. Nie wolno tworzyć future demandu następnego miesiąca podczas PLAN wcześniejszego miesiąca. Cross-month pairing powstaje wyłącznie wtedy, gdy późniejszy demand realnie należy do aktualnie planowanego miesiąca.

Ta reprezentacja jest technicznym wykonaniem decyzji A i zachowuje `ScheduleVersion` jako stan jednego Site/miesiąca.

## CP-SAT, NIE WŁASNY SEARCH

Pairing musi być modelowany jako opcjonalne decyzje/constraints w CP-SAT. Nie wolno implementować własnego backtrackingu, permutacji ani zewnętrznego combinatorial search.

Model musi gwarantować:

- jeśli employee używa same-month emergency pair, jest PRIMARY na obu demandach;
- jeśli employee używa cross-month emergency pair, jest już PRIMARY na persisted boundary Assignment i zostaje PRIMARY na bieżącym demandzie;
- same-month oba Assignment dostają ten sam work_period_id i required_rest_after_hours = emergency_24h_rest_hours;
- cross-month current Assignment reuse boundary work_period_id i terminalny rest zgodnie z sekcją wyżej;
- demand nie może jednocześnie należeć do dwóch pairings w jednym solution;
- nie powstaje chain >2 poprzez D1+D2 oraz D2+D3 ani przez kolejne miesiące;
- coverage nadal dokładnie required_primary_count;
- jeżeli required_primary_count >1, pairing jest per employee; nie wolno wymagać, by wszyscy PRIMARY na dwóch niezależnych zwykłych demandach byli identyczni, chyba że konkretny employee używa pairing option.

## ENGINE TWO-PASS CONTRACT

`plan()` zachowuje trzy public statuses i nie ujawnia próby numer 1/2.

Sekwencja:

1. capped solve `allow_emergency_24h=False`;
2. jeśli daje candidate → zwykła independent validation i normalny outcome; NIE uruchamiać emergency tylko po to, żeby znaleźć „lepszy” SOFT;
3. jeśli pierwszy solve ma PROVEN business INFEASIBLE/shortage/conflict, uruchomić capped solve `allow_emergency_24h=True`;
4. drugi model zawiera legalne same-month oraz dostępne cross-month pair candidates;
5. jeśli drugi daje candidate → validate i outcome;
6. jeśli drugi capped jest INFEASIBLE, diagnoza LOAD przez uncapped retry MUSI również mieć `allow_emergency_24h=True` i ten sam boundary context;
7. UNKNOWN/MODEL_INVALID/technical status pierwszego lub drugiego przebiegu nie może być maskowany kolejną próbą jako zwykły DECISION_REQUIRED;
8. finalny DECISION_REQUIRED ma opisywać stan po wyczerpaniu legalnego emergency mechanism, nie intermediate blocker pierwszego przebiegu.

Istniejący unassignable/conflict diagnosis może zostać refaktoryzowany tylko tyle, ile potrzeba do zachowania tej sekwencji.

## ELIGIBILITY / BLOCKERS

`SHIFT-24-01` jest aktywnym HARD/qualification blockerem tylko w kontekście próby przydzielenia normalnego/emergency 24h na mixed profile.

Nie wolno globalnie uznać pracownika `can_work_24h=false` za nieeligible do zwykłego pojedynczego 12h.

Jeżeli końcowa niewykonalność emergency jest spowodowana wyłącznie brakiem checkboxa `24` u konkretnych możliwych pracowników, blocker może zawierać `SHIFT-24-01`. T013 później przetłumaczy go na język Panelu; T012 nie buduje nowej warstwy prezentacji.

`deviation_mapping.py` ma znać dokładnie:

- `SHIFT-24-01 -> DeviationCategory.PREFERENCE` — kwalifikacja/restriction pracownika analogiczna do DAY_ONLY/MEMBERSHIP;
- `SHIFT-24-PAIR-01 -> DeviationCategory.COVERAGE` — złamanie wymaganej struktury pokrycia normalnego 24h.

Nie zmieniać istniejących kategorii innych rules.

## SOFT / REPLAN

Emergency 24h jest capability drugiego przebiegu, nie nowym SOFT score. Jeżeli pierwszy przebieg ma pełne rozwiązanie, emergency nie może zastąpić go dlatego, że ma lepsze target/fairness.

W drugim przebiegu istniejący objective oraz REPLAN minimal reshuffle nadal działają wśród rozwiązań dopuszczonych rozszerzonym modelem.

Cross-month emergency nie daje prawa do mutowania boundary REALIZED/frozen/final facts. Zmianie podlega wyłącznie assignment state późniejszego planowanego miesiąca.

## TESTY C — MINIMUM

Testy C dopisywane są do wspólnego `tests/test_t012.py` utworzonego w A.

- first pass FEASIBLE => emergency path nie jest wołany/nie jest użyty;
- first pass infeasible, emergency D→N rescue => FEASIBLE;
- analogiczny N→D;
- same employee, shared work_period/rest provenance;
- can_work_24h=false na mixed profile nie rescue'uje;
- employee eligible tylko do jednej połowy nie pairuje;
- DAY_ONLY/N restriction nadal działa;
- INNY 8+16, 8+8+8, 16+8 nie tworzy emergency 24;
- three consecutive 12h nie tworzy overlapping chain >2;
- UNKNOWN first pass => TECHNICAL_ERROR bez emergency masking;
- second capped infeasible + uncapped emergency-enabled proves LOAD boundary;
- final DECISION_REQUIRED nie jest intermediate first-pass payload;
- normal catalog 24 działa już w first pass i nie jest liczone jako emergency;
- category_for_rule dla obu nowych codes zwraca dokładnie zamrożone kategorie;
- N 31.08 + D 01.09 może rescue'ować wrzesień jako cross-month emergency pair;
- analogicznie 31.12 + 01.01;
- wcześniejszy ScheduleVersion/Assignment pozostaje niezmieniony po utworzeniu pair;
- boundary demand snapshot, nie current profile mutation, decyduje o emergency rest;
- cross-month terminal component niesie 24h rest i REST po całym okresie używa tej wartości;
- już dwukomponentowy boundary work period nie może zostać przedłużony do trzeciej 12h;
- brak boundary demand/history => brak cross-month pair bez sztucznego warningu;
- full candidate validate HARD PASS;
- full suite + ROTA-REG-001 PASS.

## GATE C

Codex ma monkeypatch/fault-injection potwierdzić dokładną orkiestrację statusów oraz dwa real-persistence przypadki boundary: 31.08→01.09 i 31.12→01.01. Musi też potwierdzić, że poprzedni ScheduleVersion nie jest mutowany.

Wynik: `PASS — READY_FOR_IMPLEMENTATION_D`.

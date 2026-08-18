# ROTA-T012-C — HIDDEN EMERGENCY 24h RETRY

STATUS: BLOCKED UNTIL B PASS AND T012-R1-3 OWNER DECISION IS FROZEN
PARENT_CONTRACT: `tasks/ROTA-T012/brief.md`

## CEL

Dodać drugi, niewidoczny dla użytkownika przebieg CP-SAT, który może uratować pełny grafik przez potraktowanie dwóch bezpośrednio kolejnych zwykłych 12h jako jednego 24h work period uprawnionego pracownika.

Normalne katalogowe 24h z B nie jest „emergency” i istnieje już w pierwszym przebiegu.

## PART C SCOPE

- rota/application/deviation_mapping.py
- rota/planning/eligibility.py
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/validator.py
- rota/planning/engine.py
- rota/planning/work_periods.py
- tests/test_t012.py

Żaden inny plik w C.

## PAIR CANDIDATE

Awaryjna para istnieje tylko gdy:

- oba demandy są zwykłym `catalog_kind=12h`, nie normalnymi componentami katalogowego 24h;
- każdy trwa dokładnie 12h;
- `second.start_datetime == first.end_datetime`;
- shift_kind są przeciwne D↔N;
- first.emergency_24h_rest_hours jest jawnie snapshotowane i nie-None;
- employee może indywidualnie pokryć oba demandy według wszystkich HARD poza internal REST pomiędzy tymi dwoma;
- mixed profile: membership.can_work_24h=true;
- all-24 profile nie potrzebuje emergency pairingu, bo normalne 24h jest jedynym katalogiem; drugi pass nie ma tworzyć dodatkowej alternatywnej semantyki na takim profilu.

INNY nie jest pair candidate nawet jeśli dwie/trzy pozycje sumują się do 24h.

## T012-R1-3 — MONTH-BOUNDARY PRODUCT BLOCKER

Round 1 wykazał nierozstrzygniętą granicę produktu: powyższe „dwie bezpośrednio kolejne zwykłe 12h” nie określa, czy emergency pair może łączyć demand kończący jeden `ScheduleVersion.month` z demandem rozpoczynającym następny miesiąc, np. N 31.08 + D 01.09.

Do czasu jawnej decyzji właściciela NIE wolno implementować ani testować przypadkowej semantyki tej granicy. Po decyzji:

- `arch/spec.md` musi literalnie wskazać TAK/NIE;
- `arch/FROZEN.lock` musi zostać ponownie przeliczony;
- ten Part C musi opisać dokładną reprezentację;
- `tests/test_t012.py` musi zawierać jawny test 31→1 oraz 31.12→01.01 dla wybranej semantyki.

## CP-SAT, NIE WŁASNY SEARCH

Pairing musi być modelowany jako opcjonalne decyzje/constraints w CP-SAT. Nie wolno implementować własnego backtrackingu, permutacji ani zewnętrznego combinatorial search.

Model musi gwarantować:

- jeśli employee używa emergency pair, jest PRIMARY na obu demandach;
- oba Assignment dostają ten sam work_period_id i required_rest_after_hours = emergency_24h_rest_hours;
- demand nie może jednocześnie należeć do dwóch pairings w jednym solution;
- nie powstaje chain >2 poprzez D1+D2 oraz D2+D3;
- coverage nadal dokładnie required_primary_count;
- jeżeli required_primary_count >1, pairing jest per employee; nie wolno wymagać, by wszyscy PRIMARY na dwóch niezależnych zwykłych demandach byli identyczni, chyba że konkretny employee używa pairing option.

## ENGINE TWO-PASS CONTRACT

`plan()` zachowuje trzy public statuses i nie ujawnia próby numer 1/2.

Sekwencja:

1. capped solve `allow_emergency_24h=False`;
2. jeśli daje candidate → zwykła independent validation i normalny outcome; NIE uruchamiać emergency tylko po to, żeby znaleźć „lepszy” SOFT;
3. jeśli pierwszy solve ma PROVEN business INFEASIBLE/shortage/conflict, uruchomić capped solve `allow_emergency_24h=True`;
4. jeśli drugi daje candidate → validate i outcome;
5. jeśli drugi capped jest INFEASIBLE, diagnoza LOAD przez uncapped retry MUSI również mieć `allow_emergency_24h=True`;
6. UNKNOWN/MODEL_INVALID/technical status pierwszego lub drugiego przebiegu nie może być maskowany kolejną próbą jako zwykły DECISION_REQUIRED;
7. finalny DECISION_REQUIRED ma opisywać stan po wyczerpaniu legalnego emergency mechanism, nie intermediate blocker pierwszego przebiegu.

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
- po decyzji T012-R1-3: jawny month-boundary test 31→1 i year-boundary 31.12→01.01;
- full candidate validate HARD PASS;
- full suite + ROTA-REG-001 PASS.

## GATE C

Codex ma monkeypatch/fault-injection potwierdzić dokładną orkiestrację statusów, nie tylko happy-path roster.

Wynik: `PASS — READY_FOR_IMPLEMENTATION_D`.

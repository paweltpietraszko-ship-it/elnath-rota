# ROTA-T017 — multi-variant FEASIBLE planning

STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — ROUND 2 — NOT READY FOR CC
DATE: 2026-08-19
TASK_ID: ROTA-T017
BASE_SHA: d1a0ec0438718b1b7fd91e5c146e67b58c4eb4f9
BASE_BRANCH: main
TASK_BRANCH: task/ROTA-T017
OWNER_SOURCE: arch/T017_multi_variant_plan_architect_brief.md
FROZEN_ADDENDUM: arch/FROZEN_ADDENDUM_MULTI_VARIANT_PLAN_01.md
DEPENDS_ON: T006 + T012 + T013 + T018 merged on main
PREIMPLEMENTATION_ROUND_1: FAIL — T017-R1-1 legacy consumer scope + T017-R1-2 baseline sentence; SECTION_CHECK 2–8 remain CLOSED/PASS

## CEL

`PLAN` / `REPLAN` może zwrócić koordynatorowi do 3 pełnych poprawnych grafików do wyboru.

Każdy kolejny zwracany wariant musi być realnie odrębny o minimum 15% według kanonicznej metryki T017. Jeżeli kwalifikują się tylko 1 albo 2 warianty, wynik nadal jest poprawnym `FEASIBLE`.

T017 nie zmienia żadnego HARD, nie dodaje nowego fallbacku i nie wybiera wariantu za koordynatora.

## BASELINE — POST T013 / POST T018

Projekt powstaje na exact `main` SHA `d1a0ec0438718b1b7fd91e5c146e67b58c4eb4f9`.

Ta baza zawiera:
- T006 `REPLAN-MIN-01`;
- T012 emergency 24h;
- T018 workday absence + DAY_ONLY N fallback i literalną 4-stage retry order;
- T013 coordinator-facing final DECISION_REQUIRED guidance.

Na tej exact bazie `arch/spec.md` już literalnie dopuszcza 1–3 HARD-valid kandydatów i wybór koordynatora. T017 nie rozszerza tej decyzji produktowej; domyka mechanikę generowania wariantów, kanoniczną diversity 15%, pairwise semantics, optional-search statuses i warning association.

T017 ma zachować wszystkie wcześniejsze kontrakty bez redefinicji.

## OWNER DECISIONS — CLOSED

- maksymalnie 3 warianty;
- 1 albo 2 kwalifikujące się warianty = `FEASIBLE`, nie błąd;
- każdy wariant pełny i HARD-valid;
- minimum 15% realnej różnicy;
- koordynator wybiera wariant;
- techniczna metryka, rounding i compute budget należą do architekta.

## ARCHITECTURE CHOICE

Nie tworzyć drugiego solvera ani osobnego subsystemu candidate generation.

Rozszerzyć istniejący `rota/planning/solver.py` tak, aby po znalezieniu pierwszego legalnego rozwiązania w danym pass użył **tego samego CP-SAT modelu** z już zamrożonymi leksykograficznymi minimami i kolejno dodawał diversity cuts.

Pierwszy solve pozostaje dotychczasowym solve. Maksymalnie dwa kolejne solve szukają wariantu 2 i 3.

`rota/planning/engine.py` pozostaje ownerem publicznego `PlanningResult`: składa pełne Assignments, niezależnie waliduje każdy kandydat i zwraca 1–3 elementy `PlanningResult.candidates`.

Nie zmieniać `PlanningResult.candidates` typu ani `select_candidate(...)` publicznej sygnatury.

### Internal SolverOutcome transport

Dozwolone jest kompatybilne dopisanie na końcu internal `SolverOutcome` jednego defaultowanego pola transportującego dodatkowe solved candidates wraz z ich solver warnings, np.:

`alternatives: list[tuple[list[Assignment], list[str]]] = field(default_factory=list)`

albo równoważny minimalny kształt.

Warunki:
- istniejące `.assignments` i `.warnings` nadal oznaczają pierwszy kandydat;
- dotychczasowe positional constructions SolverOutcome nie mogą zostać złamane;
- nie tworzyć publicznego DTO ani persistence modelu.

## TASK_SCOPE

TASK_SCOPE:
- arch/T017_multi_variant_plan_architect_brief.md
- arch/FROZEN_ADDENDUM_MULTI_VARIANT_PLAN_01.md
- tasks/ROTA-T017/brief.md
- rota/planning/solver.py
- rota/planning/engine.py
- benchmarks/real_object.py
- benchmarks/manual_audits.py
- tests/test_real_object_benchmark.py
- tests/test_t018.py
- tests/test_t017.py

Żaden inny plik bez STOP + amendment architekta po preimplementation enumeration albo konkretnym implementacyjnym blockerze.

## EXPLICITLY OUT OF SCOPE

Nie zmieniać bez osobnego amendmentu:
- arch/spec.md;
- arch/FROZEN.lock;
- rota/domain.py;
- rota/planning/engine_types.py;
- rota/planning/validator.py;
- rota/planning/eligibility.py;
- rota/planning/site_rules.py;
- rota/planning/constraints.py;
- rota/planning/replan_reshuffle.py;
- rota/planning/decision_guidance.py;
- rota/application/*;
- rota/persistence/*;
- persistence schema.

W szczególności `select_candidate(...)` już przyjmuje konkretny candidate i nie wymaga przebudowy.

Jeżeli implementacja naprawdę wymaga zmiany któregokolwiek z tych plików, STOP przed edycją i wrócić do architekta z konkretnym dowodem.

## NEW_FILES

Dozwolone nowe pliki:
- `arch/FROZEN_ADDENDUM_MULTI_VARIANT_PLAN_01.md`;
- `tasks/ROTA-T017/brief.md`;
- `tests/test_t017.py`.

Nie tworzyć nowego production module, Candidate DTO, candidate repository ani persisted candidate table.

## A. CANONICAL DIVERSITY METRIC

Korzystać dokładnie z frozen addendum.

### A1. Denominator

Po `_build_slots(...)` istniejący solver ma `still_needed`.

`N = sum(still_needed.values())`

N to liczba solver-controlled PRIMARY coverage placements, które ten pass rzeczywiście rozstrzyga.

Nie używać:
- liczby Assignment rows całego kandydata;
- liczby employees;
- liczby dni;
- sumy godzin;
- technicznych IDs.

### A2. Candidate signature

`S(C) = set((demand_id, employee_id) dla selected x == 1)`

Pełny legalny candidate ma `|S(C)| == N`.

### A3. Distance

`distance(A,B) = N - |S(A) ∩ S(B)|`

Substitution employee na jednym demandzie = 1 changed placement.

### A4. Threshold

Dla `N > 0`:

`K = ceil(15*N/100) = (15*N + 99) // 100`

Dla `N == 0`: nie generować wariantu 2/3; zwrócić najwyżej jeden FEASIBLE candidate.

### A5. Pairwise requirement

Każdy nowy candidate musi mieć `distance >= K` względem **każdego** wcześniejszego zwróconego candidate.

Candidate 3 nie może być >=15% od candidate 2, ale <15% od candidate 1.

## B. EXACT DIVERSITY CUT

Po candidate `Ci` dodać cut równoważny:

`sum(x[e,d] for (d,e) in S(Ci)) <= N - K`

Dla candidate 3 model ma dwa cuts: względem candidate 1 i candidate 2.

Nie używać random seed, losowania, perturbacji objective ani technicznego Assignment ID jako diversity mechanism.

Jeżeli `N-K < 0` albo konstrukcyjnie próg nie może być osiągnięty, stop z istniejącą listą; to nie jest błąd.

## C. FIRST CANDIDATE REGRESSION LOCK

Pierwszy candidate nie widzi żadnego diversity cut.

Dla tego samego PlanningState i successful capability context jego placements mają być identyczne z pre-T017 wynikiem.

Existing deterministic settings pozostają:
- `num_search_workers = 1`;
- `random_seed = 0`;
- existing objective weights;
- existing status semantics.

Nie „ustawiać” pierwszego kandydata pod przyszłe warianty.

## D. LEXICOGRAPHIC MINIMA ARE FROZEN ACROSS CANDIDATES

Nie przebudowywać REPLAN-MIN-01 ani T018 B5.

Istniejąca `_solve_lexicographic_phases(...)` najpierw PROVEN OPTIMAL minimalizuje fazy i dodaje equality constraints.

Dopiero potem ordinary `_add_objective(...)` i pierwszy final solve.

Diversity search 2/3 odbywa się na **tym samym modelu po tych equality constraints**.

Każdy wariant ma więc dokładnie te same globalne minimum:
- reshuffle count, gdy REPLAN baseline istnieje;
- exceptional_n_count, gdy DAY_ONLY fallback jest aktywny.

Nie przeliczać minimum osobno po diversity cut, bo mogłoby to dopuścić większy reshuffle/exceptional N w zawężonej przestrzeni.

## E. T018 STAGE FREEZE

Engine stage order zostaje literalnie bez zmian.

Warianty powstają tylko w pierwszym stage, który ma solver candidate.

Przykłady wiążące:
- Stage 1 FEASIBLE + tylko 1 diverse candidate -> wynik FEASIBLE z 1; **nie** Stage 2;
- Stage 2 first FEASIBLE -> variants tylko przy `allow_day_only_n_fallback=True`, emergency OFF;
- Stage 3 first FEASIBLE -> variants przy obu capability ON; **nie** Stage 4 dla samej różnorodności;
- Stage 4 pozostaje DECISION_REQUIRED LOAD diagnosis, nie candidate source.

Dodatkowe warianty nigdy nie są powodem użycia bardziej wyjątkowego fallbacku.

## F. ADDITIONAL SOLVE STATUS

Po pierwszym candidate maksymalnie 2 optional final-objective solves.

Dla optional solve:
- OPTIMAL / FEASIBLE -> wyciągnąć candidate + solver warnings;
- INFEASIBLE -> stop, return accumulated 1/2;
- UNKNOWN / MODEL_INVALID / inny technical -> zwrócić technical SolverOutcome tak, aby publiczny result był TECHNICAL_ERROR z `candidates=[]`.

Nie traktować UNKNOWN jako dowodu „istnieją tylko 1–2”.

Nie tworzyć conflicting_demand_ids/DECISION_REQUIRED z INFEASIBLE wynikającego wyłącznie z diversity cuts.

## G. COMPUTE BUDGET

Każdy optional solve używa existing `SOLVER_TIME_LIMIT_SECONDS`.

Maksymalny dodatkowy budżet po first candidate = dwa takie final-objective solve.

Nie uruchamiać ponownie lexicographic phase solves dla wariantów 2/3.

Nie uruchamiać variant solves, jeśli initial stage outcome nie ma `.assignments`.

## H. INDEPENDENT VALIDATION / ENGINE

Engine buduje `full = fixed_existing_assignments(state) + solved` dla każdego candidate, dokładnie jak dziś dla pierwszego.

Każdy candidate przechodzi osobny `validate(state, full)`.

### H1. First candidate

Jeżeli first candidate nie ma HARD PASS, zachować istniejącą `_evaluate_candidate` klasyfikację:
- known frozen/load autonomy boundary -> istniejący DECISION_REQUIRED;
- unexplained solver/validator mismatch -> TECHNICAL_ERROR.

W takim wyniku nie publikować żadnych variants.

### H2. Additional candidate

Jeżeli first candidate ma HARD PASS, ale candidate 2/3 nie ma HARD PASS:
- cały publiczny result = TECHNICAL_ERROR;
- `candidates=[]`;
- nie silent-drop wadliwego candidate;
- nie zwracać wcześniejszych jako częściowego FEASIBLE.

To zachowuje anti-drift rule 12.

## I. FEASIBLE RESULT SHAPE

Po wszystkich validation PASS:
- status = FEASIBLE;
- candidates = ordered list 1..min(3, found);
- decision_payload = None;
- error_message = None.

Kolejność kandydatów = kolejność generation:
1. pre-T017 first result;
2. best found under cut vs 1;
3. best found under cuts vs 1+2.

Nie sortować final list po employee ID / Assignment ID.

## J. WARNINGS WITHOUT NEW DTO

Nie zmieniać `PlanningResult` schema.

Dla jednego candidate:
- warnings = exact legacy `outcome.warnings + report.warnings` bez prefixu.

Dla 2–3 candidates:
- zebrać warnings osobno per candidate;
- każdy warning prefixować dokładnie:
  `candidate=<1-based-number> | `;
- następnie dołączyć istniejący warning body bez zmiany jego obowiązkowych pól.

Przykład T018 (ROTA-T055 R2-01, OWNER 2026-09-04: treść po dwukropku
przepisana na polski z zacytowanym employee_id -- prefiks
`candidate=N | RULE-CODE SOFT:` bez zmian):
`candidate=2 | DAY_ONLY-N-FALLBACK-01 SOFT: 'A' ma nockę mimo dnia wolnego dzięki wyjątkowi zmianowemu (zapotrzebowanie D-N, data 2027-03-17, reguła RV-1)`

Nie deduplikować warningów pomiędzy candidate 1/2/3.

Single-candidate output musi zachować stare warning oracles bez zmian.

## K. APPLICATION / PERSISTENCE NON-CHANGE

Nie zmieniać `plan_ops.select_candidate`.

Każdy returned candidate ma ten sam schedule_version_id context i może być przekazany jako istniejący `list[Assignment]`.

Wymagany integration oracle wybiera nie pierwszy, tylko candidate 2, zapisuje go istniejącą operacją, zamyka/reopen store i potwierdza, że persisted current schedule odpowiada dokładnie wybranemu candidate.

Niewybrane candidates nie są persistowane.

## L. T013 NON-REGRESSION

T017 nie dotyka `decision_guidance.py`.

DECISION_REQUIRED pozostaje dokładnie obecnym T013 outputem i zawsze ma `candidates=[]`.

Brak dodatkowego wariantu przy FEASIBLE nie generuje żadnego T013 message ani unblocking option.

## M. TESTS — MINIMUM T017 MATRIX

`tests/test_t017.py` minimum:
1. >=3 legal pairwise-diverse -> exactly 3;
2. only 1 -> FEASIBLE + len=1;
3. only 2 -> FEASIBLE + len=2;
4. N=20 -> K=3 exact boundary;
5. N=7 -> K=2;
6. N=6 -> K=1;
7. one employee substitution on one demand counts 1;
8. assignment_id-only change does not count;
9. list ordering does not count;
10. work_period/provenance-only difference does not count;
11. TRAINEE/CANCELLED/fixed facts absent from signature;
12. candidate 3 pairwise threshold against candidate 1 and 2;
13. first candidate identical to pre-T017 placement oracle;
14. REPLAN all returned candidates preserve same minimum reshuffle;
15. DAY_ONLY fallback all returned candidates preserve same minimum exceptional_n_count;
16. TARGET/fairness cannot increase reshuffle/exception count for diversity;
17. Stage1 FEASIBLE/one candidate -> no Stage2;
18. Stage2 first FEASIBLE -> no emergency just for variants;
19. Stage3 first FEASIBLE -> no uncapped just for variants;
20. optional INFEASIBLE after candidate1 -> FEASIBLE len1;
21. optional INFEASIBLE after candidate2 -> FEASIBLE len2;
22. optional UNKNOWN -> TECHNICAL_ERROR candidates=[];
23. optional MODEL_INVALID -> TECHNICAL_ERROR candidates=[];
24. every returned candidate validator HARD PASS;
25. injected validator failure on candidate2 -> TECHNICAL_ERROR candidates=[];
26. multi warning candidate prefixes and stable order;
27. single candidate warning bit-for-bit legacy;
28. T018 DAY_ONLY warning mandatory body preserved under candidate prefix;
29. select candidate2 real persistence/reopen roundtrip;
30. DECISION_REQUIRED unchanged/candidates empty;
31. TECHNICAL_ERROR unchanged/candidates empty;
32. repeated same input -> same ordered candidate placement signatures;
33. ROTA-REG-001 first candidate/outcome non-regression;
34. March 2027 owner probe first candidate/outcome non-regression.

## N. LEGACY TEST ENUMERATION — PREIMPLEMENTATION REQUIRED

T017 może zmienić liczbę solver `_run_solver` calls po FEASIBLE i liczbę publicznych `PlanningResult.candidates`. Może też zmienić warning string tylko w multi-candidate FEASIBLE.

Przed CC Codex musi mechanicznie przeskanować istniejące testy i konsumentów i wyliczyć każdy legacy plik wymagający zmiany wyłącznie dlatego, że:
- asercja wymaga `len(candidates) == 1` albo exact one-candidate list;
- consumer odrzuca legalne `FEASIBLE` z 2–3 kandydatami;
- test zakłada dokładną liczbę `_run_solver` wywołań po first FEASIBLE;
- fake/mock musi tolerować appended default `SolverOutcome` alternatives transport;
- exact FEASIBLE warning assertion może wejść w multi-candidate path;
- integration test wybiera zawsze `[0]` i jego oracle powinien pozostać świadomie first-candidate-only.

Required output:
- exact file list;
- exact affected tests/assertions;
- classification: mechanical multi-candidate expectation vs real semantic conflict.

Architect nie autoryzuje broad rewrites z góry.

Jeżeli jakikolwiek plik poza literalnym TASK_SCOPE wymaga edycji, STOP + architect amendment before edit.

## N1. ROUND 1 AMENDMENT — T017-R1-1 / T017-R1-2

Round 1 Codex audit na exact contract SHA `477180914603c4a8ce247034f47522445ebbe10c` znalazł dokładnie dwa mechaniczne findings kontraktowe:
- `T017-R1-1`: cztery legacy consumer/test files poza TASK_SCOPE;
- `T017-R1-2`: jedna nieprawdziwa baseline sentence w owner source.

SECTION_CHECK 2–8 Round 1 pozostają PASS/CLOSED i nie są ponownie otwierane przez ten amendment.

### N1.1 T017-R1-1 — dokładnie cztery dodatkowe pliki

Literalny TASK_SCOPE obejmuje teraz dokładnie:

1. `benchmarks/real_object.py`
   - `_feasible_errors`: mechanicznie zaakceptować legalne `FEASIBLE` z `1 <= len(candidates) <= 3` zamiast wymagać dokładnie 1;
   - `_decision_errors`: false-FEASIBLE diagnostic ma działać dla legalnej kardynalności 1–3;
   - zachować dotychczasowy first-candidate ground-truth/checker oracle; nie zmieniać scenariusza benchmarku ani kryterium poprawności pierwszego kandydata.

2. `tests/test_real_object_benchmark.py`
   - tylko `_clean_candidate` i bezpośrednie cardinality expectation zależne od dokładnie jednego kandydata;
   - zaakceptować 1–3, ale zwracany/sprawdzany `candidates[0]` nadal zamraża dotychczasowy pre-T017 first-candidate oracle;
   - żadnych zmian scenariusza ani ground truth.

3. `benchmarks/manual_audits.py`
   - `verify_feasible_month`: legalne 1–3 candidates nie mogą być FAIL tylko z powodu cardinality;
   - zachować dotychczasową ręczną kontrolę pierwszego kandydata;
   - nie rozszerzać ani nie osłabiać innych manual-audit checks.

4. `tests/test_t018.py`
   - tylko `test_b10_4_5_global_minimum_exceptional_n_not_inflated_for_fairness` oraz jego bezpośrednie helper/assertion expectations wymagające multi-candidate warning association;
   - test ma nadal dowodzić `exceptional_n_count == 1` **dla każdego** zwróconego candidate;
   - first-candidate placement oracle pozostaje niezmieniony;
   - przy 2–3 candidates obowiązuje T017 `candidate=N | ` warning prefix, ale body `DAY_ONLY-N-FALLBACK-01` zachowuje code/employee/demand/date/rule_version_id;
   - nie zmieniać T018 fallback order, minimum, exception legality ani innych testów w tym pliku.

### N1.2 Explicitly not opened

Ten amendment NIE autoryzuje:
- żadnej zmiany statusów produktu;
- zmiany metryki 15%, pairwise rule, diversity cut, first-candidate lock ani solver design;
- zmiany T006 REPLAN minimum;
- zmiany T018 fallback order lub exceptional-N minimum;
- zmiany T012 emergency 24h;
- zmiany T013 DECISION_REQUIRED communication;
- zmian benchmark scenarios/fixtures/ground truth poza mechaniczną akceptacją legalnej kardynalności 1–3;
- zmian w 28 legacy test files, które czytają `candidates[0]` i pozostają poprawnymi first-candidate oracles;
- zmian `tasks/ROTA-T012/scenarios/t012_owner_march_2027_probe.py` ani `benchmarks/rota_stress.py`;
- jakiegokolwiek piątego legacy consumer/test file.

Każdy piąty plik znaleziony podczas implementacji = STOP + architect amendment przed edycją.

### N1.3 T017-R1-2 — baseline correction only

`arch/T017_multi_variant_plan_architect_brief.md` został skorygowany wyłącznie w opisie źródła autoryzacji:
- na exact BASE_SHA `d1a0ec0438718b1b7fd91e5c146e67b58c4eb4f9` `arch/spec.md` już literalnie dopuszcza 1–3 HARD-valid kandydatów i wybór koordynatora;
- T017 domyka implementacyjną lukę generowania, kanoniczny próg 15%, pairwise semantics, optional-search statuses i warning association;
- nie zmieniać `arch/spec.md` ani `arch/FROZEN.lock`.

## O. PREIMPLEMENTATION CODEX AUDIT

Round 1 zamknął SECTION_CHECK 2–8. Round 2 jest deliberately narrow i sprawdza wyłącznie T017-R1-1 / T017-R1-2 oraz exact diff amendmentu.

### O1. ROUND 2 — NARROW AUDIT ONLY

Codex sprawdza:
1. czy TASK_SCOPE zawiera dokładnie cztery nowe pliki z N1.1;
2. czy dozwolone zmiany w tych plikach są wyłącznie mechaniczną obsługą legalnej kardynalności/warning association;
3. czy benchmark/test first-candidate ground truth pozostaje nienaruszony;
4. czy `tests/test_t018.py` nadal dowodzi exceptional_n minimum per candidate i zachowuje first-candidate placement oracle;
5. czy żaden piąty legacy plik nie został otwarty;
6. czy owner source poprawnie opisuje actual `arch/spec.md` baseline na `d1a0ec...`;
7. czy `arch/spec.md` i `arch/FROZEN.lock` pozostają nietknięte;
8. czy amendment zawiera tylko dokumentację, bez implementation/test changes;
9. czy SECTION_CHECK 2–8 Round 1 pozostają CLOSED/PASS.

Required Round 2 verdict:
`PASS — READY_FOR_IMPLEMENTATION`.

Do tego exact PASS:
**CC MUST NOT START T017 IMPLEMENTATION.**

## P. FINAL IMPLEMENTATION GATE

Po implementacji Codex audytuje exact PRODUCT SHA i pełny BASE_SHA -> HEAD diff.

Wymagane:
- T017 dedicated matrix PASS;
- wszystkie autoryzowane legacy adaptations PASS;
- full `tests/` PASS;
- REPLAN-MIN-01 regressions PASS;
- T018 4-stage + DAY_ONLY warning/minimum regressions PASS;
- T012 emergency regressions PASS;
- T013 DECISION_REQUIRED regressions PASS;
- ROTA-REG-001 PASS;
- owner March 2027 probe PASS;
- Ruff PASS;
- `python guard.py check arch/spec.md` PASS;
- `git diff --check` PASS;
- `arch/spec.md` i `arch/FROZEN.lock` unchanged;
- backend.py literal TASK_SCOPE;
- każdy SIZE_FILE/SIZE_FUNC/RATIO/TOTAL_LINES `WYMAGA_DECYZJI` wraca do architekta z exact PRODUCT SHA.

Dopiero po Codex PASS i finalnej akceptacji architekta:
`ARCHITECT FINAL GATE ACCEPTANCE — ROTA-T017: PASS — READY FOR MERGE`.

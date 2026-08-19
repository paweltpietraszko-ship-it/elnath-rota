# FROZEN PRODUCT CONTRACT ADDENDUM — MULTI-VARIANT-PLAN-01

ADDENDUM_ID: MULTI-VARIANT-PLAN-01
DATE: 2026-08-19
STATUS: FROZEN_PRODUCT_CONTRACT_ADDENDUM
BASE_SHA: d1a0ec0438718b1b7fd91e5c146e67b58c4eb4f9
OWNER_DECISION_SOURCE: arch/T017_multi_variant_plan_architect_brief.md
DEPENDS_ON: T006 + T012 + T013 + T018 merged on main

## SUPERSESSION — EXACT SCOPE

Ten addendum zmienia wyłącznie dotychczasową kardynalność poprawnego wyniku `FEASIBLE`:
- przed T017 engine zwracał dokładnie 1 element `PlanningResult.candidates`;
- po T017 może zwrócić 1, 2 albo 3 pełne kandydaty.

Nie zmienia publicznych statusów `FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR`.

Nie zmienia `DecisionRequiredPayload`, T013 coordinator guidance, persistence schema, lifecycle, SiteRule, availability, HARD/SOFT, target_hours ani definicji poprawności pojedynczego grafiku.

`PlanningResult.candidates` pozostaje istniejącą `list[list[Assignment]]`; nie tworzyć nowego publicznego Candidate DTO tylko po to, aby przenieść kilka list Assignment.

## OWNER DECISION

1. Maksymalna liczba zwracanych wariantów = **3**.
2. Każdy zwracany wariant jest kompletnym grafikiem i niezależnie spełnia HARD.
3. Każdy kolejny zwracany wariant musi być co najmniej **15%** różny w rzeczywistej obsadzie według kanonicznej metryki tego addendum.
4. Jeżeli kwalifikują się tylko 1 albo 2 warianty, wynik pozostaje `FEASIBLE` z odpowiednio 1 albo 2 elementami `candidates`.
5. Sam brak drugiego/trzeciego wariantu nigdy nie tworzy `DECISION_REQUIRED` ani `TECHNICAL_ERROR`.
6. Koordynator wybiera konkretny wariant; program nie wybiera za niego.

## CANONICAL DIVERSITY UNIT

T017 porównuje wyłącznie **solver-controlled PRIMARY coverage placements** bieżącego planowania.

Dla successful pass solver już posiada `still_needed[demand_id]`: liczbę PRIMARY placements tego demandu, które nie są zaspokojone zachowanymi/fixed faktami i są rzeczywiście decyzją CP-SAT w tym runie.

Kanoniczny mianownik:

`N = sum(still_needed.values())`

To oznacza:
- świeży PLAN bez fixed coverage: N jest sumą wymaganych PRIMARY positions wszystkich demandów;
- REPLAN/frozen/REALIZED/manual fixed facts, których solver nie może zmienić, nie zwiększają mianownika różnorodności;
- redistributable baseline placements REPLAN są ponownie decyzją solvera, więc wchodzą do N;
- TRAINEE nie jest PRIMARY coverage i nie wchodzi do N;
- CANCELLED nie jest pracą i nie wchodzi do N.

Dla jednego kandydata `C` jego solver-controlled signature:

`S(C) = {(demand_id, employee_id) | odpowiadająca zmienna x[employee_id, demand_id] == 1}`

Dla pełnego legalnego rozwiązania `|S(C)| == N`.

Nie wchodzą do signature:
- `assignment_id`;
- kolejność Assignment w liście;
- `schedule_version_id`;
- `work_period_id` i inne techniczne provenance, jeżeli obsada employee/demand się nie zmieniła;
- TRAINEE;
- CANCELLED;
- fixed facts, które są identyczne dla wszystkich wariantów tego samego runu.

## DISTANCE / 15% / ROUNDING

Dla dwóch kandydatów A i B:

`changed_placements(A,B) = N - |S(A) ∩ S(B)|`

Jedna substytucja employee na jednym demandzie liczy się jako **1 zmieniona placement**, nie 2. Usunięty `(demand,A)` i dodany `(demand,B)` są jednym faktycznym przestawieniem obsady tego demandu.

Minimalny wymagany dystans dla `N > 0`:

`K = ceil(0.15 * N)`

Implementacyjnie bez float:

`K = (15 * N + 99) // 100`

Każdy nowy kandydat musi spełniać:

`changed_placements(new, previous) >= K`

względem **każdego** wcześniej zwróconego kandydata, nie tylko bezpośrednio poprzedniego.

Jeżeli `N == 0`, nie istnieje realna solver-controlled placement, na której można zbudować różny wariant; zwracany jest najwyżej 1 kandydat.

## CP-SAT DIVERSITY CUT — EXACT SEMANTICS

Po uzyskaniu kandydata `Ci` dodać dla jego selected signature cut równoważny:

`sum(x[e,d] for (d,e) in S(Ci)) <= N - K`

Każdy kolejny solve ma jednocześnie cut dla każdego wcześniejszego kandydata.

Jeżeli RHS staje się ujemny albo konstrukcyjnie wiadomo, że próg jest nieosiągalny, nie uruchamiać sztucznego kolejnego solve; obecna lista 1–2 kandydatów jest poprawnym wynikiem FEASIBLE.

Diversity cut jest HARD-em wyłącznie wewnątrz poszukiwania kolejnego wariantu; nie staje się regułą domenową, SiteRule ani persisted constraint.

## FIRST CANDIDATE MUST NOT DRIFT

Kandydat nr 1 musi być dokładnie tym samym rozwiązaniem, które pre-T017 istniejący solver zwróciłby dla tego samego state i tego samego successful T018 pass.

Nie wolno:
- dodać diversity do objective pierwszego kandydata;
- losować pierwszego kandydata;
- przestawić istniejących priorytetów SOFT;
- wybrać gorszego pierwszego kandydata po to, aby później łatwiej znaleźć 3 warianty.

Dopiero po uzyskaniu pierwszego kandydata powstają diversity cuts.

## FROZEN LEXICOGRAPHIC PRIORITIES APPLY TO EVERY VARIANT

T017 nie może kupić różnorodności pogorszeniem wcześniej zamrożonych minimów.

W successful pass model najpierw zachowuje istniejące fazy:

REPLAN, gdy baseline istnieje:
1. minimum reshuffle — PROVEN OPTIMAL;
2. przy zamrożonym reshuffle, gdy DAY_ONLY fallback jest aktywny: minimum `exceptional_n_count` — PROVEN OPTIMAL;
3. zwykły TARGET/fairness/pozostałe SOFT.

PLAN bez REPLAN baseline:
1. gdy DAY_ONLY fallback jest aktywny: minimum `exceptional_n_count` — PROVEN OPTIMAL;
2. zwykły TARGET/fairness/pozostałe SOFT.

Po wyznaczeniu wartości faz leksykograficznych model ma już equality constraints zamrażające te minima. **Te same equality constraints pozostają w modelu dla wariantów 2 i 3.**

Wariant 2/3 nie może mieć większego reshuffle albo większej liczby exceptional N tylko po to, aby osiągnąć 15%.

Zwykły SOFT objective pozostaje objective również przy kolejnych solve. Wariant 2/3 może mieć gorszy zwykły SOFT score od wcześniejszego, jeżeli jest najlepszym znalezionym rozwiązaniem w przestrzeni spełniającej dotychczasowe diversity cuts; nie wymagamy równego SOFT score.

## T018 FALLBACK STAGE IS FROZEN BY FIRST FEASIBLE

Literalna kolejność T018 pozostaje:
1. NORMAL capped;
2. DAY_ONLY fallback capped;
3. DAY_ONLY + emergency 24h capped;
4. uncapped LOAD diagnosis.

Jeżeli Stage 1 daje poprawny kandydat, warianty 2/3 są szukane wyłącznie w Stage 1 capability context. Nie wolno uruchomić Stage 2 tylko dlatego, że Stage 1 ma mniej niż 3 różnorodne warianty.

Analogicznie:
- jeżeli pierwszym FEASIBLE jest Stage 2, wszystkie warianty należą do Stage 2 i zachowują globalne minimum exceptional N;
- jeżeli pierwszym FEASIBLE jest Stage 3, wszystkie warianty należą do Stage 3;
- Stage 4 jest diagnozą LOAD/DECISION_REQUIRED i nie produkuje wariantów FEASIBLE.

Brak drugiego/trzeciego wariantu nigdy nie jest dowodem do uruchomienia bardziej wyjątkowego fallbacku.

## OPTIONAL VARIANT SEARCH STATUS

Pierwszy kandydat zachowuje dotychczasową semantykę solver status.

Dla poszukiwania wariantu 2/3:
- `OPTIMAL` albo `FEASIBLE` -> legalny znaleziony kandydat, następnie independent validation;
- `INFEASIBLE` po diversity cuts -> dowód, że w tej przestrzeni nie istnieje kolejny kwalifikujący wariant; zwrócić dotychczasowe 1/2 jako FEASIBLE;
- `UNKNOWN`, `MODEL_INVALID` albo inny techniczny status -> `TECHNICAL_ERROR`; nie maskować problemu jako „po prostu nie ma więcej wariantów”.

T017 nie osłabia istniejącej zasady fail-closed dla statusów technicznych.

## COMPUTE BUDGET

Maksymalnie dwa dodatkowe final-objective solve po znalezieniu pierwszego kandydata, ponieważ limit wyniku to 3.

Każdy dodatkowy solve używa istniejącego `SOLVER_TIME_LIMIT_SECONDS` i istniejących deterministycznych ustawień solvera.

Nie uruchamiać ponownie faz minimum reshuffle/exceptional N dla każdego wariantu; ich udowodnione minima są już zamrożone equality constraints w tym samym modelu.

Nie uruchamiać dodatkowych variant solves na stage, który nie znalazł pierwszego kandydata.

## INDEPENDENT VALIDATION OF EVERY RETURNED CANDIDATE

Każdy kandydat zwrócony w `PlanningResult.candidates` musi zostać niezależnie sprawdzony przez istniejący `validate(state, candidate)`.

Jeżeli pierwszy kandydat nie przechodzi validatora, zachować dokładnie istniejącą klasyfikację engine (known autonomy boundary vs TECHNICAL_ERROR).

Jeżeli pierwszy kandydat przechodzi HARD, ale którykolwiek dodatkowy kandydat nie przechodzi independent HARD validation, cały wynik jest `TECHNICAL_ERROR`; nie wolno po cichu wyrzucić wadliwego wariantu i zwrócić wcześniejszych jako rzekomo pełny sukces T017.

`DECISION_REQUIRED` i `TECHNICAL_ERROR` nadal mają `candidates=[]`.

## WARNINGS / CANDIDATE ASSOCIATION WITHOUT NEW DTO

T017 nie dodaje nowego publicznego Candidate DTO ani persistence dla warningów.

Dla dokładnie 1 zwróconego kandydata `PlanningResult.warnings` pozostaje bit-for-bit w dotychczasowym kształcie.

Dla 2–3 kandydatów każdy solver/validator warning musi być przypisany do konkretnego numeru kandydata w istniejącym `PlanningResult.warnings` przez stabilny techniczny prefix:

`candidate=<1-based-number> | <existing warning body>`

Kolejność warningów: candidate 1, potem 2, potem 3; wewnątrz kandydata dotychczasowa deterministyczna kolejność.

Nie deduplikować warningu pomiędzy kandydatami: ten sam warning występujący w dwóch wariantach jest dwoma przypisanymi faktami.

T018 `DAY_ONLY-N-FALLBACK-01` zachowuje obowiązkowe code/employee/demand/date/rule_version_id w body; prefix jest wyłącznie technicznym skojarzeniem warningu z elementem `PlanningResult.candidates`.

Po `select_candidate` trwała provenance nadal opiera się na istniejących Assignment/ShiftDemand/applied_rule_version_ids; T017 nie dodaje persisted candidate id.

## APPLICATION / SELECTION

`rota/application/plan_ops.select_candidate(...)` pozostaje bez zmiany publicznej sygnatury: koordynator przekazuje dokładnie jeden wybrany `list[Assignment]` z `PlanningResult.candidates`.

Każdy z 1–3 kandydatów musi być legalnie wybieralny i przejść istniejący re-validation/persistence path.

Nie auto-save pierwszego wariantu. Nie auto-select. Nie zapisuj niewybranych wariantów.

## DETERMINISM

Przy identycznym PlanningState, tych samych danych i tym samym solver status path lista kandydatów ma być deterministyczna:
- kandydat 1 jest dotychczasowym deterministic result;
- kandydat 2 powstaje po cut względem 1;
- kandydat 3 po cuts względem 1 i 2;
- nie sortować kandydatów po technicznych Assignment IDs;
- nie używać random seed do wymuszania różnicy.

## REQUIRED ORACLES

Minimum:
1. gdy istnieją >=3 pairwise-diverse rozwiązania -> FEASIBLE z dokładnie 3;
2. gdy istnieje tylko 1 -> FEASIBLE z 1, bez DR/TE;
3. gdy istnieją tylko 2 -> FEASIBLE z 2, bez DR/TE;
4. `N=20` -> K=3; 2 zmiany nie wystarczają, 3 wystarczają;
5. mały N: `N=7` -> K=2; `N=6` -> K=1;
6. jedna substytucja employee na jednym demandzie liczy 1;
7. Assignment ID/order/provenance-only zmiany nie tworzą diversity;
8. TRAINEE/CANCELLED/fixed facts nie tworzą signature;
9. candidate 3 musi przejść 15% względem candidate 1 i 2;
10. candidate 1 identyczny z pre-T017 oracle;
11. diversity cut nie zmienia minimum REPLAN reshuffle;
12. diversity cut nie zwiększa minimum exceptional N;
13. Stage 1 FEASIBLE z tylko 1 wariantem -> Stage 2 nie jest wywoływany;
14. Stage 2 first FEASIBLE -> wszystkie warianty z tym samym minimum exceptional N;
15. Stage 3 first FEASIBLE -> warianty nie uruchamiają Stage 4;
16. optional INFEASIBLE -> zwróć dotychczasowe 1/2 FEASIBLE;
17. optional UNKNOWN/MODEL_INVALID -> TECHNICAL_ERROR;
18. każdy zwrócony candidate independent HARD PASS;
19. injected additional-candidate validator failure -> TECHNICAL_ERROR, nie silent drop;
20. multi-candidate warnings mają poprawny candidate prefix i T018 provenance body;
21. single-candidate warnings pozostają legacy-identical;
22. można wybrać candidate 2 przez real `select_candidate`, restart/reassemble zachowuje wybrany grafik;
23. DECISION_REQUIRED/TECHNICAL_ERROR nadal candidates=[];
24. ROTA-REG-001 i marcowy T018 probe zachowują dotychczasowy pierwszy candidate/outcome.

## OUT OF SCOPE

T017 nie tworzy UI, historii odrzuconych kandydatów, „pokaż następne 3”, losowania, persisted candidate table, ranking API ani automatycznej decyzji koordynatora.

Nie zmienia `arch/spec.md` ani `arch/FROZEN.lock`; ten późniejszy addendum superseduje wyłącznie opisaną kardynalność FEASIBLE i zasady generowania dodatkowych wariantów.

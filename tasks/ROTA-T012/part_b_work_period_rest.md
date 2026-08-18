# ROTA-T012-B — WORK PERIOD + DIRECTIONAL REST + NORMAL CATALOG 24h

STATUS: READY FOR IMPLEMENTATION B
PARENT_CONTRACT: `tasks/ROTA-T012/brief.md`
A_PRODUCT_SHA: `326b52c5b137d150fd765b2a65f07149a6ad5639`
A_AUDIT: merytoryczny PASS; 591/591; Ruff/guard/diff-check PASS
A_ARCHITECT_GATE: `RATIO 11.6:1` ACCEPTED; `TOTAL_LINES 1008` ACCEPTED
OWNER_DECISION_OPEN: no

## CEL

Zamienić dane dostarczone przez T012-A w wykonywalną semantykę czasu pracy:

- `REST-01` przestaje używać globalnego 11 h dla bieżących T012 danych;
- solver i independent validator liczą odpoczynek między faktycznymi work periods;
- normalne katalogowe `24h` jest jednym work period złożonym z dwóch 12h komponentów tego samego PRIMARY;
- mixed profile egzekwuje `SiteMembership.can_work_24h`; all-24h profile ignoruje tę flagę;
- Assignment utworzony przez solver dostaje trwałe work-period/rest provenance;
- persisted boundary/cross-site provenance steruje REST, nie aktualny SiteProfile.

B NIE implementuje awaryjnego 24h. Same-month emergency, cross-month emergency i `boundary_shift_demands` należą do C. B ma jednak zbudować work-period primitive tak, aby C nie musiało tworzyć drugiej semantyki REST.

## PART B SCOPE

- rota/application/assembler.py
- rota/application/deviation_mapping.py
- rota/persistence/schedule_repository.py
- rota/planning/eligibility.py
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/validator.py
- rota/planning/work_periods.py
- tests/test_t012.py

Żaden inny plik produkcyjny/testowy w B.

`rota/planning/work_periods.py` jest drugim i ostatnim nowym plikiem nie-pipeline całego T012. `tests/test_t012.py` już istnieje po A; B tylko dopisuje testy.

## POZA B

B NIE zmienia:

- `arch/spec.md` ani `arch/FROZEN.lock`;
- schema v5 ani kolumn persistence z A;
- `rota/domain.py` — wszystkie pola są już w A;
- `rota/planning/state.py` — `boundary_shift_demands` dopiero C;
- engine two-pass / emergency orchestration;
- manual REST override / DecisionRecord — D;
- UI/bridge;
- ROTA-REG-001 fixture/oracle;
- T013/T017.

Jeżeli implementacja B rzeczywiście potrzebuje innego pliku, STOP + amendment Part B przed zmianą. Nie poszerzać samodzielnie.

## A JEST ŹRÓDŁEM DANYCH

Na A SHA obowiązują już:

- `ShiftDemand.shift_kind`;
- `ShiftDemand.catalog_kind`;
- `ShiftDemand.required_rest_hours`;
- `ShiftDemand.work_period_template_id`;
- `ShiftDemand.work_period_component`;
- `ShiftDemand.emergency_24h_rest_hours`;
- `Assignment.work_period_id`;
- `Assignment.required_rest_after_hours`;
- persistence round-trip tych pól;
- normalne 24h jako dwa demandy H24 component 1/2 z jednym template id i równym configured rest/count.

B nie tworzy alternatywnych DTO ani równoległych pól.

## PURE WORK-PERIOD MODEL — JEDNO ŹRÓDŁO SEMANTYKI CZASU

Nowy `rota/planning/work_periods.py` jest wąskim pure modułem bez CP-SAT, SQL i I/O.

Może definiować prywatny/value dataclass `WorkPeriod` lub równoważną strukturę zawierającą co najmniej:

- employee_id;
- period key;
- start_datetime;
- end_datetime;
- required_rest_after_hours;
- assignment_ids/component identity potrzebne validatorowi.

Moduł odpowiada za:

1. normalizację non-CANCELLED Assignment do work periods;
2. legacy fallback;
3. scalenie komponentów z tym samym `(employee_id, work_period_id)`;
4. wyznaczenie start/end całego periodu;
5. resolved rest po periodzie;
6. directional REST relation A→B;
7. wykrycie malformed work-period provenance;
8. helpery potrzebne solverowi do zbudowania prospective periodu z ShiftDemand bez persistence I/O.

To NIE jest façade nad solverem/validatorem. Solver używa tej samej semantyki czasu do budowy constraints; validator niezależnie iteruje finalny candidate i sam emituje `ViolationDetail`.

## WORK PERIOD IDENTITY / LEGACY

Dla Assignment:

- jawny `work_period_id` grupuje komponenty wyłącznie w obrębie tego samego employee;
- `work_period_id=None` = ten Assignment jest samodzielnym legacy work period;
- `required_rest_after_hours=None` = legacy 11 h;
- CANCELLED nie jest pracą i nie wchodzi do period normalization;
- TRAINEE pozostaje pracą dla REST/LOAD; jeżeli nie ma jawnego provenance, jest legacy standalone period z rest 11.

Dla nowo rozwiązanych PRIMARY po B:

- solver MUST zapisywać nie-None `work_period_id`;
- solver MUST zapisywać nie-None `required_rest_after_hours`;
- legacy demand bez T012 rest dostaje jawny compatibility rest 11, nie `None`;
- identyfikator periodu ma być deterministyczny i site-scoped, aby dwa Site z podobnym profile/date/template nie mogły przypadkowo stworzyć tego samego work_period_id dla jednego employee;
- exact string format jest techniczny, ale nie może zależeć od kolejności iteracji solvera.

## RESOLVED REST W JEDNYM PERIODZIE

Normalny B case:

- standalone 12h/INNY: rest = Assignment.required_rest_after_hours;
- normalne 24h: dwie bezpośrednio kolejne komponenty tego samego employee/work_period_id; span = start component 1 → end component 2; rest po całości = configured 24h rest;
- między komponentami tego samego work period NIE ma REST gap.

Malformed provenance fail-closed:

- komponenty jednego work period muszą tworzyć ciągły, niepokrywający się chain;
- work period nie może mieć >2 komponentów;
- kilka komponentów utworzonych w tym samym ScheduleVersion musi mieć zgodne explicit rest;
- brak/ujemny explicit rest w nowym T012-created provenance nie może zostać po cichu zastąpiony current profile.

Forward-compatible z zamrożonym C:

- gdy kiedyś jeden work_period_id obejmuje komponenty z różnych ScheduleVersion.month (cross-month emergency C), terminalna/najnowsza komponenta jest źródłem rest po całym periodzie;
- B NIE tworzy takiej pary, ale pure normalizer nie może zakładać, że wspólny period zawsze mieści się w jednym ScheduleVersion;
- różna wartość rest między schedule versions jest dopuszczalna tylko jako historyczny cross-month extension opisany w Frozen Contract; nie legalizuje rozbieżnych rest dwóch komponentów utworzonych razem w jednym ScheduleVersion.

## DIRECTIONAL REST-01

Dla dwóch kolejnych, różnych work periods A potem B tego samego employee:

`B.start_datetime - A.end_datetime >= A.required_rest_after_hours`

Reguły:

- tylko rest A buduje ścianę przed B;
- rest B nie działa wstecz;
- overlap dwóch różnych periods jest HARD REST-01;
- `required_rest_after_hours=0` jest legalne;
- internal boundary dwóch komponentów jednego periodu nie jest gapem i nie może obniżać `minimum_rest_hours` do 0;
- `minimum_rest_hours` raportu oznacza minimum rzeczywistego gapu między różnymi sprawdzanymi work periods, nie między technicznymi komponentami jednego periodu.

## CP-SAT REST — PROSPECTIVE PERIODS, NIE POJEDYNCZE SLOTY

Obecne `constraints.py` porównuje pojedyncze ShiftDemand i używa `REST_MIN_HOURS`. B ma to usunąć z current T012 path.

Solver ma budować REST względem prospective work periods per employee:

- zwykły 12h/INNY demand = jeden prospective period;
- normalna para H24 component 1/2 jednego template = jeden prospective period, jeżeli employee jest wybrany;
- fixed existing/boundary/other-site Assignment są najpierw normalizowane do fixed work periods;
- constraints powstają między różnymi periods, nigdy pomiędzy komponentami tego samego normalnego 24h.

Dla dwóch variable periods:

- overlap => nie mogą być oba wybrane;
- A przed B i gap < rest_A => nie mogą być oba wybrane;
- B przed A analogicznie używa rest_B.

Dla variable vs fixed:

- fixed A przed variable B: użyj persisted rest_A;
- variable A przed fixed B: użyj configured/snapshot rest_A variable periodu;
- overlap => variable jest niedozwolony.

Fixed-fixed history nie jest czymś, co CP-SAT ma „naprawiać”. B nie tworzy własnego backtrackingu ani search; tylko constraints OR-Tools.

## NORMAL CATALOG 24h — SAME PRIMARY SET HARD

Normalne 24h rozpoznaje się wyłącznie po T012 demand provenance:

- `catalog_kind=24h`;
- wspólny non-None `work_period_template_id`;
- dokładnie components 1 i 2;
- bezpośrednio kolejne 12h;
- równy required_primary_count/rest zgodnie z A.

Dla każdej takiej pary finalny zbiór PRIMARY employee_id na component 1 MUSI być identyczny jak na component 2.

Solver:

- egzekwuje tę równość per employee, nie tylko total headcount;
- działa także gdy `required_primary_count > 1`;
- musi uwzględniać fixed existing PRIMARY: fixed na jednej połowie wymusza tego samego employee na drugiej, jeżeli druga jest rozwiązywalna; sprzeczne fixed facts nie mogą zostać zamaskowane inną osobą;
- employee eligible tylko do jednej połówki nie może być użyty do całego normalnego 24h;
- zwykłe dwa sąsiednie H12 NIE są jeszcze parą — to dopiero C/emergency.

Independent validator:

- niezależnie grupuje finalne PRIMARY po H24 template;
- mismatch emituje `SHIFT-24-PAIR-01` z assignment_ids/demand_ids wystarczającymi do audytu;
- sprawdza również fixed/REALIZED/frozen components; nie mutuje ich.

## can_work_24h — NORMALNE 24h W B

`eligibility.py` ma dodać kwalifikację tylko dla `catalog_kind=24h` w B.

`profile_is_all_24h` = `standard_shifts` niepuste i po normalizacji KAŻDA pozycja ma catalog_kind=24h.

- mixed profile: normalna H24 component wymaga `membership.can_work_24h=true`;
- all-24h profile: flaga jest ignorowana;
- false nie blokuje ordinary 12h ani INNY;
- flagi 24h nie wolno użyć jako obejścia DAY_ONLY, Availability, SiteRule, membership.enabled ani EXTERNAL;
- obie komponenty 24h nadal przechodzą zwykłe D/N HARD osobno, więc np. DAY_ONLY employee nie dostaje N tylko dlatego, że całość jest 24h.

Stable blocker/violation code: `SHIFT-24-01`.

Validator stosuje tę kwalifikację do bieżących/non-REALIZED assignments zgodnie z istniejącą zasadą, że późniejsza zmiana roster/availability nie retroaktywnie unieważnia REALIZED history. Structural `SHIFT-24-PAIR-01` pozostaje sprawdzane niezależnie.

## DEVIATION MAPPING — DOMKNĄĆ JUŻ W B

Ponieważ B aktywuje oba built-in HARD codes dla normalnego 24h, `deviation_mapping.py` musi znać je od tego checkpointu:

- `SHIFT-24-01 -> DeviationCategory.PREFERENCE`;
- `SHIFT-24-PAIR-01 -> DeviationCategory.COVERAGE`.

Nie czekać z tym do C. Part C zachowuje te mapowania bez zmiany kategorii.

## ASSIGNMENT PROVENANCE Z SOLVERA

Przy `_extract_assignments` lub równoważnym miejscu:

Ordinary 12h/INNY:

- work_period_id = deterministyczny id tego employee + Site + demand/template;
- required_rest_after_hours = demand.required_rest_hours; legacy None → 11.

Normalne 24h:

- oba Assignment tego employee mają ten sam work_period_id;
- oba mają configured `required_rest_after_hours` z H24 demand provenance;
- role/state/frozen/covers_demand semantics pozostają obecne.

B nie przepisuje provenance fixed existing/REALIZED/frozen Assignment. Replan zachowuje fixed facts; redistributable future PRIMARY może dostać nowy, poprawny B provenance jako część nowego candidate.

## BOUNDARY / CROSS-SITE CONTEXT — REST NIE MA STAŁEGO HORYZONTU

A przechowuje required rest na Assignment, a kontrakt dopuszcza `required_rest_hours >= 0` bez górnego limitu.

Dlatego istniejące stałe `_context_window` około `-6/+8 dni` może pozostać dla LOAD-01, ale NIE może być jedynym źródłem REST context po B.

Dla każdego roster employee PlanningState musi mieć dla REST wystarczający persisted CURRENT context, aby znać:

- najbliższy wcześniejszy work period przed bieżącym candidate/month, niezależnie od tego jak dawno się skończył;
- najbliższy późniejszy known CURRENT work period, jeśli taki istnieje;
- wszystkie komponenty selected boundary/other-site work period potrzebne do poprawnej normalizacji jego span/rest;
- assignments w istniejącym rolling-7d window potrzebne LOAD-01 jak dotychczas.

Można to osiągnąć przez wąskie repository queries albo przez istniejące read API + deterministyczne filtrowanie w assemblerze. Nie tworzyć application façade ani nowego store.

Source of truth:

- previous/future persisted Assignment provenance;
- NIE current SiteProfile dla historycznego work period.

Cross-site:

- previous other-site period rest blokuje current candidate, jeśli gap jest za krótki;
- current candidate rest blokuje późniejszy known other-site period;
- brak persisted other-site record nadal oznacza brak danych, bez warning/DECISION_REQUIRED tylko z powodu braku historii.

## VALIDATOR — TYLKO RELEWANT REST EDGES

Independent validator normalizuje:

- finalny candidate/current target assignments;
- potrzebny boundary context;
- potrzebny other-site context.

REST-01 finding ma dotyczyć edge, w którym co najmniej jeden period należy do aktualnie walidowanego target candidate/current ScheduleVersion. Validator nie jest historycznym audytorem całej bazy i nie może zablokować bieżącego PLAN wyłącznie dlatego, że dwa stare fixed periods poza targetem naruszały REST między sobą.

Sprawdzane są więc:

- current ↔ current;
- previous boundary/other-site → current;
- current → future boundary/other-site.

Nie emitować nowego current finding dla historical-context ↔ historical-context, jeżeli żaden period nie należy do targetu.

## LOAD-01 — NIE PRZEPISYWAĆ

B nie zmienia produktu LOAD:

- LOAD nadal liczy faktyczne godziny Assignment;
- normalne 24h = 12h + 12h, nie dodatkowe 24h ponad komponenty;
- CANCELLED nie liczy się;
- TRAINEE zachowuje istniejącą semantykę LOAD;
- rolling window i threshold pozostają bez zmian.

Refactor `build_fixed_intervals` może rozdzielić REST context od LOAD intervals, ale nie zmieniać wyników LOAD poza koniecznym zachowaniem istniejącej semantyki.

## TESTY B — MINIMUM

Wszystkie poniższe dopisać do istniejącego `tests/test_t012.py`.

### Directional REST

- ordinary 12h rest=8: gap 8h legalny;
- ordinary 12h rest=16: ten sam gap 8h blokuje;
- asymmetry A(rest=16)→B(rest=0) używa 16;
- reverse ordering używa rest faktycznie wcześniejszego periodu;
- rest=0 legalny;
- overlap różnych periods HARD fail;
- internal gap 0 między H24 halves legalny i nie staje się `minimum_rest_hours=0`;
- legacy Assignment without provenance = standalone rest 11;
- newly solved legacy demand zapisuje jawny rest 11, nie None.

### Normal catalog 24h

- D→N H24: ten sam PRIMARY na obu components;
- N→D analogicznie;
- required_primary_count=2: identyczny dwuelementowy employee set po obu stronach;
- fixed employee na component 1 wymusza tę osobę na component 2;
- fixed sprzeczne sets są wykrywane przez independent validator jako `SHIFT-24-PAIR-01`;
- mixed profile `can_work_24h=false` blokuje normalne H24 jako `SHIFT-24-01`;
- all-24h ignoruje flagę;
- false nie blokuje ordinary H12/INNY;
- DAY_ONLY/HARD na N component nadal działa w normalnym 24h;
- oba solved H24 Assignments share work_period_id + configured rest;
- H24 start ostatniego dnia miesiąca i component 2 w następnym miesiącu nadal jest jednym normalnym work period.

### Persistence/history context

- previous same-site persisted period z rest >11 blokuje current candidate;
- previous cross-site persisted period z rest >11 blokuje current candidate;
- current candidate z długim rest blokuje known future other-site period;
- po zmianie current SiteProfile.required_rest_hours historyczny wynik pozostaje oparty na Assignment provenance;
- required rest większy niż 6/8 dni jest nadal widoczny przez nearest-period context — fixed context window nie może go zgubić;
- selected multi-component prior normal H24 jest normalizowany jako jeden period, nie dwa;
- brak other-site history nie tworzy syntetycznego warning/blockera;
- unrelated historical-context↔historical-context REST violation nie blokuje bieżącego candidate, jeśli target nie uczestniczy w tym edge.

### Provenance / regression

- malformed same-ScheduleVersion period with >2 components fail-closed;
- malformed same-ScheduleVersion period with inconsistent rest fail-closed;
- CANCELLED nie bierze udziału w REST;
- TRAINEE bez provenance zachowuje legacy standalone rest=11;
- `category_for_rule` dla SHIFT-24-01/PAIR zwraca dokładnie zamrożone kategorie;
- każdy FEASIBLE przechodzi independent HARD validation;
- ROTA-REG-001 PASS;
- pełna suite PASS.

## REQUIRED COMMANDS B

Po implementacji B, przed Codexem:

```text
pytest -q tests/test_t012.py
pytest -q
ruff check rota/application/assembler.py rota/application/deviation_mapping.py rota/persistence/schedule_repository.py rota/planning/eligibility.py rota/planning/constraints.py rota/planning/solver.py rota/planning/validator.py rota/planning/work_periods.py tests/test_t012.py
python guard.py check arch/spec.md
git diff --check
python backend.py tasks/ROTA-T012/brief.md 3a389bcbac274566ef6cdc5b7ddd0d66f4873958 <HEAD_SHA> <OUTPUT_PATH>
```

Backend nadal liczy cały T012 od integrated base. `RATIO/TOTAL_LINES` z A nie są blanket waiverem dla późniejszego HEAD. Po B konkretne bieżące wartości wracają do architekta, jeśli backend daje `WYMAGA_DECYZJI`.

## CODEX AUDIT B

Codex ma audytować dokładny B HEAD, nie tylko diff ostatniego commita.

Szczególnie atakować:

- globalne 11 nadal użyte jako current REST;
- rest przyszłego periodu zastosowany wstecz;
- 24h potraktowane jako dwa periods z internal REST;
- różni PRIMARY na dwóch halves normalnego 24h;
- can_work_24h omijane na mixed profile albo błędnie stosowane na all-24h;
- fixed half normalnego 24h ignorowane przez same-person constraint;
- current profile użyty do odtworzenia historycznego rest;
- stałe -6/+8 dni gubiące dłuższy persisted rest;
- validator blokujący plan przez stare history-history violation niezwiązane z targetem;
- LOAD przypadkowo zmieniony przez refactor REST;
- nowy własny search/backtracking;
- nowy plik poza `work_periods.py`.

## GATE B

Warunek przejścia:

`PASS — READY_FOR_IMPLEMENTATION_C`

Każdy finding zmieniający produkt albo wymagający nowego pliku poza union TASK_SCOPE wraca do architekta. CC nie zaczyna C przed PASS B + ewentualną jawną akceptacją konkretnych wartości backend `WYMAGA_DECYZJI`.

# Elnath Rota — remanent kodu i Contract Minimum

Data audytu: 2026-08-28
Bazowy branch: `main`
Bazowy SHA: `aa6330cd32d3f891777cc148805527bc307bd719`
Branch audytu: `audit/code-inventory-2026-08-28`

## Status dokumentu

To jest dokument audytowy. Nie zmienia `arch/spec.md`, nie zmienia kontraktu produktu i nie autoryzuje usuwania kodu. Każde cięcie elementu wymaganego przez aktualny frozen contract wymaga jawnej decyzji właściciela.

Cel: odpowiedzieć na trzy pytania przed dalszym debugowaniem:

1. Czy obecna architektura ma rdzeń wart zachowania?
2. Które elementy są konieczne, które użyteczne, które podejrzane jako przerost, a które są wyłącznie artefaktami procesu wytwarzania?
3. W jakiej kolejności należy falsyfikować kontrakt i upraszczać system, aby nie przepisywać programu bez potrzeby?

## Werdykt wykonawczy

`DO NOT REWRITE FROM SCRATCH.`

Rdzeń planistyczny należy zachować. CP-SAT + niezależny HARD validator + jawne statusy `FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR` tworzą sensowny fundament. Problemem nie jest sam wybór architektury solvera. Problemem jest narastająca szerokość kontraktu, liczba ścieżek fallback/replan oraz wymieszanie kodu produktu z warsztatem audytowo-zadaniowym.

Do czasu zakończenia remanentu obowiązuje rekomendacja:

`FEATURE FREEZE -> CONTRACT FALSIFICATION -> PRUNE/ISOLATE -> DEBUG -> dopiero potem nowe funkcje.`

## 1. Contract Minimum — cztery poziomy

Poniższe poziomy NIE redefiniują frozen contract. Służą do ustalenia minimalnej wartości produktu i identyfikacji kosztu dodatkowych funkcji.

### CM0 — rdzeń, bez którego Elnath Rota nie jest programem do układania grafików

Program musi potrafić:

- zbudować `PlanningState` dla jednego Site i miesiąca;
- wygenerować wymagane `ShiftDemand` z profilu;
- przypisać PRIMARY do wszystkich demandów albo jawnie powiedzieć, że nie może tego zrobić;
- egzekwować podstawowe HARD: coverage, membership/eligibility, niedostępność/urlop, DAY_ONLY jeśli profil tego wymaga, REST, rolling 7d load threshold oraz frozen/REALIZED w replanie;
- korzystać z CP-SAT jako wyszukiwarki kombinatorycznej;
- niezależnie zwalidować wynik HARD po solverze;
- zwrócić wyłącznie `FEASIBLE`, `DECISION_REQUIRED` albo `TECHNICAL_ERROR`;
- zachować grafik po restarcie programu;
- odtworzyć bieżący grafik dla Site/month.

Kod, który bezpośrednio obsługuje CM0, ma domyślny status `MUST`.

### CM1 — minimalny produkt operacyjny dla realnego obiektu

Oprócz CM0:

- koordynator może utworzyć/otworzyć miesiąc;
- może wprowadzić pracowników, członkostwo, ograniczenia i dostępność;
- może wykonać REPLAN po chorobie/no-show bez ruszania REALIZED/frozen;
- może ręcznie skorygować plan;
- program zachowuje current ScheduleVersion i historię potrzebną do bezpiecznej rekonstrukcji;
- można odczytać/exportować grafik w formie użytecznej dla koordynatora;
- błędy konfiguracji nie są maskowane jako brak personelu.

CM1 jest docelowym progiem: „program rzeczywiście daje się używać na obiekcie”.

### CM2 — pełny obecny kontrakt domenowy

To wszystko, co frozen `arch/spec.md` wymaga ponad CM1, m.in.:

- rozbudowane SiteRule/version provenance;
- Deviation + acknowledgement/finalization;
- normalne i awaryjne 24h, work-period provenance, cross-month/cross-site REST;
- external support;
- trainee/readiness;
- WorkBalance i historyczne salda;
- pełna wersjonowalność ScheduleVersion;
- reguły wyjątków i ich audytowalność;
- dodatkowe zachowania wymagane przez późniejsze amendmenty.

CM2 może być poprawnym produktem, ale każda jego funkcja musi uzasadnić swój koszt poprzez rzeczywisty wymóg właściciela/operacji. Fakt, że kod już istnieje, nie jest uzasadnieniem.

### CM3 — wygoda, optymalizacja jakości i warstwa produktowa ponad minimum

Przykłady:

- 2–3 alternatywne grafiki;
- wyszukiwanie „Szukaj dalej / Szukaj szerzej”;
- rozbudowane analytics;
- rozbudowany ekran historii/decision guidance;
- dodatkowe rankingi i fairness ponad wymagane minimum;
- mechanizmy służące wyłącznie zwiększaniu jakości wariantu, gdy pierwszy HARD-valid grafik już istnieje.

CM3 nie powinien blokować osiągnięcia CM1.

## 2. Klasyfikacja kodu: MUST / USEFUL / SUSPECT / PROCESS-ONLY

Znaczenie:

- `MUST` — bezpośrednio potrzebne CM0/CM1 albo fundamentalne dla bezpieczeństwa kontraktu.
- `USEFUL` — sensowne, ale nie powinno blokować minimalnego działającego produktu.
- `SUSPECT` — funkcja może być kontraktowo wymagana, lecz jej koszt/złożoność wymaga ponownego uzasadnienia; NIE usuwać bez owner ruling.
- `PROCESS-ONLY` — narzędzie produkcji/audytu, nie runtime produktu.

### 2.1 `rota/planning`

`MUST`

- `engine.py` — publiczna orkiestracja planowania i mapowanie statusów. Zachować komponent, ale uproszczenie ścieżek jest kandydatem audytowym.
- `solver.py` — CP-SAT adapter. Zachować.
- `validator.py` — niezależny HARD validator. Zachować. Jest istotną barierą przeciw solver/model drift.
- `constraints.py` — HARD constraints. Zachować, ale każdą regułę mapować do literalnego kontraktu.
- `eligibility.py` — eligibility/membership/availability. Zachować.
- `state.py`, `engine_types.py` — kontrakty wejścia/wyjścia planowania. Zachować.
- `shift_catalog.py` — generacja/klasyfikacja demandów. Zachować.
- `timeutil.py`, `work_periods.py` — niezbędne dla REST/rolling windows/24h provenance. Zachować dopóki obecny kontrakt zawiera T012.

`USEFUL`

- `fairness.py` — jakość grafiku. Nie może być warunkiem poprawności CM0/CM1. Jeśli komplikuje debugowanie HARD, powinna być możliwa do izolowanego wyłączenia w testach diagnostycznych bez zmiany modelu HARD.
- `absence.py` — użyteczne operacyjnie, ale należy sprawdzić, czy nie dubluje durable input / availability semantics.
- `decision_guidance.py` — dobra warstwa UX dla `DECISION_REQUIRED`, ale nie powinna tworzyć semantyki decyzji niezależnej od wyniku engine/validator.

`SUSPECT`

- `replan_reshuffle.py` — REPLAN jest CM1/MUST, ale osobna warstwa „reshuffle/diversity” może zawierać optymalizację ponad minimalny replan. Należy rozdzielić „replan poprawny” od „replan koniecznie inny / szerzej przetasowany”.
- wielostopniowy fallback w `engine.py`: DAY_ONLY-N fallback, emergency 24h, uncapped LOAD i dalsza diagnostyka. Poszczególne wyjątki są obecnie kontraktowe, lecz liczba ścieżek kontrolnych jest wysoka. Audyt ma sprawdzić, czy da się zachować semantykę przy jednej jawnej tabeli etapów zamiast rozproszonego sterowania.
- wyszukiwanie wielu alternatywnych kandydatów i różnorodności. To CM3, chyba że właściciel jawnie utrzyma to jako obowiązek produktu.

### 2.2 `rota/application`

`MUST`

- `assembler.py` — boundary pomiędzy persisted state a PlanningState. Zachować.
- `open_month.py` — potrzebne CM1.
- `plan_ops.py` — potrzebne, jeśli jest jedyną warstwą use-case planowania; sprawdzić, czy nie dubluje engine orchestration.
- `manual_edit.py` — CM1, ponieważ realny koordynator musi móc poprawić grafik.
- `lifecycle_ops.py` — minimalny lifecycle current/final potrzebny dla bezpiecznej wersji; zakres może być większy niż minimum.
- `store.py` / kontekst dostępu — zachować cienką warstwę.

`USEFUL`

- `schedule_export.py` — użyteczny produktowo; nie powinien wpływać na poprawność solvera.
- `backup.py` — właściwe operacyjnie, ale niezależne od rdzenia planowania.
- `availability_matrix.py` — UX/read model.
- `memory_read.py`, `balance_read.py`, `analytics_read.py` — read models; izolować od logiki decyzyjnej.

`SUSPECT`

- `durable_inputs.py` — bardzo duży moduł. Wymaga audytu, czy agreguje zbyt wiele niezależnych use-case'ów i czy istnieją równoległe ścieżki zapisu tych samych pojęć.
- `rule_decisions.py` — obecny kontrakt wymaga decisions/rules, ale warstwa może być szersza niż CM1.
- `deviation_mapping.py` — kontraktowo potrzebne dla obecnego Deviation model, lecz nie jest częścią minimalnej obietnicy „ułóż/replanuj poprawny grafik”.
- `training.py` — trainee/readiness to rozszerzenie domeny. Utrzymać tylko jeśli jest rzeczywiście potrzebne produktowo; obecnie traktować jako CM2.
- `analytics_read.py` — CM3 z punktu widzenia podstawowego planowania.

### 2.3 `rota/persistence`

`MUST`

- `db.py` — persistence foundation.
- `schedule_repository.py`, `schedule_lifecycle.py`, `schedule_validation.py` — zachować minimalną wersję, ponieważ current ScheduleVersion i rekonstrukcja są CM1.
- `employee_repository.py`, `site_repository.py`, `site_profile_repository.py`, `availability_repository.py` — dane wejściowe CM1.

`USEFUL`

- `calendar_repository.py` — jeśli kalendarz jest źródłem persisted holiday truth.
- `backup_repository.py`.
- `coordinator_repository.py` — potrzebne przy realnym modelu koordynatora, lecz nie wpływa na algorytm.

`SUSPECT`

- `decision_ledger.py` — obecny kontrakt może go wymagać, ale należy potwierdzić realne użycie. Nie może stać się równoległym źródłem prawdy o regułach planowania.
- `site_memory.py` — duża warstwa pamięci operacyjnej. Sprawdzić, czy nie przechowuje derived/read-model state, który można wyliczać.
- `absence_reference_repository.py` — duży moduł; sprawdzić, czy złożoność wynika z prawdziwej konieczności czy z kolejnych audytowych edge-case'ów.
- `work_balance_repository.py` — CM2, nie rdzeń planowania.
- `site_rule_repository.py` + `site_rule_assembly.py` — obecny kontrakt je uzasadnia, ale generic rule engine jest naturalnym miejscem przerostu. Każdy obsługiwany rule_kind musi mieć realne źródło w kontrakcie i konsumenta runtime.

### 2.4 API / UI

`MUST` dla CM1:

- health/bootstrap minimalne;
- roster / durable inputs potrzebne do zasilenia danych;
- schedule plan/replan/read;
- manual correction/finalization, jeśli dostępne przez istniejący router.

`USEFUL`:

- export;
- overview.

`SUSPECT / CM3`:

- analytics;
- history;
- rozbudowane decisions UI, o ile nie jest konieczne do zamknięcia `DECISION_REQUIRED`;
- wszystko, co prezentuje metryki, ale nie uczestniczy w przygotowaniu poprawnego grafiku.

Reguła: read-only UI nie może dokładać logiki biznesowej. Router powinien marshalować dane i wywoływać application use-case.

### 2.5 Pipeline repozytorium

`PROCESS-ONLY`

- `backend.py`
- `guard.py`
- `task_init.py`
- `session_log.py`
- `tasks/`
- `diffs/`
- `log/`
- `task_*_diff.txt`
- handoffy dla modeli/audytorów

Te elementy NIE są produktem Elnath Rota. Mogą zostać w repo jako tooling/history, ale Claude Code i audytorzy nie mogą traktować ich ograniczeń mechanicznych jako wymagań runtime.

Rekomendacja docelowa: przenieść je pod jeden jawny namespace, np. `dev_pipeline/` lub osobne repo, dopiero po zakończeniu bieżącego cyklu i bez naruszania historii. Na tym etapie nie przenosić automatycznie.

## 3. Contract → code → test → decyzja

To jest macierz pierwszego przejścia. Claude Code ma ją uzupełniać dowodami, nie reinterpretacją.

| Wymaganie / capability | Główny kod | Oczekiwany test trwały | Klasa | Decyzja teraz |
|---|---|---|---|---|
| Coverage wszystkich demandów | solver, validator | coverage gap/excess, overlap | MUST | KEEP |
| Membership/eligibility | eligibility, solver, validator | enabled/local/external/availability | MUST | KEEP |
| REST-01 | constraints, work_periods, validator | same-site, boundary, work-period | MUST | KEEP |
| Rolling 7d LOAD threshold | constraints, validator | każde ruchome 7 dni, boundary | MUST | KEEP |
| DAY_ONLY | eligibility/validator | N blocked + profile off + authorized exception | MUST | KEEP |
| Frozen/REALIZED REPLAN | solver, replan, validator | niezmienność fixed assignment | MUST | KEEP |
| CP-SAT search | solver | realistic feasible/infeasible fixtures | MUST | KEEP |
| Independent validation | validator + engine | solver candidate rejected -> TECHNICAL_ERROR/decision per contract | MUST | KEEP |
| Schedule persistence/current version | persistence schedule* | restart/reconstruct/current-only | MUST | KEEP |
| Manual edit | application/manual_edit + lifecycle | legal correction + deviation behavior | MUST CM1 / CM2 details | KEEP, AUDIT SCOPE |
| REPLAN after absence | engine/replan/absence | sickness/no-show realistic vertical case | MUST CM1 | KEEP |
| SiteRule generic execution | site_rules + repositories | each supported executable kind | CM2 | SUSPECT — prove consumers |
| Emergency/normal 24h | shift_catalog/constraints/work_periods/solver/validator | pair identity/rest/cross-month | CM2 frozen | KEEP unless owner retires |
| External support | eligibility/repository/UI | window-qualified assignment | CM2 | REVIEW PRODUCT NEED |
| Training/trainee | training + validator + persistence | mentor/readiness lifecycle | CM2 | REVIEW PRODUCT NEED |
| WorkBalance | balance + repository/analytics | current-version-only totals | CM2 | REVIEW PRODUCT NEED |
| Deviation/decision ledger | lifecycle/deviation/decision* | manual violation/finalization provenance | CM2 | REVIEW SCOPE |
| Multiple schedule alternatives | solver/engine/fairness | diversity + HARD validity | CM3 | SUSPECT |
| Search further/wider | replan/solver/engine | same HARD model, different result, bounded time | CM3 | SUSPECT |
| Analytics screens | analytics read/API/UI | read-only consistency | CM3 | KEEP ONLY IF PRODUCT VALUE |
| Audit round history | tests/test_audit_* + tasks | none as product capability | PROCESS | CONSOLIDATE |
| Mechanical gate | backend/guard/task_init | tooling tests | PROCESS | ISOLATE FROM PRODUCT |

## 4. Test suite — remanent, nie masowe kasowanie

Obecny test suite przechowuje wiele plików nazwanych numerami rund audytowych (`test_audit_r*`, `test_audit_t*_r*`). To jest wartościowa historia znajdowanych błędów, ale słaba końcowa taksonomia regresji.

Docelowa zasada:

- test trwały nazywamy zachowaniem produktu, nie rundą audytu;
- test, który udowodnił realny bug kontraktowy, zostaje po przeniesieniu do właściwej rodziny zachowania;
- test oparty na nieautoryzowanej interpretacji kontraktu nie może zostać oracle;
- testy historyczne można archiwizować dopiero po udowodnieniu, że ich wartościowe przypadki są pokryte przez testy zachowania;
- NIE robić teraz masowego rename/delete, bo utrudni to debugowanie przed uzyskaniem baseline.

Proponowane docelowe rodziny:

- `tests/planning/test_coverage.py`
- `tests/planning/test_rest.py`
- `tests/planning/test_load.py`
- `tests/planning/test_eligibility.py`
- `tests/planning/test_replan.py`
- `tests/planning/test_24h.py`
- `tests/planning/test_validator_independence.py`
- `tests/persistence/test_schedule_lifecycle.py`
- `tests/application/test_manual_edit.py`
- `tests/vertical/test_real_object.py`

To jest rekomendacja organizacyjna, nie obecny task implementacyjny.

## 5. Najbardziej prawdopodobne źródła przerostu

### A. Sterowanie fallbackami w planowaniu

Ryzyko: wiele etapów solvera i diagnostyki tworzy combinatorial control-flow nawet wtedy, gdy model CP-SAT sam jest poprawny.

Cel audytu: zapisać jedną tabelę stanów:

`stage -> które wyjątki dozwolone -> kiedy przejść dalej -> jakie statusy są terminalne`.

Jeśli istnieją dwie ścieżki o identycznej semantyce, scalić dopiero po testach kontraktowych.

### B. REPLAN jako osobny „produkt w produkcie”

Minimalny REPLAN ma: zachować fixed/REALIZED, usunąć niedostępnego pracownika z przyszłego planu, ponownie pokryć demandy i zwrócić poprawny wynik albo DECISION_REQUIRED.

Wyszukiwanie koniecznie innego wyniku, diversity, narrow/wide search i minimalizacja reshuffle to warstwa jakości. Nie wolno pozwolić, aby błąd w tej warstwie blokował podstawowy bezpieczny REPLAN.

### C. Generic rules + provenance + ledgers

Historia zmian doprowadziła do wielu pojęć: SiteRuleVersion, applicability, applied_rule_version_ids, DecisionRecord, Deviation, source_reference, exception records.

Każde z nich może być uzasadnione, ale razem tworzą własny subsystem. Wymagany test remanentu:

dla każdego persisted typu wskazać:

1. kto go zapisuje;
2. kto go czyta;
3. jaka decyzja runtime zależy od niego;
4. jaki literalny fragment kontraktu go wymaga;
5. co konkretnie zepsuje się po jego usunięciu.

Jeżeli punkt 3 i 5 brzmią „nic, tylko historia/audyt”, obiekt jest kandydatem do uproszczenia lub archiwalnej warstwy read-only.

### D. Analytics / history / balances

Nie wolno ich mieszać z logiką planowania. PlanningState może korzystać tylko z tych danych historycznych, które literalnie wpływają na constraint/objective. Reszta powinna pozostać read-model.

### E. Proces modeli jako quasi-architektura produktu

`backend.py`, guard, Task scopes, limits linii i raporty rund służą dyscyplinie implementacyjnej. Nie są argumentem za istnieniem klasy, tabeli, endpointu ani constraintu w produkcie.

## 6. Następne kroki audytu — kolejność obowiązkowa

### AUDIT-1 — Baseline kontraktowy na dokładnym SHA

Na bazowym SHA uruchomić:

1. pełny `pytest`;
2. benchmark z README z ustalonym seedem;
3. real-object vertical scenario;
4. minimalne scenariusze CM0/CM1 zapisane poniżej.

Wynik: tabela PASS/FAIL/ERROR, bez naprawiania kodu w tym samym kroku.

### AUDIT-2 — Minimalne scenariusze CM0/CM1

Minimum wymagane do stwierdzenia „warto debugować ten kod”:

1. zwykły realny miesiąc 5 pracowników, D/N, pełne coverage;
2. DAY_ONLY employee nie dostaje N;
3. zgłoszona choroba jednego pracownika w już istniejącym planie -> REPLAN zachowuje REALIZED/frozen i próbuje naprawić przyszłość;
4. jednocześnie co najmniej jeden dzień wolny/urlop innej osoby;
5. brak personelu -> `DECISION_REQUIRED`, nie TECHNICAL_ERROR i nie fałszywe FEASIBLE;
6. rolling 7d > threshold -> plan nie kończy jako zwykłe FEASIBLE;
7. REST boundary między miesiącami;
8. restart/reopen -> current schedule rekonstruuje się identycznie;
9. manual correction -> nowa wersja, poprzedni FINAL nie jest mutowany;
10. invalid model/config -> `TECHNICAL_ERROR`, nie decyzja kadrowa.

### AUDIT-3 — Reachability / dead-code inventory

Claude Code ma zrobić statyczny remanent każdego pliku produkcyjnego:

- public functions/classes;
- importerzy/callers;
- endpoint/use-case entry points;
- test-only symbols;
- symbole bez runtime callerów.

Wynik ma zawierać `UNUSED_RUNTIME`, `TEST_ONLY`, `DUPLICATED_PATH`, `LIVE`.

Zakaz: nie usuwać w tej fazie.

### AUDIT-4 — Duplicate business logic inventory

Szczególnie sprawdzić:

- solver vs validator — duplikacja jest celowa tylko tam, gdzie validator niezależnie re-derives HARD;
- assembler vs repositories;
- schedule_validation vs planning validator;
- site_rule_assembly vs site_rules;
- absence.py vs availability/durable inputs;
- plan_ops vs engine;
- API routers vs application layer.

Każda duplikacja ma zostać oznaczona `INTENTIONAL_INDEPENDENCE` albo `ACCIDENTAL_DUPLICATION`.

### AUDIT-5 — Complexity budget

Nie używać arbitralnego limitu linii jako wyroku. Dla modułów `solver.py`, `validator.py`, `engine.py`, `constraints.py`, `durable_inputs.py`, `db.py`, `schedule_export.py` policzyć:

- liczbę publicznych wejść;
- liczbę znaczących branchy/trybów biznesowych;
- liczbę różnych kontraktowych rule codes;
- liczbę callerów;
- liczbę test families.

Celem jest wskazanie modułów, które robią kilka różnych rzeczy, nie karanie ich za sam rozmiar.

### AUDIT-6 — Owner Decision Queue

Po AUDIT-1..5 powstaje krótka lista decyzji, maksymalnie po jednej na capability. Przykładowe pytania:

- Czy 2–3 alternatywne grafiki są funkcją produktu czy można zejść do jednego poprawnego + „szukaj ponownie”?
- Czy narrow/wide REPLAN jest potrzebny, czy wystarczy jeden bezpieczny replan minimalizujący zmiany?
- Czy trainee/readiness ma wejść do pierwszej wersji używanej na obiekcie?
- Czy external support jest potrzebny teraz?
- Czy analytics/quarter balances są potrzebne przed stabilizacją grafiku?
- Czy generic SiteRule ma obsługiwać dowolne przyszłe reguły, czy tylko jawnie nazwane rule kinds obecnego produktu?

Bez owner ruling nic z CM2 nie jest usuwane tylko dlatego, że audyt uzna je za SUSPECT.

## 7. Kryterium KEEP / PRUNE / REWRITE

Po wykonaniu AUDIT-1..6:

### KEEP + DEBUG

Jeśli CM0/CM1 scenariusze w większości przechodzą, a błędy są lokalne i wynikają z konkretnych edge-case'ów, zachować architekturę i debugować.

### PRUNE + DEBUG

Jeśli rdzeń działa, ale większość awarii pochodzi z CM2/CM3, izolować/odchudzać te capability po decyzjach właściciela. Nie przepisywać solvera.

### TARGETED REWRITE

Przepisać tylko komponent, jeśli jego odpowiedzialność jest nieodwracalnie wymieszana i nie da się zbudować kontraktowego testu wokół publicznej granicy. Przykładem może być pojedyncza warstwa orkiestracji, nie całe repo.

### FULL REWRITE

Dopuszczalne tylko jeśli zostanie dowiedzione jednocześnie:

- nie da się wiarygodnie zrekonstruować PlanningState;
- solver nie reprezentuje kontraktu HARD;
- independent validator nie potrafi niezależnie zweryfikować kandydata;
- persistence nie zachowuje reconstructable current schedule;
- naprawa tych granic wymagałaby większej zmiany niż napisanie minimalnego CM1 od nowa.

Na dziś brak takich dowodów.

## 8. Instrukcja dla Claude Code

Jeśli zaczynasz pracę od tego dokumentu:

1. przeczytaj `arch/spec.md`, ale NIE rozszerzaj jego znaczenia;
2. potraktuj bazowy SHA tego audytu jako punkt odniesienia;
3. nie refaktoryzuj i nie kasuj niczego podczas AUDIT-1..5;
4. najpierw dostarcz dowody i macierze;
5. test nie tworzy kontraktu;
6. finding bez literalnego źródła kontraktowego oznacz jako `ARCHITECTURE_PROPOSAL`, nie BLOCKER;
7. rozdziel `product code` od `process/tooling`;
8. jeśli znajdziesz martwy kod, nie usuwaj go bez pokazania runtime caller inventory;
9. jeśli znajdziesz duplikację solver-validator, nie scalaj jej automatycznie — niezależność validatora jest celowa;
10. wynik kolejnego kroku zapisz jako `CODE_INVENTORY_AUDIT_RESULTS_2026-08-28.md` na osobnym task/audit branchu.

## 9. Pierwsza decyzja audytu

Na podstawie obecnego remanentu:

`VERDICT = KEEP_ARCHITECTURE / FREEZE_FEATURES / AUDIT_AND_PRUNE_BEFORE_DEBUG_EXPANSION`

Nie ma podstaw do wyrzucenia Elnath Rota ani pełnego rewrite. Są natomiast podstawy do podejrzenia, że obecny produkt zawiera zbyt szeroki zakres CM2/CM3 i zbyt dużo trwałych artefaktów procesu. Najpierw należy zmierzyć, które z tych elementów rzeczywiście uczestniczą w runtime i które powodują awarie.

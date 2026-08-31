# ROTA-T044 — architect implementation review R2

Status: **PASS — IMPLEMENTATION ARCHITECTURALLY CLOSED — READY FOR OWNER MERGE DECISION**

Data: 2026-08-31
Branch: `task/ROTA-T044`
Audytowany exact implementation SHA: `8e76de2d8f50800e9da1c81850cb44146d07b588`
Niezależny reaudyt blockera ARCH-R1-01: `tasks/ROTA-T044/round_01/tests/tests_r14.txt` @ commit `dcc7a7267043cc085aec2b9e565d211a35a7df28` — PASS.
Poprzednia ocena architekta: `tasks/ROTA-T044/ARCHITECT_IMPLEMENTATION_REVIEW_R1.md` — FAIL z jednym blockerem `ARCH-R1-01` oraz jednym findingiem non-blocking `ARCH-R1-02`.

## 1. Werdykt

**PASS — T044 jest merytorycznie zgodne z zamrożonym celem Wariantu B.**

Symulator B:

- bada aktualny produkt/solver przez prawdziwe operacje API;
- nie poprawia solvera i nie zmienia wejścia pod jego wynik;
- nie buduje drugiego solvera, fairness evaluatora ani kwartalnego oracle;
- generuje zmienne obiekty i ciasną obsadę przed pierwszym PLAN;
- zachowuje surowe wyniki produktu do późniejszej diagnozy, także gdy formalnie nie są błędem harnessu;
- utrwala awarie harnessu/backendu i nie ukrywa błędów samego zapisu raportu.

Nie ma otwartego blockera kontraktowego ani implementacyjnego wymagającego dalszej poprawki T044.

Nie wykonuję merge. Decyzja o merge należy do OWNERA.

## 2. Scope i regresja zakresu — PASS

Od poprzedniego audytowanego implementation SHA `e80103d10e7d980a1d38b3572ecac25731a464b8` do `8e76de2d8f50800e9da1c81850cb44146d07b588` zmiana implementacyjna dotyczy wyłącznie:

- `tests/property/test_coordinator_simulator_variant_b.py` — neutralny raw-report/readback path i jego testy.

Pozostałe różnice w historii to dokumenty/audyty T044. Nie zmieniono:

- `rota/**`;
- `api/**`;
- `frontend/src/**`;
- `benchmarks/**`;
- Wariantu A;
- kalkulatora/generatora/EXTERNAL helperów B w `tests/property/coordinator_simulator.py`.

Dlatego elementy ocenione jako PASS w `ARCHITECT_IMPLEMENTATION_REVIEW_R1.md` pozostają semantycznie nietknięte.

Pełna regresja repo nie była uruchamiana; `tests_r14.txt` jawnie ogranicza się do poprawki ARCH-R1-01 i podaje `3 passed`. Jest to zgodne z kontraktem T044, który zabraniał pełnej regresji bez osobnej zgody OWNERA.

## 3. Merytoryczny cel Symulatora — PASS

### 3.1 Symulator obserwuje solver, nie pomaga mu

Wariant B zachowuje zamrożoną granicę:

- jedyne własne liczenie to kalkulator LOCAL przed PLAN;
- pierwszy PLAN idzie na zadeklarowanym LOCAL;
- EXTERNAL jest reakcją testową wyłącznie po realnym, niepustym `DECISION_REQUIRED`;
- zły/dziwny `FEASIBLE`, `TECHNICAL_ERROR`, końcowy `DECISION_REQUIRED`, `NO_ALTERNATIVE`, `NARROW_SEARCH_EXHAUSTED` albo `SEARCH_INCOMPLETE` nie powoduje zmiany obiektu pod wynik;
- harness automatycznie ocenia tylko HEADCOUNT i CLOSED WORLD.

To spełnia cel OWNERA: obecny solver ma pokazać swoje rzeczywiste zachowanie; jego zły grafik jest materiałem do następnego Tasku naprawczego, a nie czymś, co Symulator ma poprawić.

### 3.2 Kalkulator/generator — PASS i bez zmian od R1

Pozostaje kanoniczne:

`max_m(sum_k(ceil(layer_hours(k,m) / norm(m))))`

z oracle `5/10/9/4`, bez marginesu urlopowego i bez łączenia szczytów z różnych miesięcy.

Generator nadal osiąga różne godziny, H24, `required_primary_count` per `(kind, weekday)` w `{1,2}` oraz legalne overlap'y. Odrzuca wyłącznie zero coverage.

### 3.3 Absencje — PASS i bez zmian od R1

Urlop i ewentualne L4 są initial-setup-only przed pierwszym PLAN. Po PLAN state machine nie ma transition dopisującego/rozszerzającego absencję.

Urlop zachowuje skalę:

- `1 LOCAL` → jeden blok 10 dni roboczych;
- `>=2 LOCAL` → dokładnie dwa bloki 10+5 dni roboczych dla dwóch różnych osób, bez nakładania.

L4 jest losowane raz na obiekt, ~25%, 5 dni kalendarzowych, LOCAL-only.

### 3.4 PLAN / EXTERNAL / REPLAN — PASS w zamrożonym zakresie

Każdy przykład używa świeżej SQLite `:memory:` i nowego Site.

EXTERNAL:

- powstaje dopiero po realnym `DECISION_REQUIRED` z payloadem;
- zachowuje pierwszy wynik;
- create-person niesie bieżące decision id;
- membership/window przekazują `null`;
- retry jest zachowany w uporządkowanej liście;
- limit EXTERNAL = początkowy LOCAL count;
- brak reaktywnego dodawania LOCAL i ręcznych Assignmentów.

CLOSED WORLD obejmuje wszystkich kandydatów FEASIBLE oraz zachowane FEASIBLE wyniki REPLAN.

## 4. ARCH-R1-01 — CLOSED / PASS

Poprzedni blocker polegał na tym, że zwykłe zakończone przebiegi znikały wraz z bazą `:memory:`. Na `8e76de2` ten problem jest zamknięty.

### 4.1 Neutralny report path działa niezależnie od verdictu solvera

`_write_completed_report()` jest wywoływany z `teardown()` dla każdego przykładu, który dotarł do realnego PLAN, o ile wcześniej nie powstał failure snapshot.

Nie wymaga wyjątku ani własnego verdictu harnessu. Dzięki temu raport jest utrwalany również dla normalnego wyniku produktu.

`TECHNICAL_ERROR` pozostaje w `plan_result` / `final_result` dokładnie jako surowy status produktu; harness nie zmienia go na własny błąd jakości grafiku. `tests_r14.txt` potwierdza ten przypadek.

### 4.2 Payload jest wystarczający do późniejszej diagnozy

Wspólny `_snapshot()` zawiera co najmniej:

- stage;
- seed;
- month/regime;
- wygenerowane atoms/katalog;
- declared LOCAL;
- calculator result;
- target hours;
- absence draws;
- action log;
- pierwszy PLAN;
- ordered EXTERNAL/retry results;
- final result;
- informację o select;
- wszystkie zachowane REPLAN results;
- readback;
- reproduction command.

Candidates/Assignmenty pozostają wewnątrz surowych PlanningResultów; raport ich nie ocenia.

### 4.3 Readback jest prawdziwym odczytem produktu, nie nowym oracle

`_readback()` używa istniejących `sim.get_analytics()` i `sim.get_month_view()`.

Nie wylicza własnego bilansu/fairness. Pobiera wyłącznie istniejący stan produktu. Jeżeli sam odczyt nie jest dostępny, zapisuje `{"error": ...}` jako fakt diagnostyczny zamiast zastępować pierwotny PLAN/REPLAN swoim błędem.

Niezależny R14 wykonał realny przebieg i potwierdził niepuste `readback.analytics` oraz `readback.month_view`.

### 4.4 Awaria zapisu raportu nie jest ukrywana

`_write_completed_report()` nie połyka wyjątku z zapisu.

`teardown()` używa `try/finally`, więc:

- błąd IO jest widoczny dla pytest/Hypothesis;
- połączenie SQLite i dependency override są mimo tego sprzątane.

To jest właściwa granica: brak wymaganego artefaktu nie może dać zielonego przebiegu.

## 5. Failure path — PASS

Poprzednie R11-01 pozostaje zamknięte:

- setup/plan/select/replan/invariant przechwytują także wyjątki inne niż `AssertionError`;
- wspólny failure snapshot jest zapisywany;
- pierwotny wyjątek jest ponownie zgłaszany.

Zmiana raw-report nie obchodzi ani nie zastępuje failure path.

## 6. Findings non-blocking — nie rozszerzać T044

### 6.1 ARCH-R1-02 — FEASIBLE po REPLAN nie jest później wybierany

Pozostaje wcześniejsza obserwacja:

- po pierwszym PLAN Symulator potrafi wykonać `select_candidate`;
- `do_replan()` zapisuje późniejszy PlanningResult;
- state machine nie ma osobnej ścieżki `REPLAN FEASIBLE -> select_candidate tego nowego kandydata`.

To jest realna luka pokrycia pełnego zachowania koordynatora, ale nie blocker T044: frozen Task nie wymagał jednoznacznie akceptacji każdego FEASIBLE REPLAN. Nie rozszerzać teraz po cichu. Jeżeli OWNER będzie chciał badać sekwencję `REPLAN -> wybór nowego grafiku -> dalsza praca`, powinien powstać osobny mały Task/kontrakt.

### 6.2 Reproduction command dla krótkiego FEASIBLE może wykonać dodatkowy select

`reproduction_command_b(seed, num_replans)` używa `run_full_scenario_b()`, który po FEASIBLE automatycznie wybiera pierwszego kandydata.

State machine może natomiast zakończyć krótki przykład po samym PLAN, zanim Hypothesis wylosuje `do_select_candidate`. W takim raporcie `selected=false`, a gotowa komenda wykona jeszcze select.

Nie blokuje to celu diagnostycznego T044:

- oryginalny `plan_result` wraz z candidates/Assignmentami jest już trwale zapisany;
- `action_log` i `selected` pokazują rzeczywistą sekwencję;
- ten sam seed odtwarza kanoniczny obiekt i pierwszy PLAN;
- dla przypadków z REPLAN `num_replans>0` implikuje, że select wcześniej nastąpił, więc materialna sekwencja jest zgodna.

To można kiedyś dopracować, jeśli wymagane będzie bit-for-bit replay każdego skróconego przebiegu Hypothesis; nie rozszerzać T044 tylko z tego powodu.

### 6.3 `observe()` może zużyć część małego profilu

`observe()` jest zawsze dostępne, również przed PLAN, aby uniknąć `InvalidDefinition` po terminalnym wyniku produktu. Nie zmienia stanu, ale może zużyć część `stateful_step_count=4`.

To obniża efektywne pokrycie, lecz nie zmienia semantyki i nie jest blockerem. Ewentualne strojenie profilu/warunku `observe` jest osobnym TECHNICAL_ONLY cleanupem.

## 7. Relacja do R14

`tests_r14.txt` nie jest samodzielnym dowodem całego T044 i nie traktuję go w ten sposób.

R14 poprawnie potwierdza w swoim wąskim zakresie:

- realny completed report ma analytics i month_view;
- TECHNICAL_ERROR pozostaje surowym wynikiem;
- awaria zapisu jest widoczna;
- SQLite jest sprzątana w `finally`;
- 3/3 testy celowane PASS.

Finalny PASS tej oceny wynika z połączenia:

1. wcześniejszego merytorycznego review całego `e80103d`, gdzie jedynym blockerem był ARCH-R1-01;
2. kontroli diffa do `8e76de2`, który nie naruszył wcześniej zamkniętych pionów;
3. bezpośredniego przeglądu obecnego raw-report/readback/failure lifecycle;
4. niezależnego R14 na exact implementation SHA.

## 8. Finalny gate

**ROTA-T044 jest architektonicznie zamknięte.**

Nie ma otwartego blockera wymagającego kolejnej implementacji w ramach T044.

Dalsze uwagi z sekcji 6 są świadomie non-blocking i nie powinny zostać dopisane do tego Tasku bez osobnej decyzji/kontraktu.

Merge nie jest wykonywany w tej ocenie.

---

**ARCHITECT FINAL IMPLEMENTATION VERDICT: PASS — READY FOR OWNER MERGE DECISION.**

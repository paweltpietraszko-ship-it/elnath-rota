# ROTA-T041 — ARCHITECT REVIEW R1

**Reviewed contract SHA:** `4dd3c105ee15d5dcb1b3cb6dda0c48dfeef8aa53`  
**Base:** `main@a919a8244cc592e6b12f35b9c8e08b40803e07ec`  
**Review status:** **WYMAGA KOREKTY PRZED PREIMPLEMENTATION AUDIT**  
**Scope:** review only; no product-code change authorized.

## 1. Fairness bez targetu — zamrozić hierarchię objective

Obecny kontrakt poprawnie wymaga przy brakującym `target_hours` target-independent fairness oraz w T41-A01 wyniku `144/144/144/144/144`, gdy HARD na to pozwala. Brakuje jednak literalnej relacji tego fallbacku do istniejącego `TARGET-01` i target equity.

Obecny solver buduje canonical worked-hours w kontekście pracowników obecnych w targetach i chroni `TARGET-01` matematycznym priorytetem przed equity/rhythm. Samo dodanie nowego spread penalty nie gwarantuje więc T41-A01: istniejące targety czterech osób mogą nadal dominować piątą osobę bez targetu.

**Wymagana korekta kontraktu:**

> Jeżeli choć jeden uczestniczący eligible LOCAL nie ma `target_hours`, wektor targetów jest niekompletny i w tym solve `TARGET-01` oraz target-equity **nie rankują kandydatów**. Zastępuje je target-independent minimalizacja spreadu `max(actual PRIMARY hours) - min(actual PRIMARY hours)` dla całej grupy uczestniczących eligible LOCAL. Gdy komplet targetów istnieje, dotychczasowy `TARGET-01` i target-equity działają bez zmian.

Dodatkowo T041 nie może tworzyć drugiego ownera rzeczywistych godzin. Należy uogólnić/reuse istniejący canonical worked-hours expression tak, aby tę samą wartość konsumował albo targetowy objective, albo fallback spread.

## 2. Fresh WORKING po zmianie katalogu — zawęzić do dowiedzionego C-04

AUDIT-1 C-04 dowodzi przypadku: istniejący current WORKING ma pusty/nieaktualny snapshot demandów i nie ma Assignmentów; po zmianie katalogu ponowny PLAN nadal używa starego persisted snapshotu.

Brief w OWNER-T041-03 zaczyna jednak szerzej i może być odczytany jako obowiązek automatycznej migracji dowolnego WORKING, także zawierającego PLANNED/frozen/REALIZED Assignmenty. Tego AUDIT-1 nie dowiódł, a taki przypadek otwiera REPLAN/provenance oraz mapowanie istniejących Assignmentów na nowe demandy.

**Wymagana korekta kontraktu:**

> Automatyczna regeneracja w T041 dotyczy potwierdzonego C-04: current WORKING **bez Assignmentów**, którego persisted demands różnią się materialnie od demandów generowanych z aktualnego katalogu. Następny PLAN tworzy nowy WORKING przez istniejący `create_schedule_version`; stary WORKING pozostaje niezmieniony w historii. WORKING zawierający Assignmenty nie jest w T041 automatycznie migrowany na nowy katalog — taki przypadek wymaga osobnego OWNER_DECISION, jeżeli wystąpi.

Nie wolno używać `replace_working_snapshot()` do mutacji starej wersji.

`Materialna zmiana katalogu` nie wymaga nowego fingerprintu w DB. Powinna być wykrywana przez porównanie persisted demand snapshotu z aktualnie generowanym zestawem demandów po ich semantycznych polach, ignorując wyłącznie scope/version id.

## 3. COVERAGE-01 — dopisać invariant równoczesnych niezależnych demandów

Macierz T41-A07–A12 poprawnie chroni dwie strony istniejącego konfliktu:

- legalne occurrence katalogu mogą się nakładać;
- T022 zabrania ślepego ufania `covers_demand_id`, bo manual/spanning PRIMARY może rzeczywiście pokrywać inne segmenty czasu.

Brakuje jednak literalnego invariant-u zapobiegającego temu, aby jeden PRIMARY został policzony jako obsada dwóch **równoczesnych, niezależnych** demandów tylko dlatego, że geometrycznie przecina oba.

**Wymagana korekta kontraktu:**

> `covers_demand_id` jest lineage/disambiguation dla równoczesnych niezależnych demandów, a geometria potwierdza, że Assignment rzeczywiście pokrywa wskazany demand. Jeden PRIMARY nie może zaspokajać dwóch niezależnych required occurrences w tym samym odcinku czasu. Jednocześnie geometria nadal musi wykrywać legalne/manual spanning na nierównoczesnych sąsiadujących segmentach zgodnie z T022.

Dodać acceptance case **T41-A13**:

- dwa nakładające się niezależne demandy;
- dwie osoby PRIMARY;
- oba Assignmenty geometrycznie przecinają oba demandy;
- oba `covers_demand_id` wskazują ten sam demand;
- drugi demand pozostaje undercovered — geometria nie może sama „przydzielić” mu jednej z tych osób.

Validator pozostaje jedynym ownerem `COVERAGE-01`.

## 4. Ręczna korekta — jawnie objąć FINAL przez istniejący child lifecycle

Checkpoint C mówi, że skrót „Ręczna korekta” prowadzi do `MonthlyPlanning`, ale obecny frontend nie pozwala wybrać Assignmentu do korekty, gdy current version jest FINAL (`onSelectAssignment` jest wtedy wyłączony).

Backendowy `apply_manual_correction()` już ma właściwy mechanizm: bierze current snapshot i tworzy **nowy child ScheduleVersion** przez `create_schedule_version`, więc parent FINAL może pozostać niezmieniony.

**Wymagana korekta C06:**

> Na current FINAL wejście przez „Ręczna korekta” pozwala wybrać istniejący przyszły Assignment i wykonać istniejącą operację manual correction. Powstaje nowy child WORKING; parent FINAL i jego snapshot pozostają byte-for-byte niezmienione. Nie powstaje drugi backend korekty ani mutacja FINAL.

## Potwierdzone elementy bez korekty

1. `warnings` nie wymagają nowego persistence ani DTO: `open_month()` ponownie składa durable state, API `MonthViewOut` już zwraca warnings, a `MonthlyPlanning` ma istniejący banner. Wymóg „warning po refreshu” jest więc wykonalny przez reuse.
2. Fresh empty-WORKING może użyć istniejącego `create_schedule_version()` i atomowego current pointer; nowa encja/lifecycle nie są potrzebne.
3. PDF może użyć jednego istniejącego export response: ten sam Blob/bytes dla preview i download; bez drugiego generatora/endpointu.
4. `Room.tsx` już deklaruje konceptualnie, że „Ręczna korekta” i „Wydruk Grafiku” są skrótami do jednego MonthlyPlanning, lecz runtime nadal renderuje Wydruk osobno. T041 naprawia istniejący seam, nie dodaje nowego produktu.
5. T040 jest na bazie i T041 nie powinno ponownie projektować H24; tylko regresja.

## Verdict

**WYMAGA KOREKTY PRZED PREIMPLEMENTATION AUDIT.**

Korekta ma być wyłącznie kontraktowa i ograniczona do czterech punktów powyżej. Bez poszerzenia scope, bez nowej architektury, bez zmian kodu produktu. Po ich zamknięciu kontrakt nadaje się do niezależnego preimplementation reduction gate.

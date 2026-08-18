# TASK_CONTRACT

TASK_ID: ROTA-T012
TITLE: Katalog zmian 24h / 12h / INNY + odpoczynek per okres pracy
STATUS: DRAFT FOR CODEX PREIMPLEMENTATION AUDIT — ROUND 1
DATE: 2026-08-18
ARCHITECT_ROLE: ChatGPT (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: no — decyzje właściciela z 2026-08-15/16 są zamknięte

INTEGRATED_BASE_SHA: 3a389bcbac274566ef6cdc5b7ddd0d66f4873958
BASE_BRANCH_AT_FREEZE: main
DEPENDS_ON: ROTA-T016 merged in base
BLOCKS: ROTA-T013; ROTA-T017 should not be implemented before T012 stabilizes solver semantics

## CEL

Rozszerzyć istniejący model zmian bez tworzenia nowego `ShiftKind`:

- SiteProfile ma katalog pozycji `24h`, `12h`, `INNY`;
- każda pozycja katalogu ma konfigurowany przez koordynatora wymagany odpoczynek;
- pozycje katalogu mogą obowiązywać tylko w wybrane dni tygodnia;
- `24h` jest zapisywane i pokazywane jako dwie kolejne istniejące zmiany D/N tej samej osoby;
- REST-01 staje się regułą zależną od faktycznie odbytego okresu pracy, a nie jedną globalną stałą 11 h;
- na obiekcie mieszanym pracownik ma per-Site checkbox `24`, domyślnie włączony;
- solver najpierw szuka pełnego grafiku bez awaryjnego łączenia dwóch zwykłych 12h, a dopiero po niepowodzeniu ukrycie uruchamia drugi przebieg z takim łączeniem;
- ręczne naruszenie REST-01 nadal jest możliwe przez istniejącą manual correction, z Deviation/finalize oraz dodatkowym trwałym DecisionRecord.

T012 NIE implementuje UI. Dostarcza domenę, persistence i application/planning semantics, z których Panel skorzysta później przez istniejące entry points.

## DECYZJE WŁAŚCICIELA — WIĄŻĄCE

1. Katalog SiteProfile zawiera pozycje `24h`, `12h`, `INNY`. Dla `INNY` koordynator podaje długość; każda pozycja ma własny `required_rest_hours`.
2. Program nie oblicza prawa pracy i nie waliduje prawidłowości prawnej tej liczby. Egzekwuje wpisaną wartość jako HARD.
3. Katalog może mieć dowolnie wiele pozycji `INNY`, kilka pozycji aktywnych tego samego dnia oraz wpisy nakładające się czasowo. Każda aktywna pozycja generuje osobny demand.
4. Aktywność pozycji katalogu per dzień tygodnia jest HARD i jest kotwiczona do daty rozpoczęcia okresu pracy.
5. Nie wolno dodawać `ShiftKind=24`. `ShiftKind` pozostaje `D | N`.
6. Normalne `24h` ma dwie kolejne 12-godzinne komponenty D/N, pokazywane jak dotychczasowe dwa pola grafiku, ale obsadzone tym samym PRIMARY.
7. Para może zaczynać się D albo N: D→N lub N→D.
8. Dla REST obie komponenty `24h` są jednym ciągłym work period i dopiero po jego końcu stosuje się odpoczynek wpisany dla pozycji `24h`.
9. Na profilu mieszanym z możliwością 24h `SiteMembership.can_work_24h` określa kwalifikację pracownika. Default=true. Brak kwalifikacji nie może zostać automatycznie zignorowany.
10. Na profilu, którego cały aktywny katalog składa się wyłącznie z `24h`, checkbox `24` jest ukryty/ignorowany; każdy członek obsady może otrzymać 24h, o ile nie blokuje go inny istniejący HARD.
11. Pierwszy przebieg solvera nie używa awaryjnego 24h z dwóch zwykłych 12h. Jeżeli nie ma kompletnego grafiku, drugi przebieg może sparować dwie bezpośrednio kolejne zwykłe zmiany 12h tej samej osobie.
12. Awaryjne 24h nie może powstać z `INNY`; nie może też składać się z więcej niż dwóch komponentów.
13. Próby wewnętrzne są niewidoczne. Koordynator widzi tylko kompletny FEASIBLE albo końcowy DECISION_REQUIRED/TECHNICAL_ERROR.
14. Odpoczynek „podróżuje” z pracownikiem między Site: obowiązuje wartość przypisana do poprzedniego faktycznego work period.
15. Jeżeli LocalStore ma CURRENT Assignment z innego Site, cross-site REST jest sprawdzany automatycznie. Jeżeli takiego rekordu nie ma, program nie zgaduje, nie pyta i nie ostrzega — wykonuje plan na podstawie danych, które posiada.
16. Manual correction może świadomie naruszyć REST-01. Operacja nie jest blokowana; powstaje Deviation, finalize wymaga dotychczasowego potwierdzenia, a dodatkowo zapisuje się DecisionRecord o override REST.
17. T015 pozostaje wycofane. Tymczasowy pracownik dodany do bieżącej obsady jest zwykłym nazwanym Employee/SiteMembership i podlega wszystkim REST/LOAD/target/fairness.

## ARCHITECTURE DECISIONS — TECHNICZNE, WIĄŻĄCE DLA T012

### 1. D/N i rodzaj katalogu są ortogonalne

Wprowadzić osobną klasyfikację domenową `ShiftCatalogKind` o wartościach dokładnie:

- `24h`
- `12h`
- `INNY`

Nazwy członków enum są techniczne; wartości trwałe muszą być powyższe. `StandardShift.kind: ShiftKind` pozostaje D/N i opisuje istniejący lane używany przez DAY_ONLY, dostępność, SiteRule oraz wydruk.

`INNY` również ma jawny `kind: D | N`; T012 nie zgaduje D/N z długości zmiany. Dzięki temu istniejące reguły D/N mają jednoznaczną semantykę również dla niestandardowej długości.

### 2. Rozszerzenie StandardShift

Do `StandardShift` dopisać kompatybilnie na końcu:

- `catalog_kind: Optional[ShiftCatalogKind]`
- `required_rest_hours: int`
- `active_weekdays: tuple[int, ...]` — ISO 1..7

Compatibility defaults dla starych konstruktorów/testów:

- `catalog_kind=None` oznacza legacy row i jest normalizowane semantycznie: dokładnie 24 h → `24h`, dokładnie 12 h → `12h`, inna reprezentowalna dodatnia długość → `INNY`;
- `required_rest_hours=11` jest wyłącznie legacy default zgodny z przed-T012 REST-01;
- `active_weekdays=(1,2,3,4,5,6,7)`.

Każdy NOWY albo zapisany ponownie wpis po T012 ma być persistowany z jawnym `catalog_kind`.

Walidacja konfiguracji:

- `required_primary_count > 0`;
- `required_rest_hours >= 0`; program nie ma prawnego minimum;
- `active_weekdays` niepuste, bez duplikatów, wyłącznie 1..7;
- `24h` reprezentuje dokładnie 24 h;
- `12h` reprezentuje dokładnie 12 h;
- `INNY` jest dodatnią długością inną niż dokładnie 12/24 h;
- kilka pozycji i overlap są legalne;
- exact duplicate 24h capability o tym samym `kind+start_time`, ale z różnym `required_rest_hours`, jest konfiguracją niejednoznaczną dla awaryjnego pairing i musi fail-closed jako model/config error zamiast arbitralnego wyboru wartości.

### 3. Weekday semantics

`active_weekdays` jest sprawdzane na `start_datetime.date().isoweekday()` całego katalogowego occurrence.

- zwykłe 12h/INNY generuje demand tylko gdy start day jest aktywny;
- normalne 24h generuje obie komponenty, jeżeli dzień STARTU pozycji 24h jest aktywny; druga komponenta może wejść w następny dzień, nawet jeśli ten następny dzień nie należy do `active_weekdays`;
- weekday mask steruje normalnym occurrence z katalogu, nie dostępnością pracownika.

Awaryjne pairing jest osobnym mechanizmem: obecność zgodnej pozycji `24h` w SiteProfile daje capability/template dla drugiego przebiegu także wtedy, gdy jej weekday mask nie generuje tego dnia normalnego 24h demand. Twarda weekday mask nadal określa wyłącznie normalne demandy katalogowe. To realizuje rozdzielenie dwóch mechanizmów wskazane przez właściciela: stały plan obiektu vs awaryjne użycie kwalifikacji pracownika.

### 4. SiteMembership.can_work_24h

Dopisać na końcu `SiteMembership` pole `can_work_24h: bool = True` i persistować je per `(employee_id, site_id)`.

`profile_is_all_24h` oznacza: po normalizacji każda pozycja standard_shifts ma `catalog_kind=24h` i lista nie jest pusta.

- mixed profile: normalne 24h i awaryjne 24h wymagają `can_work_24h=true`;
- all-24h profile: flaga jest ignorowana;
- żaden z tych przypadków nie wyłącza DAY_ONLY, Availability, SiteRule, EXTERNAL, membership.enabled ani innych HARD.

Stabilny built-in condition code dla braku tej kwalifikacji: `SHIFT-24-01`.

### 5. ShiftDemand musi snapshotować semantykę katalogu

Do `ShiftDemand` dopisać kompatybilnie na końcu:

- `shift_kind: Optional[ShiftKind]`
- `catalog_kind: Optional[ShiftCatalogKind]`
- `required_rest_hours: Optional[int]`
- `work_period_template_id: Optional[str]`
- `work_period_component: Optional[int]`
- `emergency_24h_rest_hours: Optional[int]`

T012-generated demand ma mieć jawne wszystkie dane potrzebne do późniejszego PLAN/REPLAN bez odczytywania zmienionego SiteProfile jako źródła historii.

Normalny 12h/INNY occurrence:
- jeden demand;
- własny deterministyczny `work_period_template_id`;
- `work_period_component=1`;
- `required_rest_hours` z pozycji katalogu.

Normalny 24h occurrence:
- dwa bezpośrednio kolejne 12h demandy;
- pierwszy `shift_kind` jak katalogowy StandardShift, drugi przeciwny D↔N;
- wspólny `work_period_template_id`;
- component 1 i 2;
- obie komponenty mają ten sam `required_rest_hours` pozycji 24h i ten sam `required_primary_count`;
- independent validator wymaga identycznego zbioru PRIMARY employees na obu komponentach.

Built-in code dla złamania tej pary: `SHIFT-24-PAIR-01`.

`emergency_24h_rest_hours` jest snapshotem jednoznacznego pasującego 24h capability dla zwykłej 12h zmiany, która może być pierwszą połową awaryjnej pary. Brak matching capability = None.

Legacy persisted demand bez nowych pól pozostaje czytelny; `required_rest_hours=None` oznacza przed-T012 legacy REST 11 h, a `shift_kind=None` może użyć dotychczasowego klasyfikatora tylko jako legacy fallback.

### 6. Assignment snapshotuje rzeczywisty work period

Do `Assignment` dopisać kompatybilnie na końcu:

- `work_period_id: Optional[str]`
- `required_rest_after_hours: Optional[int]`

Semantyka:

- klucz work period jest `(employee_id, work_period_id)`;
- zwykły 12h/INNY Assignment ma własny work_period_id;
- dwie komponenty normalnego 24h tego samego employee mają ten sam work_period_id;
- dwie zwykłe 12h połączone awaryjnie mają ten sam work_period_id;
- `required_rest_after_hours` jest snapshotem rest obowiązującego po tym okresie;
- wszystkie komponenty jednego work period muszą nieść zgodną wartość rest;
- legacy `work_period_id=None` = każdy Assignment jest oddzielnym work period;
- legacy `required_rest_after_hours=None` = 11 h.

Nie wolno wyprowadzać historycznego/cross-site rest z CURRENT SiteProfile. Profile jest mutowalny; Assignment provenance jest źródłem prawdy o odbytym work period.

### 7. REST-01 staje się kierunkowe per work period

Dla dwóch kolejnych work periods A potem B tego samego employee:

`B.start - A.end >= A.required_rest_after_hours`.

To odpoczynek po A określa ścianę przed B. Nie stosować `max(rest_A, rest_B)` ani rest przyszłej zmiany B.

Komponenty w obrębie tego samego work period są ciągłą pracą i nie wymagają odpoczynku pomiędzy sobą.

Overlap dwóch różnych work periods tego samego employee pozostaje niedozwolony.

Ta sama funkcja semantyczna musi być używana w solver constraints i independent validator, ale validator ma nadal niezależnie przejść po finalnym candidate — nie wolno zastąpić walidacji samym faktem, że CP-SAT miał constraint.

### 8. Cross-site „program ma dane”

T012 nie wprowadza nowego statusu dostępności danych ani pytania do koordynatora.

Program „ma dane” wtedy, gdy istniejący assembler znajduje persisted CURRENT Assignment pracownika na innym Site i umieszcza go w `PlanningState.other_site_assignments`. Wtedy REST-01 używa zapisanego `work_period_id/required_rest_after_hours` tamtego Assignment.

Brak takiego Assignment w LocalStore = brak danych do sprawdzenia; solver nie tworzy ostrzeżenia ani DECISION_REQUIRED tylko z powodu braku historii zewnętrznej.

### 9. Hidden two-pass solver

Pierwszy przebieg:
- pełny obecny model HARD/SOFT;
- normalne katalogowe 24h są obsługiwane;
- awaryjne łączenie dwóch zwykłych 12h jest wyłączone.

Drugi przebieg jest uruchamiany tylko po PROVEN business infeasibility pierwszego przebiegu, nie po UNKNOWN/MODEL_INVALID/innym technical status.

Drugi przebieg:
- pozwala opcjonalnie zgrupować dokładnie dwie zwykłe `catalog_kind=12h` zmiany, gdy `second.start == first.end`, mają przeciwne D/N i pierwsza niesie `emergency_24h_rest_hours`;
- ten sam employee musi być eligible dla obu komponentów i — na mixed profile — `can_work_24h=true`;
- INNY nigdy nie wchodzi do pairingu;
- jeden demand nie może należeć do dwóch awaryjnych par dla tego samego solution;
- nie wolno tworzyć 36h/48h chain przez nakładające się pairingi;
- powstałe dwa Assignment mają wspólny work_period_id i rest = `emergency_24h_rest_hours`.

CP-SAT nadal wykonuje wyszukiwanie kombinatoryczne. Zakaz własnego backtrackingu/search pozostaje.

LOAD fallback/diagnosis po niepowodzeniu drugiego capped solve musi używać tego samego rozszerzonego emergency mode przy uncapped retry; inaczej silnik mógłby błędnie zgłosić brak rozwiązania, które istnieje po emergency pairing + jawnej decyzji LOAD.

Intermediate attempt/status nie może trafić do PlanningResult.

### 10. REPLAN i frozen facts

T012 nie zmienia REPLAN-MIN-01, NN, REALIZED ani frozen immutability.

- persisted work-period provenance jest częścią snapshotu i musi przetrwać parent→child;
- fixed REALIZED/frozen facts zachowują swoje provenance;
- redistributable future PRIMARY może zostać przebudowany przez solver zgodnie z dotychczasowym REPLAN;
- emergency 24 nie daje prawa do zmiany REALIZED/frozen ani do obejścia minimal reshuffle objective.

### 11. Manual REST override + DecisionRecord

`manual_edit.apply_manual_correction` nadal nie blokuje HARD violation.

Jeżeli independent validator po ręcznej korekcie zwraca co najmniej jeden `REST-01`:

1. materializować zwykłe Deviation(category=LAW, source_reference=`REST-01`) jak dotychczas;
2. zapisać dodatkowo dokładnie jeden trwały DecisionRecord dla tej child ScheduleVersion, podsumowujący wszystkie REST-01 tej korekty;
3. DecisionRecord ma być powiązany z wąskim SiteRuleVersion:
   - category `CONFIRMED_EXCEPTION`;
   - rule_kind `REST_OVERRIDE_RECORD`;
   - enforcement `INFORMATIONAL`;
   - resolution_status `RESOLVED`;
   - structured_parameters zawierają co najmniej child version id, affected assignment ids/employees oraz required/gap values dostępne z walidacji;
4. ten SiteRuleVersion jest audit record, nie executable rule: nie wchodzi do `applied_rule_version_ids`, nie osłabia przyszłego REST i jest ignorowany przez PlanningEngine zgodnie z RULE-03;
5. schedule child + Deviations + DecisionRecord/SiteRuleVersion muszą commitować atomowo albo wszystkie się wycofać.

Do osiągnięcia atomowości wolno rozdzielić `decision_ledger.record_decision` na wewnętrzny transaction-neutral helper i istniejący public wrapper z `with conn`; nie wolno budować generic transaction/workflow framework.

T012 nie rozszerza DecisionRecord na inne decision paths.

## PERSISTENCE / MIGRATION CONTRACT

Podnieść LocalStore schema version jednym krokiem (v4 → v5).

Nowe kolumny muszą odtwarzać powyższy snapshot bez odczytu aktualnego profilu:

- `standard_shifts`: catalog_kind, required_rest_hours, active_weekdays;
- `site_memberships`: can_work_24h;
- `shift_demands`: shift_kind, catalog_kind, required_rest_hours, work_period_template_id, work_period_component, emergency_24h_rest_hours;
- `assignments`: work_period_id, required_rest_after_hours.

Legacy rows:

- nie są kasowane ani przepisywane destrukcyjnie;
- old membership → can_work_24h=true;
- old standard shift → rest=11, weekdays all; catalog_kind może pozostać NULL i jest normalizowane z realnej długości przy odczycie;
- old demand/assignment z brakującym provenance używa legacy rest 11 zgodnie z zasadami wyżej;
- FINAL ScheduleVersion history pozostaje czytelna.

`REST_MIN_HOURS=11` może zostać jako stała `LEGACY_REST_MIN_HOURS` albo zachować obecną nazwę tylko jeżeli wszystkie nowe ścieżki używają jej wyłącznie jako compatibility fallback. Nie wolno używać 11 jako uniwersalnego current REST po T012.

## IMPLEMENTATION CHECKPOINTS

T012 jest jednym taskiem i jednym finalnym merge, ale implementacja ma cztery sekwencyjne checkpointy:

- A — `part_a_catalog_persistence.md`
- B — `part_b_work_period_rest.md`
- C — `part_c_emergency_24h.md`
- D — `part_d_manual_override.md`

Każdy checkpoint ma osobny commit/serię commitów i niezależny audit Codexa przed przejściem dalej. Nie merge'ować A/B/C osobno do main.

## UNION TASK_SCOPE

Zamknięty union scope dla całego T012:

- arch/spec.md
- arch/FROZEN.lock
- rota/constants.py
- rota/domain.py
- rota/application/assembler.py
- rota/application/bootstrap.py
- rota/application/manual_edit.py
- rota/application/rule_decisions.py
- rota/application/deviation_mapping.py
- rota/persistence/db.py
- rota/persistence/site_profile_repository.py
- rota/persistence/employee_repository.py
- rota/persistence/schedule_repository.py
- rota/persistence/schedule_lifecycle.py
- rota/persistence/schedule_validation.py
- rota/persistence/decision_ledger.py
- rota/planning/shift_catalog.py
- rota/planning/eligibility.py
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/validator.py
- rota/planning/engine.py
- rota/planning/work_periods.py
- tests/test_t012_a_catalog_persistence.py
- tests/test_t012_b_work_period_rest.py
- tests/test_t012_c_emergency_24h.py
- tests/test_t012_d_manual_override.py

`rota/planning/work_periods.py` oraz cztery testy są jedynymi z góry autoryzowanymi nowymi plikami produkcyjno-testowymi. Task/pipeline artifacts nie liczą się do tej liczby.

Plik z union scope może zostać niewykorzystany; CC nie musi go dotykać tylko dlatego, że jest autoryzowany. Każdy plik spoza listy = STOP i amendment kontraktu przed zmianą.

W szczególności poza scope:

- frontend/UI/bridge;
- rota/application/durable_inputs.py — istniejące `update_profile` / `update_membership` mają zostać ponownie użyte;
- rota/application/plan_ops.py — istniejąca orkiestracja PLAN/select ma przenosić rozszerzone dataclasses bez nowej fasady;
- rota/planning/site_rules.py — INFORMATIONAL już jest nieexecutowalne; nie dodawać REST_OVERRIDE_RECORD do executable catalog;
- ROTA-REG-001 fixture/oracle;
- T013, T017;
- jakikolwiek T015/external temp-worker mechanism.

## REQUIRED TEST PRINCIPLES

1. Wszystkie istniejące 555 testów są nadal regression oracle; kompatybilne defaulty mają zapobiec masowej edycji fixture'ów.
2. Nowe testy używają public behavior i real persistence tam, gdzie testuje się restart/cross-site/history.
3. Wymagany migration test z prawdziwej v4 bazy do v5 z non-empty profile/membership/schedule; po reopen provenance/defaulty są zgodne i dane nie znikają.
4. ROTA-REG-001 nadal PASS; jego fixture nadal semantycznie używa 11 h jako skonfigurowanego/legacy rest dla swoich standardowych zmian.
5. Każdy FEASIBLE z normalnym/emergency 24 musi przejść independent validate HARD PASS.
6. Testy muszą odróżniać normalne catalog 24 od emergency 24.
7. Cross-site test musi zmienić current SiteProfile po zapisaniu wcześniejszego Assignment i udowodnić, że historyczny rest NIE zmienia się retroaktywnie.
8. Manual override test musi udowodnić atomic DecisionRecord + Deviation i brak executable effect tego recordu.
9. `git diff --check`, Ruff, dependency-boundary scan, `python guard.py check arch/spec.md` PASS.
10. Full suite PASS.

## FROZEN CONTRACT AMENDMENT

T012 jawnie zmienia `arch/spec.md` i `arch/FROZEN.lock` na branchu kontraktowym przed implementacją. Amendment musi literalnie objąć:

- SiteProfile catalog fields i weekday semantics;
- SiteMembership `can_work_24h`;
- ShiftDemand/Assignment work-period provenance;
- SHIFT-01 normal 24 representation i same-person pairing;
- REST-01 per-work-period, kierunkowy i cross-site;
- hidden two-pass emergency 24;
- manual REST override + additional DecisionRecord;
- usunięcie globalnego 11h jako bieżącego prawa systemu, pozostawiając je wyłącznie jako legacy compatibility/default dla danych sprzed T012 oraz konkretny parametr ROTA-REG-001.

Po zmianie:

```text
python guard.py freeze --recompute arch/spec.md
python guard.py check arch/spec.md
```

Nie wolno obchodzić FROZEN_LOCK ani zmieniać guard.py/backend.py.

## ENGINEERING GATES

- SIZE_FILE <= 600 / SIZE_FUNC <= 50 / Ruff PASS;
- brak własnego search/backtracking poza OR-Tools CP-SAT;
- żadnej nowej pass-through façade;
- żadnej równoległej implementacji REST w solver i validator o rozbieżnej semantyce czasu; wspólny pure model work-period jest dozwolony, ale independent validator nadal wykonuje własne przejście po candidate;
- `TOTAL_LINES` / `RATIO` podlegają backend.py; każda wartość `WYMAGA_DECYZJI` wymaga finalnej konkretnej akceptacji architekta/owner gate, nie jest zaakceptowana z góry;
- final acceptance dotyczy dokładnego audited SHA.

## PREIMPLEMENTATION GATE

CC NIE zaczyna A przed PASS Codexa dla:

- tego briefu;
- czterech part contracts;
- amendment `arch/spec.md`;
- nowego `arch/FROZEN.lock`.

Codex ma szczególnie próbować znaleźć:

- miejsce, gdzie current SiteProfile nadal retroaktywnie steruje historycznym REST;
- możliwość utworzenia 24h z INNY albo chain >2;
- możliwość obejścia can_work_24h na mixed profile;
- przypadek all-24, gdzie flaga błędnie blokuje;
- normalne 24, którego dwie komponenty dostają różnych pracowników;
- cross-site REST liczone z przyszłej zmiany zamiast poprzedniego work period;
- retry po UNKNOWN ukrywający technical failure;
- LOAD fallback bez emergency mode;
- DecisionRecord wpływający na future planning;
- nieatomowy manual correction audit trail;
- masową zmianę starych testów zamiast compatibility defaults.

Wynik wymagany przed implementacją: `PASS — READY_FOR_IMPLEMENTATION_A`.

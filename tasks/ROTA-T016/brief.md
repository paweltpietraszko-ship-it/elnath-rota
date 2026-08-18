# TASK_CONTRACT

TASK_ID: ROTA-T016
TITLE: Wycofanie EMP-02 / active period z eligibility
STATUS: DRAFT FOR CODEX PREIMPLEMENTATION AUDIT — ROUND 1
DATE: 2026-08-18
ARCHITECT_ROLE: ChatGPT (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: no — decyzja właściciela z 2026-08-16 jest zamknięta

INTEGRATED_BASE_SHA: 004f8774ce8ac3aa6ff04c69ce8f0733306e6f92
BASE_BRANCH_AT_FREEZE: main
DEPENDS_ON: none

## CEL

Usunąć z Rota mechanizm `EMP-02`: `Employee.active_from` / `Employee.active_to`
nie określają już, czy pracownik może zostać przypisany do zmiany. Program
układa grafik dla pracowników należących do bieżącej obsady danego obiektu i
stosuje pozostałe jawne reguły dostępności/HARD; nie podejmuje własnej decyzji
kadrowej na podstawie globalnego okna aktywności Employee.

To jest świadoma zmiana Frozen Product Contract na podstawie decyzji
właściciela 2026-08-16, a nie naprawa implementacyjna starego EMP-02.

## DECYZJA WŁAŚCICIELA — WIĄŻĄCA

Właściciel: „My nie ustalamy czy pracownik może pracować. KROPKA. Ustalamy
grafik dla pracowników których wpisał koordynator. KROPKA.”

W konsekwencji:

1. `EMP-02` zostaje całkowicie wycofane z eligibility i niezależnego
   validatora.
2. `Employee.active_from` / `Employee.active_to` nie mogą blokować PLAN,
   REPLAN, ręcznej korekty, wyboru kandydata ani żadnego Assignment.
3. Nie wolno emitować nowego blockera/ViolationDetail/Deviation o kodzie
   `EMP-02`.
4. Źródłem prawdy o przynależności pracownika do obsady konkretnego Site
   pozostaje istniejący `SiteMembership` / `MEMBERSHIP-01`.
5. Pozostałe ograniczenia nadal obowiązują bez zmian: DAY_ONLY, Availability,
   SiteRule HARD, EXTERNAL window, REST-01, LOAD-01, COVERAGE itd.
6. EMP-03 pozostaje bez zmian: Employee nie jest strukturalnie własnością
   jednego Site.

## ARCHITECTURE DECISION — POLA LEGACY ZOSTAJĄ, SEMANTYKA OPERACYJNA ZNIKA

T016 NIE usuwa `active_from` ani `active_to` z `Employee` ani z tabeli
`employees`.

Powód techniczny: usunięcie pól wymagałoby migracji schematu i szerokiej
zmiany konstruktorów/fixture'ów, mimo że decyzję produktową można zamknąć
bezpiecznie przez odcięcie ich od całej ścieżki planowania. Nie ma wartości
produktowej w destrukcyjnej migracji tych danych w tym tasku.

Po T016 pola są wyłącznie legacy/informacyjne:

- mogą nadal być zapisywane i odczytywane;
- obecna kontrola spójności danych `active_to >= active_from` w persistence
  może pozostać — to walidacja kształtu przechowywanego metadata, nie reguła
  eligibility;
- ich obecność w modelu/storage NIE oznacza pola, które przyszły Panel musi
  pytać koordynatora jako warunek planowania;
- żaden kod wykonujący lub przygotowujący plan nie może z nich wyprowadzać
  uprawnienia do pracy.

Usunięcie samych kolumn/pól, jeśli kiedykolwiek będzie potrzebne, jest osobnym
cleanupem technicznym i nie należy do T016.

## FROZEN CONTRACT AMENDMENT

T016 jawnie zmienia `arch/spec.md`; nie wolno implementować go wyłącznie na
podstawie briefu przy pozostawieniu starego kanonu.

Minimalna wymagana zmiana `arch/spec.md`:

1. Nagłówek wersji ma odnotować amendment EMP-02 z decyzji właściciela
   2026-08-16.
2. Przy `Employee.active_from/active_to` trzeba zapisać, że są to legacy
   informational metadata bez wpływu na planning/eligibility/validation.
3. Literalne aktywne `EMP-02` należy zastąpić zapisem RETIRED: kod `EMP-02`
   nie jest już regułą eligibility i nie może być emitowany przez planning
   ani validator.
4. `MEMBERSHIP-01` musi utracić warunek „Employee active period covers
   Assignment”. Pozostają: membership enabled, pozostałe Employee
   restrictions, AvailabilityRecords i aktywne rules.
5. Żadna inna reguła Frozen Product Contract nie zmienia semantyki w T016.

Po edycji architekt/implementer wykonuje dokładnie:

```text
python guard.py freeze --recompute arch/spec.md
python guard.py check arch/spec.md
```

`arch/FROZEN.lock` jest częścią TASK_SCOPE i musi zawierać hash dokładnie
zmienionego `arch/spec.md`. Nie wolno wyłączać ani obchodzić FROZEN_LOCK w
`backend.py`.

## TASK_SCOPE

TASK_SCOPE:
- arch/spec.md
- arch/FROZEN.lock
- rota/application/deviation_mapping.py
- rota/application/training.py
- rota/planning/eligibility.py
- rota/planning/engine.py
- rota/planning/validator.py
- tests/test_audit_r12_findings.py
- tests/test_audit_r13_findings.py
- tests/test_t016_emp02_retirement.py

Powyższa lista jest zamknięta. `tests/test_t016_emp02_retirement.py` jest
jedynym nowym plikiem niebędącym artefaktem pipeline'u.

W szczególności poza TASK_SCOPE pozostają:

- `rota/domain.py` — pola legacy zostają;
- `rota/persistence/db.py` — brak migracji schematu;
- `rota/persistence/employee_repository.py` — persistence metadata zostaje;
- `rota/application/durable_inputs.py` — zwykły zapis Employee pozostaje;
- `rota/persistence/schedule_repository.py` — istniejące ogólne zapytanie
  cross-site/all-current-versions ma zostać ponownie użyte, bez nowego
  równoległego API;
- UI/Panel Sterowania;
- T012, T013, T017 i inne nowe zachowania.

## IMPLEMENTATION CONTRACT

### A. Eligibility — brak EMP-02

W `rota/planning/eligibility.py`:

- usunąć `_employee_active` albo sprawić, żeby nie istniała żadna ścieżka
  wywołująca taki gate; preferowane jest usunięcie martwego helpera;
- `_common_hard_gate` nie może sprawdzać `active_from/active_to`;
- nie może zwracać `blocked_reason="EMP-02"`;
- dotyczy identycznie LOCAL i EXTERNAL_SUPPORT;
- membership.enabled pozostaje pierwszym rzeczywistym gate'em membership;
- DAY_ONLY, Availability, SiteRule i EXTERNAL-specific checks pozostają
  niezmienione.

Nie wolno zastępować EMP-02 inną nazwą lub nowym globalnym polem czasu
zatrudnienia.

### B. Independent validator — brak EMP-02

W `rota/planning/validator.py`:

- usunąć `_check_employee_active` i jego wywołanie z `validate`;
- niezależny validator nie emituje `ViolationDetail(rule="EMP-02", ...)`;
- komentarze/docstringi mają przestać opisywać EMP-02 jako aktywny HARD;
- pozostałe niezależne kontrole HARD zostają; anty-drift rule 12 nie jest
  osłabione.

Pracownik z enabled membership może przejść validator nawet wtedy, gdy
Assignment jest przed `active_from` albo po `active_to`, o ile nie narusza
żadnego innego aktywnego HARD.

### C. Engine / DECISION_REQUIRED — EMP-02 nie jest autonomy boundary

W `rota/planning/engine.py`:

- `EMP-02` usunąć z `_FROZEN_BOUNDARY_RULES`;
- żaden DECISION_REQUIRED nie może powstać dlatego, że preserved/frozen
  Assignment leży poza `active_from/active_to`;
- nie dodawać zamiennika EMP-02 do blockerów ani unblocking options.

Frozen/REALIZED/mentor-linked Assignment nadal podlega wszystkim pozostałym
regułom zgodnie z istniejącym kontraktem.

### D. Deviation mapping — brak nowych EMP-02 Deviations

W `rota/application/deviation_mapping.py`:

- usunąć `"EMP-02": DeviationCategory.LAW` z mapowania aktywnych built-in
  rules;
- `category_for_rule("EMP-02", ...)` po T016 ma zachowywać się jak dla
  nieznanego, nieaktywnego source, a nie jak obsługiwany bieżący HARD;
- nie dodawać nowej kategorii ani aliasu dla wycofanej reguły.

HISTORIA: istniejące, już zapisane ScheduleVersion/Deviation zawierające
historyczny tekst/source_reference `EMP-02` nie są kasowane, migrowane ani
przepisywane. T016 zmienia to, co system generuje od teraz. Odczyt starego
snapshotu ma pozostać możliwy, ponieważ persistence odczytuje zapisane dane,
a nie rematerializuje ich przez `category_for_rule`.

### E. Training/readiness — active_from nie może zostać tylnym wejściem

`rota/application/training.py::_current_qualifying_training_count` używa dziś
`employee.active_from` jako początku okna dla
`get_current_assignments_for_employees`.

Po T016 jest to niedozwolone: zmiana metadata `active_from` nie może zmieniać
liczby historycznych REALIZED TRAINEE ani pośrednio readiness.

Wymagane zachowanie:

- liczyć wszystkie odpowiednie CURRENT REALIZED TRAINEE dostępne w trwałej
  historii, niezależnie od `Employee.active_from/active_to`;
- użyć istniejącego `get_current_assignments_for_employees` z neutralnym,
  technicznym zakresem czasu niezależnym od Employee metadata;
- nie tworzyć drugiego repository query/facade tylko dla T016;
- zachować dotychczasowe filtry role/state oraz CURRENT-version semantics;
- readiness pozostaje informacyjne i nadal nie wpływa na eligibility.

### F. Stare testy audytowe, których kontrakt został świadomie zastąpiony

`tests/test_audit_r12_findings.py` zawiera historyczny test
`test_finding2_inactive_external_employee_is_not_eligible`, który utrwala
stare EMP-02 dla EXTERNAL. Po T016 ma zostać przepisany jako jawna regresja
nowej decyzji: enabled EXTERNAL_SUPPORT + poprawne covering window pozostaje
eligible mimo active period, przy braku innych blockerów.

`tests/test_audit_r13_findings.py` zawiera historyczny
`test_r13_3_validator_checks_emp02`. Po T016 ma zostać przepisany tak, aby
udowodnić, że validator NIE emituje EMP-02 i że test dostarcza enabled
membership, żeby wynik nie był zaciemniony przez MEMBERSHIP-01.

Komentarz ma jasno wskazywać, że wcześniejsze findingi były poprawne dla
starego frozen contract, ale zostały świadomie superseded przez decyzję
właściciela T016. Nie wolno po prostu usunąć testów bez nowej asercji.

## WYMAGANE TESTY T016

Nowy `tests/test_t016_emp02_retirement.py` ma zawierać małą, mechaniczną
macierz. Scenariusze, nie nazwy:

1. LOCAL, enabled membership, Assignment przed `active_from` — eligibility
   dopuszcza; PLAN może osiągnąć FEASIBLE, jeśli nic innego nie blokuje.
2. LOCAL, enabled membership, Assignment po `active_to` — analogicznie.
3. EXTERNAL_SUPPORT, enabled membership + aktywne covering window, ale
   Assignment poza active period — active period nie blokuje.
4. Validator dla Assignment poza active period z poprawnym membership nie
   zawiera `EMP-02` i nie ma z tego powodu HARD FAIL.
5. Ten sam pracownik z `membership.enabled=False` nadal jest blokowany przez
   MEMBERSHIP-01/MEMBERSHIP_DISABLED — dowód, że T016 nie usuwa właściwego
   per-Site source of truth.
6. Pracownik poza active period, ale na chorobowym/urlopie/niedostępny,
   nadal jest blokowany przez odpowiedni istniejący kod — T016 nie omija
   Availability HARD.
7. Frozen/preserved future Assignment poza active period sam w sobie nie
   powoduje DECISION_REQUIRED ani `EMP-02` blockera.
8. `category_for_rule("EMP-02", {})` nie traktuje EMP-02 jako aktywnego
   built-in source.
9. Training/readiness: REALIZED TRAINEE sprzed `active_from` nadal liczy się
   do historycznego count/promocji; przesunięcie `active_from` nie zmienia
   tego wyniku.
10. Persistence compatibility: zapis/odczyt Employee z legacy
    `active_from/active_to` nadal round-tripuje — jeżeli istniejący test
    persistence już dowodzi dokładnie tego zachowania, nie duplikować go w
    nowym pliku; wystarczy wskazać istniejący zielony test w raporcie.

Testy mają dowodzić braku EMP-02 przez publiczne zachowanie, nie tylko przez
`grep`/brak funkcji.

## REGRESSION / NON-GOALS

T016 NIE zmienia:

- DAY_ONLY-01 ani jego wąskiego exception;
- Availability semantics;
- SiteRule execution;
- REST-01;
- LOAD-01;
- COVERAGE-01;
- ExternalSupportWindow poza usunięciem active-period gate;
- target_hours, WorkBalance, fairness;
- REPLAN-MIN-01;
- NN;
- ScheduleVersion history;
- readiness jako informacji;
- danych Employee należących do innych Site — EMP-03 pozostaje.

Nie wolno:

- dodawać nowego HR/employment-status mechanizmu;
- przenosić active period do SiteMembership pod inną nazwą;
- dodawać `can_work`, `employment_active`, dat membership itp.;
- usuwać historycznych ScheduleVersion/Deviation;
- robić migracji DB usuwającej kolumny;
- rozszerzać T016 na Panel/UI;
- osłabiać pozostałych HARD w celu uzyskania FEASIBLE.

## ACCEPTANCE MATRIX

Codex po implementacji musi niezależnie potwierdzić co najmniej:

- `EMP-02` nie jest emitowany przez eligibility, validator, engine ani
  deviation materialization;
- dwa Employee o identycznym SiteMembership/Availability/rules, ale skrajnie
  różnych `active_from/active_to`, mają identyczny verdict eligibility dla
  tego samego demandu;
- to samo dla LOCAL i EXTERNAL_SUPPORT (przy poprawnym window);
- disabled/missing SiteMembership nadal blokuje;
- wszystkie pozostałe HARD nadal blokują identycznie jak przed T016;
- historyczny training przed `active_from` nie znika z readiness count;
- legacy Employee metadata nadal round-tripuje bez migracji;
- stare ScheduleVersion pozostają odczytywalne;
- pełna suite PASS po świadomej aktualizacji dwóch superseded regression
  tests;
- ROTA-REG-001 PASS bez zmiany fixture/oracle;
- dependency boundary scan PASS;
- Ruff PASS;
- `python guard.py check arch/spec.md` => STATUS PASS;
- `git diff --check` PASS.

## ENGINEERING GATES

- TASK_SCOPE zamknięty jak wyżej;
- max 1 nowy plik nie-pipeline (`tests/test_t016_emp02_retirement.py`);
- żadnej zmiany progów backend.py/guard.py;
- `FROZEN_LOCK` musi być zielony po legalnym `freeze --recompute`;
- `SIZE_FILE` / `SIZE_FUNC` / Ruff PASS;
- `RATIO` i `TOTAL_LINES` podlegają zwykłym mechanicznym progom backend.py;
  ewentualne `WYMAGA_DECYZJI` wymaga finalnej, konkretnej akceptacji wartości,
  nie jest automatycznie zaakceptowane tym briefem.

## PREIMPLEMENTATION GATE

CC NIE implementuje produkcji przed audytem Codexa tego kontraktu i zmiany
frozen canonu.

Codex ma odpowiedzieć, czy brief + `arch/spec.md` po amendment:

1. jednoznacznie wycofują EMP-02 bez osłabienia MEMBERSHIP-01 i innych HARD;
2. nie zostawiają ukrytego wpływu `active_from/active_to` przez training;
3. zachowują historię bez migracji/destrukcji;
4. mają wystarczający i zamknięty TASK_SCOPE;
5. nie wprowadzają drugiego źródła prawdy ani nowego HR modelu.

Wynik wymagany przed implementacją: `PASS — READY_FOR_IMPLEMENTATION`.

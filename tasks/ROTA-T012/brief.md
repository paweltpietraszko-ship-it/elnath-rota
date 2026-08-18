# TASK_CONTRACT

TASK_ID: ROTA-T012
TITLE: Katalog zmian 24h / 12h / INNY + odpoczynek per okres pracy
STATUS: READY FOR CODEX PREIMPLEMENTATION AUDIT — ROUND 2
DATE: 2026-08-18
ARCHITECT_ROLE: ChatGPT (architekt)
IMPLEMENTER_ROLE: CC
AUDITOR_ROLE: Codex
FINAL_ARCHITECTURAL_ACCEPTANCE: architekt
OWNER_ACCEPTANCE_REQUIRED_FOR_PRODUCT_DECISIONS: no — T012-R1-3 zamknięte decyzją właściciela A z 2026-08-18

INTEGRATED_BASE_SHA: 3a389bcbac274566ef6cdc5b7ddd0d66f4873958
BASE_BRANCH_AT_FREEZE: main
DEPENDS_ON: ROTA-T016 merged in base
BLOCKS: ROTA-T013; ROTA-T017 should not be implemented before T012 stabilizes solver semantics

## ROUND 1 AUDIT STATUS

Codex Round 1 na SHA `aba48a4cfcf1ef18aea9bb4bcb12766a08cef191` zakończył się FAIL przed implementacją.

- T012-R1-1 — brak literalnego `TASK_SCOPE:`: CLOSED. Poniżej istnieje maszynowo czytelny marker wymagany przez `backend.py::read_task_scope()`.
- T012-R1-2 — pięć nowych plików przy `MAX_NEW_FILES=2`: CLOSED. T012 ma dokładnie dwa nowe pliki nie-pipeline: `rota/planning/work_periods.py` i `tests/test_t012.py`.
- T012-R1-3 — emergency 24h przez granicę miesiąca: CLOSED decyzją właściciela **A / TAK** z 2026-08-18. Cross-month i cross-year emergency pairing są wymagane.

Round 1 potwierdził spójność wcześniejszego Frozen amendmentu, `guard.py`, `git diff --check` i bazowej regresji 555/555. Po zamknięciu R1-3 Frozen Product Contract jest ponownie aktualizowany i re-freezowany; implementacja A nie startuje przed PASS Codexa Round 2.

## CEL

Rozszerzyć istniejący model zmian bez tworzenia nowego `ShiftKind`:

- SiteProfile ma katalog pozycji `24h`, `12h`, `INNY`;
- każda pozycja katalogu ma konfigurowany przez koordynatora wymagany odpoczynek;
- pozycje katalogu mogą obowiązywać tylko w wybrane dni tygodnia;
- `24h` jest zapisywane/pokazywane jako dwie kolejne istniejące zmiany D/N tej samej osoby;
- REST-01 zależy od faktycznego work period i jego persisted provenance, nie od jednej globalnej stałej 11 h;
- na profilu mieszanym pracownik ma per-Site checkbox `24`, domyślnie włączony;
- solver najpierw szuka pełnego grafiku bez awaryjnego łączenia zwykłych 12h, a po PROVEN business infeasibility ukrycie uruchamia drugi przebieg;
- awaryjne 24h działa także przez granicę miesiąca/roku, bez mutowania poprzedniego ScheduleVersion;
- ręczne naruszenie REST-01 nadal jest możliwe przez manual correction, z Deviation/finalize i dodatkowym DecisionRecord.

T012 NIE implementuje UI. Dostarcza domenę, persistence i application/planning semantics dla przyszłego Panelu Sterowania.

## DECYZJE WŁAŚCICIELA — WIĄŻĄCE

1. Katalog SiteProfile zawiera `24h`, `12h`, `INNY`. Dla `INNY` koordynator podaje długość; każda pozycja ma własny `required_rest_hours`.
2. Program nie oblicza/nie waliduje prawa pracy. Egzekwuje wpisany odpoczynek jako HARD.
3. Katalog może mieć dowolnie wiele INNY, kilka pozycji tego samego dnia oraz overlap; każda aktywna pozycja generuje osobny demand.
4. `active_weekdays` pozycji katalogu jest HARD i kotwiczy się do daty rozpoczęcia occurrence.
5. Nie powstaje `ShiftKind=24`; `ShiftKind` pozostaje `D | N`.
6. Normalne 24h ma dwie kolejne 12h komponenty D/N tego samego PRIMARY; D→N i N→D są dozwolone.
7. Dla REST dwie połówki 24h są jednym ciągłym work period; odpoczynek jest wymagany dopiero po jego końcu.
8. Mixed profile z 24h: `SiteMembership.can_work_24h` kwalifikuje pracownika, default=true. All-24h profile ignoruje tę flagę.
9. Pierwszy solver pass nie używa awaryjnego 24h; drugi może sparować dokładnie dwie bezpośrednio kolejne zwykłe 12h tej samej osobie.
10. Awaryjne 24h nigdy nie powstaje z INNY i nie tworzy 36h/48h chain.
11. Próby wewnętrzne są niewidoczne; użytkownik widzi tylko finalny FEASIBLE / DECISION_REQUIRED / TECHNICAL_ERROR.
12. Odpoczynek „podróżuje” z pracownikiem między Site i wynika z faktycznie odbytego poprzedniego work period.
13. Gdy LocalStore ma CURRENT assignment z innego Site, cross-site REST jest sprawdzany. Gdy danych nie ma, program nie zgaduje, nie pyta i nie ostrzega tylko z powodu ich braku.
14. Manual correction może świadomie naruszyć REST-01; Deviation i finalize acknowledgement pozostają, a T012 dodaje DecisionRecord audit trail.
15. T015 pozostaje wycofane; tymczasowy pracownik w bieżącej obsadzie jest zwykłym Employee/SiteMembership.
16. **T012-R1-3 / OWNER DECISION A, 2026-08-18:** awaryjne 24h może łączyć dwie kolejne zwykłe 12h także przez granicę miesiąca i roku, np. N 31.08 + D 01.09 oraz N 31.12 + D 01.01.

## ARCHITECTURE DECISIONS — TECHNICZNE, WIĄŻĄCE

### 1. D/N i rodzaj katalogu są ortogonalne

Dodać `ShiftCatalogKind` o trwałych wartościach dokładnie `24h`, `12h`, `INNY`. `StandardShift.kind: ShiftKind` pozostaje D/N i jest używany przez istniejące reguły D/N, DAY_ONLY, SiteRule i wydruk. INNY również ma jawny D/N; system nie zgaduje lane z długości.

### 2. StandardShift

Na końcu dodać kompatybilnie:

- `catalog_kind: Optional[ShiftCatalogKind]`;
- `required_rest_hours: int`;
- `active_weekdays: tuple[int, ...]` ISO 1..7.

Legacy defaults:

- `catalog_kind=None` → normalize z realnej długości: 24h / 12h / INNY;
- `required_rest_hours=11` wyłącznie legacy default;
- `active_weekdays=(1,2,3,4,5,6,7)`.

Walidacja: required_primary_count >0; rest >=0; weekdays niepuste, bez duplikatów, 1..7; 24h dokładnie 24h; 12h dokładnie 12h; INNY dodatni i nie 12/24. Overlap i wiele wpisów są legalne. Konflikt dwóch matching 24h capability o tym samym start/kind, ale różnych rest, fail-closed.

### 3. Weekday semantics

Weekday jest sprawdzany na dniu startu occurrence. Normalne 24h generuje obie połówki, jeśli dzień startu jest aktywny; druga może wejść w inny weekday. Weekday mask steruje normalnym katalogowym occurrence. Emergency capability jest osobnym mechanizmem i może ratować dwie zwykłe 12h także wtedy, gdy tego dnia pozycja 24h nie generuje normalnego demandu.

### 4. SiteMembership.can_work_24h

Dodać `can_work_24h: bool = True` per `(employee_id, site_id)`.

- mixed profile: wymagane dla normalnego i emergency 24h;
- all-24h profile: ignorowane;
- nie wyłącza DAY_ONLY, Availability, SiteRule, EXTERNAL, membership.enabled ani innych HARD.

Stable code braku kwalifikacji: `SHIFT-24-01`.

### 5. ShiftDemand snapshot

Na końcu dodać kompatybilnie:

- `shift_kind: Optional[ShiftKind]`;
- `catalog_kind: Optional[ShiftCatalogKind]`;
- `required_rest_hours: Optional[int]`;
- `work_period_template_id: Optional[str]`;
- `work_period_component: Optional[int]`;
- `emergency_24h_rest_hours: Optional[int]`.

T012-generated demand ma jawne provenance; current SiteProfile nie służy do rekonstrukcji historycznego REST.

Normalne 12h/INNY: jeden demand, component=1, własny template id, own rest.

Normalne 24h: dwa bezpośrednio kolejne 12h demandy, D↔N, wspólny template id, components 1/2, ten sam rest/count; validator wymaga identycznego zbioru PRIMARY. Code mismatchu: `SHIFT-24-PAIR-01`.

Zwykła 12h może snapshotować `emergency_24h_rest_hours` tylko z jednoznacznej 24h capability. Legacy demand bez nowych pól pozostaje czytelny; legacy rest=11.

### 6. Assignment snapshot i work period

Na końcu dodać kompatybilnie:

- `work_period_id: Optional[str]`;
- `required_rest_after_hours: Optional[int]`.

Semantyka:

- identity = `(employee_id, work_period_id)`;
- zwykły 12h/INNY ma własny work_period_id;
- normalne 24h oraz same-month emergency 24h mają wspólny work_period_id dla dwóch komponentów;
- legacy missing work_period_id = osobny period; legacy missing rest = 11 h;
- normalnie wszystkie komponenty utworzone razem mają spójny rest.

**Cross-month emergency extension jest wąskim wyjątkiem od wymogu identycznej zapisanej wartości rest na obu historycznych komponentach:** poprzedni boundary Assignment pozostaje niezmieniony; Assignment tworzony w późniejszym miesiącu reuse jego `work_period_id` i zapisuje rest 24h. W złożonym periodzie odpoczynek po całości bierze się z terminalnej/najnowszej komponenty; wcześniejsza wartość rest jest ignorowana wewnątrz ciągłej pracy.

### 7. REST-01

Dla kolejnych work periods A→B: `B.start - A.end >= A.required_rest_after_hours`.

Rest B nie wpływa wstecz. Komponenty jednego periodu nie mają internal REST. Dwa różne periods nie mogą overlapować. Normalne/emergency 24h używa po końcu rest 24h capability. Ta sama semantyka działa same-site, cross-month, cross-site. Historyczny/cross-site rest pochodzi z persisted provenance, nie current profile.

Wspólny pure moduł `rota/planning/work_periods.py` może normalizować czas/provenance dla solvera i validatora, ale independent validator nadal niezależnie przechodzi finalny candidate i emituje findings.

### 8. Cross-site data boundary

Program „ma dane”, gdy assembler znajduje persisted CURRENT Assignment innego Site i dodaje go do `other_site_assignments`. Brak takiego rekordu nie tworzy syntetycznego warning/DECISION_REQUIRED.

### 9. Hidden two-pass solver

Pass 1: pełny obecny model + normalne katalogowe 24h, emergency disabled.

Pass 2 tylko po PROVEN business infeasibility pass 1: emergency enabled. UNKNOWN/MODEL_INVALID/technical status nie uruchamia retry maskującego błąd.

Same-month emergency pair: dokładnie dwa zwykłe 12h demandy, bezpośrednio kolejne, przeciwne D/N, pierwsza ma emergency rest snapshot, ten sam eligible employee, mixed profile wymaga `can_work_24h=true`. INNY wykluczone. Demand nie może należeć do dwóch par. LOAD uncapped diagnosis po pass 2 musi korzystać z tego samego emergency-enabled modelu.

### 10. Cross-month / cross-year emergency 24h — decyzja A

Cross-month pair powstaje wyłącznie podczas PLAN/REPLAN **późniejszego miesiąca**. Wcześniejszy ScheduleVersion nie jest mutowany i wcześniejszy plan nie tworzy przyszłego demandu następnego miesiąca.

T012 dodaje do PlanningState:

- `boundary_shift_demands: tuple[ShiftDemand, ...]` — persisted CURRENT demandy pokrywane przez `boundary_assignments`, z ich oryginalnym T012 snapshot provenance.

Boundary first-half jest legalny tylko gdy:

- PRIMARY, nie-CANCELLED;
- matching boundary demand jest zwykłym catalog_kind=12h, dokładnie 12h, z jawnym shift_kind i `emergency_24h_rest_hours`;
- boundary work period jest standalone, tj. work-period-complete boundary context pokazuje dokładnie jedną CURRENT komponentę tego employee/work_period_id;
- current demand jest zwykłym 12h, dokładnie przylega (`current.start == boundary.end`) i ma przeciwny D/N;
- ten sam employee jest eligible do current demand; mixed profile wymaga can_work_24h=true.

Po wyborze pair current Assignment:

- ma employee boundary Assignment;
- reuse boundary `work_period_id`;
- ma `required_rest_after_hours = boundary_shift_demand.emergency_24h_rest_hours`.

Boundary Assignment/ScheduleVersion pozostają niezmienione. Work-period context musi być complete: jeśli boundary assignment ma work_period_id, assembler/repository dołączają wszystkie CURRENT komponenty potrzebne do ustalenia span/count; period mający już 2 komponenty nie może zostać przedłużony do trzeciej.

Brak persisted boundary Assignment albo matching boundary demand oznacza po prostu brak tej cross-month pair candidate — bez zgadywania i bez osobnego warningu.

Te same reguły obowiązują 31.08→01.09 i 31.12→01.01.

### 11. REPLAN / frozen facts

T012 nie zmienia REPLAN-MIN-01, NN, REALIZED ani frozen immutability. Fixed facts zachowują provenance. Cross-month emergency nie daje prawa do mutowania wcześniejszego REALIZED/frozen/final Assignment; zmienia tylko candidate późniejszego miesiąca.

### 12. Manual REST override + DecisionRecord

Manual correction nadal nie blokuje HARD violation. Gdy finalna independent validation korekty zawiera REST-01:

1. materializować zwykłe Deviation LAW/REST-01;
2. dodatkowo dokładnie jeden DecisionRecord dla child version;
3. powiązany SiteRuleVersion: category=CONFIRMED_EXCEPTION, rule_kind=REST_OVERRIDE_RECORD, enforcement=INFORMATIONAL, resolution_status=RESOLVED;
4. structured_parameters zawierają child version id, affected employees/assignments/work periods i required/gap evidence;
5. audit record nie wchodzi do applied_rule_version_ids i nie wpływa na future planning;
6. child schedule + Deviations + DecisionRecord/SiteRuleVersion commitują atomowo albo rollback całości.

Dozwolony jest wąski transaction-neutral helper w decision_ledger; zakaz generic workflow/transaction framework.

## PERSISTENCE / MIGRATION CONTRACT

Schema v4 → v5, atomowo i bez utraty danych.

Nowe kolumny:

- `standard_shifts`: catalog_kind, required_rest_hours, active_weekdays;
- `site_memberships`: can_work_24h;
- `shift_demands`: shift_kind, catalog_kind, required_rest_hours, work_period_template_id, work_period_component, emergency_24h_rest_hours;
- `assignments`: work_period_id, required_rest_after_hours.

`boundary_shift_demands` jest assembled view z persisted CURRENT ScheduleVersion; nie jest nową tabelą.

Legacy: membership can_work_24h=true; standard shift rest=11/weekdays all/catalog kind normalize on read; old demand/assignment missing provenance uses legacy 11; FINAL history nie jest przepisywana. `REST_MIN_HOURS=11` może pozostać tylko jako legacy fallback, nie universal current rule.

## IMPLEMENTATION CHECKPOINTS

T012 jest jednym taskiem i jednym finalnym merge:

- A — `part_a_catalog_persistence.md`;
- B — `part_b_work_period_rest.md`;
- C — `part_c_emergency_24h.md`;
- D — `part_d_manual_override.md`.

Każdy checkpoint ma audit Codexa przed następnym. A/B/C nie są merge'owane osobno do main.

## UNION TASK_SCOPE

Zamknięty union scope. Poniższy literalny marker jest wymagany przez backend.py:

TASK_SCOPE:
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
- tests/test_t012.py

Dokładnie dwa autoryzowane nowe pliki nie-pipeline: `rota/planning/work_periods.py`, `tests/test_t012.py`. Wszystkie testy A–D dopisywane są do tego samego test file. Każdy plik spoza scope = STOP + amendment kontraktu.

Poza scope m.in.: frontend/UI/bridge; `rota/application/durable_inputs.py`; `rota/application/plan_ops.py`; `rota/planning/site_rules.py`; ROTA-REG-001 fixture/oracle; T013; T017; T015 mechanism.

## REQUIRED TEST PRINCIPLES

- istniejące 555 testów nadal są regression oracle;
- real v4→v5 non-empty migration + reopen;
- wiele/overlap/weekday catalog entries, D→N/N→D normal 24;
- configured directional REST, INNY, legacy 11, cross-site profile mutation proof;
- independent HARD validation każdego FEASIBLE;
- mixed/all-24 qualification;
- same-month emergency D→N/N→D, INNY exclusion, no chain >2;
- cross-month N 31.08→D 01.09 rescue oraz cross-year 31.12→01.01;
- cross-month wcześniejszy ScheduleVersion byte/semantic unchanged;
- boundary demand snapshot, nie current profile, ustala emergency rest;
- już dwukomponentowy boundary work period nie może być trzeci raz przedłużony;
- brak boundary history/demand → no pair bez invented warning;
- UNKNOWN nie maskowany retry; LOAD fallback emergency-enabled;
- manual REST override: one audit record, Deviation/finalize unchanged, atomic rollback proof;
- ROTA-REG-001 PASS; Ruff; `git diff --check`; `python guard.py check arch/spec.md` PASS.

## FROZEN CONTRACT AMENDMENT

T012 jawnie zmienia `arch/spec.md` i `arch/FROZEN.lock`. Frozen canon musi literalnie zawierać:

- SiteProfile catalog + weekday semantics;
- SiteMembership can_work_24h;
- ShiftDemand/Assignment provenance;
- normalne 24h + same-person HARD;
- directional per-work-period REST, cross-site/cross-month;
- hidden emergency retry;
- owner decision A: emergency 24h przez month/year boundary bez mutowania wcześniejszego ScheduleVersion;
- PlanningState boundary demand provenance potrzebne do tej pary;
- manual REST override + informational DecisionRecord;
- 11 h tylko jako legacy compatibility i parametr ROTA-REG-001.

Po finalnej zmianie:

```text
python guard.py freeze --recompute arch/spec.md
python guard.py check arch/spec.md
```

Nie zmieniać `guard.py` ani `backend.py`.

## ENGINEERING GATES

- SIZE_FILE <=600; SIZE_FUNC <=50; Ruff PASS;
- NEW_FILES <=2;
- bez własnego search/backtracking poza OR-Tools CP-SAT;
- bez pass-through façade / generic workflow framework;
- `TOTAL_LINES` i `RATIO` podlegają backend.py; `WYMAGA_DECYZJI` wymaga konkretnej finalnej akceptacji, nie jest pre-approved;
- final acceptance dotyczy dokładnego audited SHA.

## PREIMPLEMENTATION GATE ROUND 2

CC NIE zaczyna A przed PASS Codexa dla poprawionego briefu, A–D, `arch/spec.md` i `arch/FROZEN.lock`.

Codex ma szczególnie sprawdzić:

- literalny `TASK_SCOPE:` i new-file count <=2;
- 31.08→01.09 i 31.12→01.01 real persistence;
- brak mutacji wcześniejszego ScheduleVersion;
- boundary demand snapshot zamiast current profile reconstruction;
- no chain >2 także przez kolejne miesiące;
- current SiteProfile nie steruje retroaktywnie REST;
- INNY nie tworzy 24h;
- can_work_24h mixed/all-24;
- normalne 24h ma ten sam PRIMARY na obu komponentach;
- retry nie maskuje technical status;
- LOAD fallback ma emergency mode;
- DecisionRecord nie wpływa na future planning i jest atomowy z manual child.

Wynik wymagany: `PASS — READY_FOR_IMPLEMENTATION_A`.

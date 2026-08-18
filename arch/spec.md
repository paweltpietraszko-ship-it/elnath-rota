# ELNATH ROTA — arch/spec.md
CONTRACT_VERSION: v0.4 + decyzje właściciela 2026-08-10 + amendment EMP-02 2026-08-16 + amendment T012 2026-08-15/16
FROZEN_SOURCE: SONET_HANDOFF_BRIEF + dokumenty 01–07 z
  ELNATH_WARD_HANDOFF_FINAL_2026-08-10.zip +
  decyzje właściciela z sesji 2026-08-10 +
  decyzja właściciela 2026-08-16 o wycofaniu EMP-02 +
  decyzje właściciela 2026-08-15/16 o katalogu 24h/12h/INNY,
  odpoczynku per okres pracy i awaryjnym 24h
STATUS: maszynowy wyciąg kanonu produktu dla Ward
  Mechanical Gate i modeli implementujących

---

## SECTION 1 — DOMAIN ENTITIES

### Site
REQUIRED:
- site_id
- profile_id
- display_name
- active

SITE-01: Site.profile_id selects SiteProfile semantics.

DECYZJA_WŁAŚCICIELA 2026-08-10:
Pola SiteProfile są konfigurowalne przez koordynatora w UI.
Reguły są danymi, nie logiką w kodzie.
day_only_blocks_n: dla profilu SKLEP może być potrzebny
szerszy model ograniczeń zmiany — CONTRACT_GAP przy
dodawaniu SKLEP, nie teraz.

### SiteProfile
REQUIRED:
- profile_id
- display_name
- active

- standard_shifts: list of
  - kind: D | N
  - start_time
  - end_time
  - end_next_day: bool
  - required_primary_count: int
  - catalog_kind: 24h | 12h | INNY
  - required_rest_hours: int
  - active_weekdays: non-empty ISO weekday set 1..7

T012 CATALOG SEMANTICS — DECYZJE_WŁAŚCICIELA 2026-08-15/16:
- catalog_kind jest osobne od ShiftKind D/N; NIE istnieje ShiftKind=24;
- 24h ma dokładnie 24 h i jest reprezentowane w ScheduleVersion jako dwie
  kolejne istniejące 12h komponenty D/N tej samej osoby;
- 12h ma dokładnie 12 h;
- INNY oznacza dodatnią, reprezentowalną długość inną niż dokładnie 12/24 h;
- każda pozycja ma wpisywany przez koordynatora required_rest_hours >= 0;
  program egzekwuje tę wartość, ale nie wyprowadza ani nie waliduje prawa;
- active_weekdays jest HARD i kotwiczy occurrence do dnia STARTU pozycji;
- kilka pozycji, kilka INNY i nakładające się occurrence są dozwolone;
  każda aktywna pozycja generuje osobny demand.

LEGACY COMPATIBILITY:
- pre-T012 catalog_kind może być nieobecne i jest normalizowane z realnej
  długości: 24 h -> 24h; 12 h -> 12h; inna dodatnia -> INNY;
- pre-T012 required_rest_hours = 11;
- pre-T012 active_weekdays = wszystkie dni 1..7.

- day_only_blocks_n: bool
  (false = profil nie blokuje N dla DAY_ONLY employees)
  (OCHRONA = true; profil blokuje N dla DAY_ONLY employees;
   przyszły profil bez tej ochrony ustawia false;
   nie jest to override Employee.DAY_ONLY —
   jest to capability flag profilu)

- external_support_enabled: bool
  (false = profil nie przewiduje X/Y)

- training_s_enabled: bool
- training_s_weekdays_only: bool
  (OCHRONA = true; poniedziałek–piątek)
- training_s_default_readiness_threshold: int
  (OCHRONA = 2; liczba REALIZED TRAINEE → READY_FOR_PRIMARY)

- rolling_7d_decision_threshold_hours: int
  (LOAD-01 trigger; OCHRONA = 60;
   solver zwraca DECISION_REQUIRED gdy przekroczone;
   koordynator konfiguruje per profil przez UI)

MUST define:
- coverage generation;
- standard shift semantics;
- profile-specific rule kinds;
- profile-specific planning policy;
- interpretation of relevant Employee restrictions.

MUST NOT own:
- Employee identity;
- Coordinator identity;
- ScheduleVersion history;
- WorkBalance identity.

### LEGACY REST FALLBACK (not current SiteProfile policy)
REST_MIN_HOURS = 11 MAY remain in code only as compatibility fallback for
pre-T012 data that has no persisted required-rest provenance.

T012 current planning MUST use configured/persisted required_rest_hours for
the actual work period. 11 h is NOT a universal current legal rule in Rota.

### Coordinator
REQUIRED:
- coordinator_id
- display_name
- active

RELATION CoordinatorSiteAssociation:
- coordinator_id
- site_id
- active

### Employee
REQUIRED:
- employee_id
- display_name
- active_from
- active_to (optional)

LEGACY INFORMATIONAL METADATA — DECYZJA_WŁAŚCICIELA 2026-08-16:
- active_from / active_to mogą pozostać przechowywane dla kompatybilności;
- nie są źródłem decyzji o tym, czy pracownik może pracować;
- MUST NOT wpływać na planning, Assignment eligibility, independent validation,
  DECISION_REQUIRED ani Deviation;
- ich obecność w modelu/storage nie ustanawia obowiązkowego pola UI dla planowania.

EMPLOYEE RESTRICTION:
- DAY_ONLY enabled=true|false

EMP-01: DAY_ONLY is a stable, toggleable Employee restriction.
EMP-02: RETIRED 2026-08-16. Employee active period MUST NOT constrain Assignment eligibility and planning/validation MUST NOT emit condition code EMP-02.
EMP-03: Employee MUST NOT be structurally owned by exactly one Site.

### SiteMembership
REQUIRED:
- employee_id
- site_id
- membership_kind: LOCAL | EXTERNAL_SUPPORT
- enabled
- readiness_state: NOT_READY | READY_FOR_PRIMARY
- readiness_source: DEFAULT | COORDINATOR_OVERRIDE
- can_work_24h: bool
  (default true; kwalifikacja per Site do 24h na profilu mieszanym)

MEMBERSHIP-01: LOCAL is eligible when: membership enabled; Employee restrictions allow Assignment; AvailabilityRecords allow Assignment; active rules allow Assignment.
MEMBERSHIP-02: EXTERNAL_SUPPORT is unavailable unless a confirmed ExternalSupportWindow covers the Assignment.

SHIFT-24 MEMBERSHIP SEMANTICS:
- mixed profile z możliwością 24h: normalne i awaryjne 24h wymagają
  can_work_24h=true;
- profil, którego cały niepusty katalog składa się wyłącznie z 24h:
  can_work_24h jest ignorowane/checkbox jest zbędny;
- brak kwalifikacji 24h NIE blokuje pojedynczej zwykłej 12h/INNY;
- built-in condition code dla próby użycia 24h bez kwalifikacji = SHIFT-24-01;
- żaden wyjątek 24h nie wyłącza DAY_ONLY, Availability, SiteRule,
  membership.enabled, EXTERNAL ani innych HARD.

### ExternalSupportWindow
REQUIRED:
- window_id
- employee_id
- site_id
- start_datetime
- end_datetime
- active

OPTIONAL:
- allowed_shift_kind: D | N

WINDOW-01: One EXTERNAL_SUPPORT membership MAY have N windows.
WINDOW-02: Only active windows make X/Y eligible.
WINDOW-03: Pilot does NOT model X/Y home-site HR, balances, or schedule.

### CalendarDay
REQUIRED:
- date
- holiday

DERIVED:
- weekday from date
- weekend from weekday

CAL-01: Holiday information used by planning MUST be reproducible after application restart.
CAL-04: Holiday data MAY come from persisted CalendarDay records or a deterministic local calendar source, including a bundled structured data file. PlanningEngine MUST NOT read CSV/JSON/calendar files directly. Holiday data is resolved before planning and passed through PlanningState.
CAL-05: Historical holiday-load metrics are derived from persisted current-version Assignments joined with CalendarDay where holiday=true.

### AvailabilityRecord
KINDS:
- DAY_SHIFT_OFF
- UNAVAILABLE_24H
- LEAVE_PLAN
- LEAVE_GRANTED

REQUIRED:
- availability_id
- availability_version_id
- employee_id
- kind
- date_or_range
- active

OPTIONAL:
- supersedes_availability_version_id
- note

### SiteRule
RULE FAMILY:
- rule_id

RULE VERSION:
- rule_version_id
- site_id
- category: CLIENT_REQUIREMENT | LOCAL_RULE | CONFIRMED_EXCEPTION
- rule_kind (optional when unresolved)
- structured_parameters (optional when unresolved)
- enforcement: HARD | SOFT | INFORMATIONAL
- resolution_status: RESOLVED | NEEDS_RESOLUTION
- effective_from
- effective_to (optional)
- changed_at
- changed_by coordinator_id
- supersedes_rule_version_id (optional)

OPTIONAL:
- description
- source
- reason/note

RULE-01: Executable rule MUST be structured.
RULE-02: NEEDS_RESOLUTION remains stored and visible; MUST NOT be executed by PlanningEngine.
RULE-03: INFORMATIONAL MUST NOT constrain planning.
RULE-04: HARD is protected from automatic violation.
RULE-05: SOFT MAY be traded according to active profile planning policy.
RULE-06: Rule version history is immutable.
RULE-07: Each SiteRule belongs to exactly one Site.

T012 REST OVERRIDE AUDIT RECORD:
- manual correction that creates >=1 REST-01 violation additionally writes
  one DecisionRecord for the child ScheduleVersion;
- its SiteRuleVersion uses category=CONFIRMED_EXCEPTION,
  rule_kind=REST_OVERRIDE_RECORD, enforcement=INFORMATIONAL,
  resolution_status=RESOLVED;
- it is an audit record only: MUST NOT enter applied_rule_version_ids and
  MUST NOT weaken or constrain future planning;
- existing Deviation + acknowledgement/finalize behavior remains mandatory.

### WorkBalance
KEY:
- employee_id
- month

FIELDS:
- target_hours: Coordinator planning input
- planned_hours: derived from current ScheduleVersions
- realized_hours: derived from current ScheduleVersions
- month_balance
- unresolved_carryover: operational value; exact lifecycle OPEN

AGGREGATE:
- quarter_balance from monthly balances

WB-01: target_hours != planned_hours != realized_hours.
WB-05: Hour calculations MUST use only current ScheduleVersion for each relevant (site_id, month). Historical ScheduleVersions MUST NOT be summed into operational hour totals.

SCOPE BOUNDARY:
WorkBalance śledzi godziny narastająco w kwartale, w tym saldo nadgodzin do oddania w następnym okresie (unresolved_carryover) — to odpowiedzialność koordynatora, w zakresie Rota.
Rota NIE oblicza rozliczeń kadrowych ani list płac.

### ScheduleVersion
REQUIRED:
- version_id
- site_id
- month
- parent_version_id (optional)
- created_at
- created_by coordinator_id
- status: WORKING | WORKING_WITH_DEVIATIONS | FINAL_NO_DEVIATIONS | FINAL_WITH_DEVIATIONS
- applied_rule_version_ids

VERSION CONTENT:
- complete ShiftDemand set for month;
- complete Assignment state for month;
- Deviations belonging to version.

VER-01: A ScheduleVersion represents a complete reconstructable state of one Site/month.
VER-03: Exactly one current version reference exists for each (site_id, month).
VER-04: FINAL ScheduleVersion is immutable.

### ShiftDemand
REQUIRED:
- demand_id
- schedule_version_id
- start_datetime
- end_datetime
- required_primary_count

T012 SNAPSHOT FIELDS (required for T012-generated demand; nullable only for legacy):
- shift_kind: D | N
- catalog_kind: 24h | 12h | INNY
- required_rest_hours: int
- work_period_template_id
- work_period_component: int
- emergency_24h_rest_hours: int (optional)

DEMAND-01: ShiftDemand is persisted as part of ScheduleVersion.
DEMAND-02: OCHRONA standard required_primary_count=1.
DEMAND-T012-01: T012-generated demand MUST carry explicit shift_kind and catalog/rest provenance; current SiteProfile MUST NOT be required to reconstruct historical REST.

NORMAL 12h/INNY:
- one catalog occurrence = one demand;
- own work_period_template_id; component=1.

NORMAL 24h:
- one catalog occurrence = exactly two directly consecutive 12h demands;
- component 1 has catalog entry ShiftKind; component 2 has opposite D/N;
- both share work_period_template_id, required_rest_hours and required_primary_count;
- active_weekdays is evaluated on component-1/start date of the whole 24h occurrence;
- both components are generated even when component 2 enters a weekday not listed for that catalog entry.

EMERGENCY TEMPLATE SNAPSHOT:
- ordinary catalog_kind=12h demand MAY carry emergency_24h_rest_hours when a
  unique matching 24h capability can start at that demand;
- conflicting matching 24h capabilities with different rest values are
  model/config ambiguity and MUST fail closed, not choose an arbitrary rest;
- the 24h catalog entry's weekday mask controls normal 24h demand generation,
  while emergency capability is a separate second-pass mechanism and MAY be
  available on another weekday when two ordinary consecutive 12h demands exist.

Legacy ShiftDemand without T012 fields remains readable; missing rest means
legacy 11 h and missing shift_kind may use the pre-T012 classifier only as
legacy fallback.

### Assignment
REQUIRED:
- assignment_id
- schedule_version_id
- employee_id
- start_datetime
- end_datetime
- role: PRIMARY | TRAINEE
- state: PLANNED | REALIZED | CANCELLED
- frozen

PRIMARY:
- covers_demand_id required

TRAINEE:
- mentor_primary_assignment_id required
- covers_demand_id absent

T012 OPTIONAL-ONLY-FOR-LEGACY SNAPSHOT:
- work_period_id
- required_rest_after_hours

WORK PERIOD SEMANTICS:
- identity = (employee_id, work_period_id);
- ordinary 12h/INNY Assignment has its own work_period_id;
- two components of normal 24h for one employee share work_period_id;
- two ordinary 12h components joined by emergency 24h for one employee share work_period_id;
- all components of one work period carry one consistent required_rest_after_hours;
- legacy work_period_id absent => each Assignment is its own work period;
- legacy required_rest_after_hours absent => 11 h.

ASSIGN-01: Site is derived through ScheduleVersion. No Assignment.site_id.
ASSIGN-03: REALIZED work MUST NOT be changed by REPLAN.
ASSIGN-04: future frozen Assignment MUST NOT be changed by REPLAN.
ASSIGN-05: Manual Assignment is NOT automatically frozen.
ASSIGN-T012-01: persisted Assignment rest/work-period provenance is the source of truth for historical and cross-site REST; changing current SiteProfile MUST NOT retroactively alter it.

### Deviation
REQUIRED:
- deviation_id
- schedule_version_id
- category: LAW | CLIENT_REQUIREMENT | LEAVE_OR_TIME_OFF | HOURS | PREFERENCE | COVERAGE
- source_reference
- affected_assignment_or_employee
- acknowledged

OPTIONAL UNTIL ACKNOWLEDGED:
- acknowledged_by
- acknowledged_at
- reason

DEV-01: source_reference = SiteRule.rule_version_id or a stable built-in condition code.
DEV-02: Finalization with deviations requires conscious confirmation.

### PlanningState (not persisted)
CONCEPT PlanningState — NOT a persisted domain entity.

SCOPE:
- one Site;
- one month;
- one current ScheduleVersion context.

INCLUDES (frozen=True, wszystkie kolekcje tuple):
  site: Site
  profile: SiteProfile
  month: date

  calendar_days: tuple[CalendarDay, ...]
  boundary_assignments: tuple[Assignment, ...]

  memberships: tuple[SiteMembership, ...]
  employees: tuple[Employee, ...]
  external_windows: tuple[ExternalSupportWindow, ...]

  availability_records: tuple[AvailabilityRecord, ...]

  site_rules: tuple[SiteRuleVersion, ...]
    # tylko RESOLVED — executable; STATE-01
  unresolved_site_rules: tuple[SiteRuleVersion, ...]
    # tylko NEEDS_RESOLUTION — display only

  shift_demands: tuple[ShiftDemand, ...]
  existing_assignments: tuple[Assignment, ...]
  deviations: tuple[Deviation, ...]

  work_balances: tuple[WorkBalance, ...]
  holiday_history: tuple[Assignment, ...]
    # REALIZED w CalendarDay(holiday=True)

  other_site_assignments: tuple[Assignment, ...]
    # same Employee na innych Site; gdy CURRENT persisted dane są dostępne;
    # T012 Assignment carries work-period/rest provenance

  schedule_version_id: str

STATE-01: NEEDS_RESOLUTION SiteRule MUST NOT enter executable rule set.
STATE-02: Boundary context MUST be sufficient for cross-month validation.
STATE-T012-01: Brak other_site Assignment w LocalStore nie tworzy syntetycznego warning/blockera ani pytania; gdy persisted CURRENT data istnieją, cross-site REST jest HARD.

### PlanningEngine (no persistent state)
COMPONENT PlanningEngine — NO persistent business-state ownership.

precheck(PlanningState) OUTPUT:
- NO_OBVIOUS_SHORTAGE
- LIKELY_INSUFFICIENT + context

plan(PlanningState) OUTPUT STATUS:
- FEASIBLE
- DECISION_REQUIRED
- TECHNICAL_ERROR

validate(PlanningState, AssignmentSet | CandidateAssignment) OUTPUT:
- findings
- deviations
- source references
- explanations

---

## SECTION 2 — HARD CONSTRAINTS
Źródło: v0.4 sekcja 6.0 + decyzje właściciela
2026-08-10 oraz amendment T012 2026-08-15/16.

### SHIFT-01
- każdy SiteProfile definiuje katalog standard_shifts;
- każda pozycja ma ShiftKind D/N ORAZ catalog_kind 24h/12h/INNY;
- godziny, required_primary_count, required_rest_hours i active_weekdays są
  konfiguracją per profil wpisywaną przez koordynatora; program nie wyprowadza
  wymaganej wartości odpoczynku z prawa;
- OCHRONA legacy/default: D=05:00–17:00, N=17:00–05:00,
  required_primary_count=1, required_rest_hours=11, active_weekdays=1..7;
- każda aktywna pozycja katalogu generuje osobny wymagany occurrence; overlap
  kilku pozycji jest legalny i nie oznacza alternatywy;
- 12h i INNY generują po jednym demandzie na occurrence;
- 24h generuje dokładnie dwie kolejne 12h komponenty D→N albo N→D;
- obie komponenty normalnego 24h mają dokładnie ten sam zbiór PRIMARY;
  złamanie tego HARD ma code SHIFT-24-PAIR-01;
- na mixed profile employee użyty do normalnego 24h musi mieć
  SiteMembership.can_work_24h=true; na all-24h profile flaga jest ignorowana;
  złamanie kwalifikacji ma code SHIFT-24-01;
- S nie pokrywa PRIMARY demand.

### REST-01
- odpoczynek jest liczony pomiędzy kolejnymi work periods tego samego pracownika,
  nie pomiędzy każdą techniczną komponentą Assignment osobno;
- po work period A przed późniejszym work period B obowiązuje:
  `B.start - A.end >= A.required_rest_after_hours`;
- required_rest_after_hours pochodzi z configured catalog entry, która utworzyła
  faktyczny work period, i jest snapshotowane w Assignment;
- rest przyszłego B nie zwiększa ani nie zmniejsza ściany po A;
- komponenty jednego work period, w tym dwie połówki 24h, stanowią ciągłą pracę
  i nie wymagają internal rest;
- dwa różne work periods tego samego pracownika nie mogą się nakładać;
- normalne 24h i awaryjne 24h wymagają po końcu odpoczynku właściwego dla
  24h capability, a nie odpoczynku pojedynczej 12h połówki;
- ta sama kierunkowa semantyka obowiązuje same-site, cross-month i cross-site;
- cross-site używa persisted provenance poprzedniego Assignment, nie current
  profilu Site, na którym praca historycznie się odbyła;
- jeśli program nie posiada persisted CURRENT assignment z innego Site,
  nie zgaduje i nie tworzy warning/DECISION_REQUIRED tylko z powodu braku danych;
- żadne SOFT ani target_hours nie mogą naruszyć REST-01 automatycznie;
- manual correction MAY świadomie zapisać REST-01 violation: operacja nie jest
  blokowana, powstaje Deviation i wymagane potwierdzenie przy finalize, a T012
  dodatkowo zapisuje DecisionRecord REST_OVERRIDE_RECORD; ten record nie jest
  executable exception dla przyszłego solvera.

### SHIFT-24-01
- dotyczy wyłącznie normalnego lub awaryjnego 24h na profilu mieszanym;
- employee z can_work_24h=false nie może zostać automatycznie użyty do 24h;
- nie blokuje pojedynczej zwykłej 12h/INNY;
- all-24h profile ignoruje tę flagę.

### SHIFT-24-PAIR-01
- dwie komponenty normalnego katalogowego 24h muszą mieć ten sam zbiór PRIMARY;
- dla każdego employee tworzą jeden work period;
- independent validator sprawdza ten HARD niezależnie od CP-SAT.

### DAY_ONLY-01
- reguła aktywna tylko gdy SiteProfile.day_only_blocks_n=true;
- gdy aktywna: pracownik z Employee.DAY_ONLY=true nie może
  otrzymać N w automatycznym planowaniu;
- koordynator może świadomie wyłączyć/override tę ochronę;
- solver nie robi tego sam;
- gdy SiteProfile.day_only_blocks_n=false: profil nie stosuje
  tego ograniczenia (np. profil bez zmian N lub z innym
  modelem ograniczeń); Employee.DAY_ONLY=true jest ignorowane
  przez solver dla tego profilu.

### DAY_SHIFT_OFF-01
- DAY_SHIFT_OFF oznacza dzień wolny od rozpoczynania pracy;
- w oznaczonym dniu solver nie może rozpocząć ani zmiany D, ani zmiany N;
- zmiana N rozpoczęta poprzedniego dnia może zakończyć się o 05:00 w dniu oznaczonym DAY_SHIFT_OFF;
- takie wejście pracy 00:00–05:00 w dzień wolny jest dopuszczalne, ale stanowi gorszy wariant SOFT;
- jeżeli istnieje porównywalny kandydat zapewniający pełny dzień bez pracy, solver powinien go preferować;
- DAY_SHIFT_OFF nie oznacza UNAVAILABLE_24H.

### UNAVAILABLE-01
- UNAVAILABLE_24H blokuje każdy automatyczny Assignment, którego rzeczywisty przedział czasu koliduje z okresem niedostępności.

### LEAVE_GRANTED-01
- LEAVE_GRANTED blokuje automatyczny Assignment kolidujący z okresem urlopu;
- użycie pracownika wymaga świadomej decyzji koordynatora/override zgodnie z kontraktem.

### LEAVE_PLAN-01
- LEAVE_PLAN nie czyni pracownika nieuprawnionym;
- kolizja jest dopuszczalna tylko jako gorszy wariant SOFT, jeżeli nie istnieje lepszy kandydat;
- kolizja musi być widoczna jako ostrzeżenie.

### COVERAGE-01
- wymagane ShiftDemand muszą być pokryte w 100%;
- częściowy grafik nie jest FEASIBLE.

### LOAD-01
- dla każdego pracownika należy policzyć każde ruchome okno
  7 kolejnych dni kalendarzowych;
- próg decyzji = SiteProfile.rolling_7d_decision_threshold_hours
  (koordynator wpisuje ręcznie per profil; OCHRONA default: 60);
- więcej niż próg w dowolnym takim oknie nie może być zwykłym
  FEASIBLE bez jawnej akceptacji koordynatora;
- wynik przed akceptacją to DECISION_REQUIRED z employee,
  dokładnym oknem i liczbą godzin.

### EXTERNAL-01
- X/Y są nieuprawnieni poza aktywnym, potwierdzonym ExternalSupportWindow;
- solver nie otwiera takiego okna i nie używa X/Y samodzielnie.

### TARGET-01
- target_hours jest parametrem SOFT;
- solver nie tworzy pracy ani nie narusza HARD tylko po to, aby osiągnąć target.

---

## SECTION 3 — PLANNING OUTCOMES
Źródło: v0.4 sekcja 6.1–6.6 + amendment T012 2026-08-16.

### FEASIBLE
Jeżeli istnieją pełne rozwiązania w ramach aktywnego kontraktu:
- solver zwraca do 1–3 kandydatów;
- każdy kandydat respektuje HARD;
- kandydaci mogą różnić się jakością SOFT;
- koordynator wybiera.

Nie jest wymagane, aby solver zawsze wskazał jeden „jedyny najlepszy” grafik.

Każdy kandydat FEASIBLE MOŻE zawierać: SOFT deviations; preference compromises; hour-target deviation; warnings.

### SOFT RANKING (v0.4 §6.3)
SOFT wpływa na ranking kandydatów, nie może łamać HARD.

Aktywne czynniki SOFT:
- równomierność godzin względem target_hours
- preferencje D/N; N,N i D,D dopuszczalne jeśli HARD zachowane
- weekend fairness: monotoniczne zbliżanie do idealnie równego
  podziału pracy weekendowej wśród uprawnionych pracowników
- holiday fairness (historyczne): solver preferuje warianty
  zmniejszające nierówność historycznej pracy w święta;
  historia = persystowane Assignment +
  CalendarDay(holiday=true); nie jest prawem pracy
- DAY_SHIFT_OFF: pełny dzień wolny lepszy od wariantu
  gdzie N wchodzi do 05:00 w dzień wolny
- LEAVE_PLAN: wariant bez kolizji lepszy;
  kolizja widoczna jako ostrzeżenie

TARGET-01: target_hours jest parametrem SOFT;
solver nie tworzy pracy ani nie narusza HARD dla targetu.

### INTERNAL EMERGENCY 24h RETRY — T012

Normalne katalogowe 24h jest częścią zwykłego modelu pierwszego przebiegu.
Osobno istnieje awaryjne łączenie dwóch zwykłych 12h:

1. pierwszy przebieg szuka pełnego grafiku z emergency pairing wyłączonym;
2. jeżeli pierwszy przebieg daje pełny candidate, solver kończy — nie używa
   emergency 24h tylko po to, by poprawić SOFT;
3. dopiero po udowodnionej biznesowej niewykonalności/braku obsady/konflikcie
   pierwszy capped model jest ponawiany z emergency pairing włączonym;
4. emergency pair może objąć dokładnie dwa zwykłe catalog_kind=12h demandy,
   gdy są bezpośrednio kolejne, mają przeciwne D/N, a pierwszy ma snapshot
   emergency_24h_rest_hours;
5. ten sam employee musi być eligible dla obu; na mixed profile musi mieć
   can_work_24h=true; INNY nigdy nie uczestniczy;
6. jeden demand nie może należeć do dwóch emergency pairs i nie wolno tworzyć
   chain >2 poprzez nakładające się pairing decisions;
7. dwa Assignment awaryjnej pary tworzą jeden work period i używają rest 24h;
8. jeśli drugi capped model jest INFEASIBLE, LOAD uncapped diagnosis używa
   również emergency-enabled modelu;
9. UNKNOWN/MODEL_INVALID/technical status nie może zostać zamaskowany retry
   i zamieniony na zwykły DECISION_REQUIRED;
10. koordynator nie widzi stanów/prób pośrednich — tylko końcowy PlanningResult.

Emergency pairing jest modelowane w Google OR-Tools CP-SAT; zakaz własnego
backtrackingu/search pozostaje.

### DECISION_REQUIRED
DECISION_REQUIRED nie jest awarią. Oznacza:
- solver doszedł do granicy swojej autonomii;
- normalny kontrakt, łącznie z legalnym wewnętrznym T012 emergency retry,
  nie pozwala ukończyć bez decyzji koordynatora.

Wynik musi zawierać:
- nieobsadzony/problematic demand albo constraint powodujący zatrzymanie;
- konkretne blokery;
- możliwe klasy odblokowania;
- skutki każdej klasy, jeśli dają się deterministycznie policzyć.

Obowiązkowe typowane pola output:

blocking_shift_demands: list of
- demand_id
- start_datetime
- end_datetime

blockers: list of
- employee_id
- condition: <built-in condition code | rule_version_id>

load_blocker (present when LOAD-01 triggered):
- employee_id
- window_start: date
- window_end: date
- hours: int

Przykładowe odblokowania koordynatora:
- potwierdzenie X/Y;
- świadome ściągnięcie pracownika z wolnego;
- świadome odwołanie/override urlopu zgodnie z kontraktem;
- świadome wyłączenie DAY_ONLY;
- świadoma akceptacja >60 h / 7 kolejnych dni;
- inna jawna ręczna korekta przewidziana kontraktem.

Solver nie wybiera i nie aktywuje tych działań sam.

Po decyzji koordynatora: PlanningState zostaje zmieniony jawnie; planowanie jest uruchamiane ponownie; dopiero wtedy solver może zwrócić kandydatów.

### TECHNICAL_ERROR
TECHNICAL_ERROR oznacza awarię techniczną:
- błąd modelu;
- błąd procesu;
- nieobsłużony błąd systemowy.

Nie wolno używać TECHNICAL_ERROR jako zastępstwa dla:
- braku obsady;
- konfliktu HARD;
- wymaganej decyzji koordynatora.

---

## SECTION 4 — REUSE MAP
Źródło: v0.4 sekcja 5.

### REUSE/ADAPT: Continuity AI desktop shell
Repo: paweltpietraszko-ship-it/continuity-ai
Branch: ui/project-report-polish-v0.4
Checkpoint SHA (baza techniczna): 709cf6a1ff829725e5d6572d286963809c990c4a

Do wykorzystania jako baza techniczna:
- Tauri 2;
- React 18;
- TypeScript;
- Vite;
- istniejący układ frontend/bridge/types/components;
- wzorzec lokalnego procesu Bridge;
- UTF-8 NDJSON;
- kontrolowane błędy;
- testowy toolchain frontendu i Rust.

Nie przenosić domeny Continuity AI:
- Project Report;
- Aurora;
- evidence map;
- conversation;
- attestations;
- logiki filmu/projektów;
- żadnych syntetycznych założeń domenowych.

UI Continuity jest dawcą shellu i wzorców technicznych, nie kontraktu produktu Rota.

### REUSE SELECTIVE: Elnath Memory Engine
Repo: paweltpietraszko-ship-it/elnath-memory-engine
Branch: main
Provenance source commit SHA: 3bdcd7909373ce541be5e6bd1a5a88b99623801b

Do rozważonego reuse:
- elnath/memory/ jako domenowo neutralna baza pamięci;
- append-only/history/source/retrieval patterns, jeśli odpowiadają kontraktowi Rota.

Warunek:
- Rota bierze własny fork/kopię;
- brak wspólnej usługi;
- brak wspólnej bazy;
- brak automatycznego back-sync.

NIE używać teraz:
- elnath/guard/review jako runtime Rota;
- code-review-specific diff/patch binding;
- mechanizmów git jako części domeny planowania.

### REUSE (tech): Google OR-Tools CP-SAT
Technologia solvera: Google OR-Tools CP-SAT.

Zakaz: CC nie implementuje własnego algorytmu scheduling/search/backtracking.

CC implementuje:
1. mapowanie domeny Rota -> model CP-SAT;
2. mapowanie HARD/SOFT/DECISION gates -> constraints/objective;
3. mapowanie wyniku CP-SAT -> Rota PlanningResult.

OR-Tools wykonuje wyszukiwanie kombinatoryczne. Rota definiuje politykę produktu.

Referencyjny plik PoC (zweryfikowany rzeczywistym uruchomieniem, nie produkcyjny kod): `elnath_rota_cp_sat_poc.py`. Rola: (1) dowód wykonalności wybranej architektury; (2) wzorzec mapowania najważniejszych HARD; (3) fixture porównawczy dla implementacji produkcyjnej; (4) zabezpieczenie przed ponownym projektowaniem solvera przez implementera.

### BUILD NEW: Rota domain
Nowe i kanoniczne dla Rota (v0.4 sekcja 5.3):
- Site / SiteProfile;
- Coordinator;
- CoordinatorSiteAssociation;
- Employee / SiteMembership;
- AvailabilityRecord;
- ShiftDemand;
- Assignment;
- Deviation;
- ScheduleVersion;
- WorkBalance;
- CalendarDay;
- ExternalSupportWindow;
- SiteRule adapter do PlanningState;
- PlanningState;
- PlanningEngine;
- REPLAN;
- mapowanie wyników do kontraktu UI.

Te elementy wynikają z Rota Product Contract, nie z Continuity ani starego Elnath Code.

---

## SECTION 5 — ANTI-DRIFT RULES
Źródło: v0.4 sekcja 12. Dosłowne, z numeracją.

1. Żaden model nie może przypisać właścicielowi decyzji, której właściciel jawnie nie podjął.
2. PASS Codexa nie jest zgodą produktową.
3. Akceptacja Soneta nie zmienia Frozen Product Contract.
4. CC nie rozszerza tasku.
5. „Lepsza architektura” implementera nie jest powodem do zmiany kontraktu.
6. Test nie definiuje produktu; test weryfikuje kontrakt.
7. Kod zgodny lokalnie, ale sprzeczny z Frozen Product Contract = FAIL kanonu.
8. Materialna niejasność = CONTRACT_GAP, nie inference.
9. Merge/acceptance dotyczy dokładnie audytowanego SHA.
10. Zmiana kanonu wymaga jawnej decyzji właściciela i nowej wersji Frozen Product Contract.
11. Żaden Task Contract nie może zastąpić literalnej reguły solvera zwrotem typu „zgodnie z zasadami czasu pracy” lub „zgodnie ze Spec”; reguła potrzebna implementacji musi być obecna bezpośrednio albo jednoznacznie referencjonowana identyfikatorem Frozen Product Contract.
12. Kandydat FEASIBLE musi przejść niezależną walidację wszystkich HARD po wygenerowaniu, nawet jeżeli ten sam constraint był używany podczas wyszukiwania.
13. Zweryfikowanego PoC CP-SAT nie wolno traktować jako sugestii do ponownego zaprojektowania solvera; jest on technicznym punktem odniesienia dla implementacji produkcyjnej.
14. Jeżeli produkcyjna implementacja daje inny status lub narusza HARD dla referencyjnego scenariusza PoC, domyślnym założeniem jest błąd implementacji lub mapowania kontraktu, nie potrzeba zmiany kanonu.
15. Zmiana referencyjnego zachowania wymaga najpierw jawnej zmiany Frozen Product Contract, a dopiero potem zmiany kodu i testów.

---

## SECTION 6 — IMPLEMENTATION ORDER
Źródło: v0.4 sekcja 14. Dosłowne.

Nie zaczynać od pełnego UI.

Preferowana kolejność:
1. Frozen types / domain contract.
2. PlanningState assembly.
3. CP-SAT adapter — minimalne HARD.
4. PlanningResult / DECISION_REQUIRED.
5. SOFT ranking.
6. REPLAN.
7. Calendar + holiday history.
8. Persistence potrzebne do scenariusza end-to-end.
9. Adapter do desktop bridge.
10. Dopiero wtedy szczegółowy UI oparty o rzeczywiste API.

Każdy etap ma być osobnym lub małą grupą Task Contracts.

---

## SECTION 7 — REGRESSION ORACLE ROTA-REG-001
Źródło: dokument 06 (ELNATH_ROTA_REGRESSION_ORACLE_ROTA-REG-001.md) + fixture 07 (ELNATH_ROTA_REGRESSION_ROTA-REG-001.json).

### Wejście (fixture)
Kanoniczne dane wejściowe: `ELNATH_ROTA_REGRESSION_ROTA_REG_001.json`.

Najważniejsze warunki:
- 5 pracowników A–E;
- codziennie dokładnie 1 D i 1 N;
- C = DAY_ONLY;
- A = DAY_SHIFT_OFF 6, 17, 26;
- B = LEAVE_GRANTED 12–18;
- D = UNAVAILABLE_24H 9, 23, 24;
- brak aktywnego ExternalSupportWindow dla X/Y;
- dla tego fixture wymagany odpoczynek = 11 h;
- >60 h w dowolnym ruchomym oknie 7 dni nie może być zwykłym FEASIBLE;
- S 8 października wymaga A jako PRIMARY D;
- target_hours: A 156, B 144, C 156, D 144, E 144.

### 7 warunków PASS
Implementacja produkcyjna przechodzi ROTA-REG-001 tylko wtedy, gdy:
1. zwraca kompletny grafik pokrywający 100% D/N;
2. wynik solvera jest sukcesem (`OPTIMAL` albo produktowo zaakceptowany odpowiednik pełnego `FEASIBLE`);
3. niezależny validator zwraca `HARD PASS`;
4. żaden Assignment nie narusza DAY_ONLY, DAY_SHIFT_OFF, LEAVE_GRANTED, UNAVAILABLE_24H, REST-01, EXTERNAL-01 ani LOAD-01;
5. A jest PRIMARY D 8 października dla zaplanowanego S;
6. każde ruchome okno 7 kolejnych dni ma <=60 h na pracownika;
7. miesięczne godziny wynoszą dokładnie: A=156, B=144, C=156, D=144, E=144.

### Co jest regresją
- `INFEASIBLE`;
- `DECISION_REQUIRED`;
- `UNKNOWN` po normalnym limicie testowym;
- `TECHNICAL_ERROR`;
- częściowy grafik;
- jakikolwiek `HARD FAIL`;
- użycie X/Y;
- przekroczenie 60 h / 7 dni;
- odpoczynek <11 h w tym konkretnym fixture;
- przypisanie B kolidujące z LEAVE_GRANTED;
- przypisanie D kolidujące z UNAVAILABLE_24H;
- N dla C;
- rozpoczęcie D lub N przez A w DAY_SHIFT_OFF;
- brak A jako PRIMARY D 8 października;
- inne sumy godzin niż wynik referencyjny, dopóki target_hours pozostają częścią tego samego objective/kontraktu.

### Co NIE jest regresją
- inny konkretny układ osób w dniach, jeżeli wszystkie powyższe warunki są spełnione;
- inna kolejność równorzędnych kandydatów;
- inna treść komunikatu dla użytkownika, jeżeli jego semantyka/status są zgodne z kontraktem;
- wystąpienie dopuszczalnego ostrzeżenia SOFT dotyczącego N kończącej się o 05:00 w DAY_SHIFT_OFF.

### Reguła dla implementera
CC nie może zmienić oczekiwanego wyniku tego testu po to, aby dopasować test do nowej implementacji.

Jeżeli ROTA-REG-001 FAIL:
1. najpierw zakładamy regresję implementacji lub mapowania kontraktu;
2. poprawiamy kod;
3. zmiana oracle/fixture jest dozwolona wyłącznie po wcześniejszej jawnej zmianie Frozen Product Contract przez właściciela.

CC nie zmienia fixture/oracle.

---

## SECTION 8 — GLOBAL FORBIDDEN ACTIONS

- zastąpienie CP-SAT własnym solverem/backtrackingiem/heurystyką;
- zmiana semantyki sprawdzonych constraints;
- zmiana oracle lub fixture ROTA-REG-001;
- merge do main bez polecenia właściciela;
- wypełnianie luk własną decyzją produktową (luka = CONTRACT_GAP);
- przenoszenie domeny Continuity AI do Rota.

---

## SECTION 9 — ENGINEERING POLICY
Źródło: decyzja właściciela 2026-08-10 + techniczne dostosowanie T012.
Nie jest częścią kanonu produktu v0.4.
Obowiązuje jako standard inżynieryjny repo.

Obowiązuje każdy plik Python w repo. Backend.py egzekwuje
SIZE_FILE (max 600 linii), SIZE_FUNC (max 50 linii) i RUFF.
Poniższe reguły uzupełniają te sprawdzenia.

STRUCTURE:
- jeden moduł = jedna odpowiedzialność
- nazwy modułów odzwierciedlają domenę (site.py, solver.py),
  nie warstwy (utils.py, helpers.py, misc.py)
- żadnych plików „na wszelki wypadek" poza TASK_SCOPE

IMPORTS:
- pełne importy (from rota.domain.types import Assignment,
  nie from rota.domain.types import *)
- stdlib → third-party → local; oddzielone pustą linią
- brak nieużywanych importów (ruff egzekwuje)

TYPES:
- wszystkie sygnatury funkcji mają type hints
- byty domenowe jako @dataclass lub TypedDict
- Optional[X] zamiast X | None dla czytelności w Python 3.10-
- brak Any bez uzasadnionego komentarza

CONSTANTS:
- żadnych magic numbers w kodzie
- stałe domenowe na poziomie modułu z UPPER_SNAKE_CASE
- wartość 11 h dla REST może istnieć jako legacy compatibility constant;
  bieżący REST MUST pochodzić z work-period/catalog provenance,
  nie z globalnej stałej.

FUNCTIONS:
- max 50 linii (backend.py egzekwuje)
- jedna funkcja = jedno zadanie
- nazwa czasownikowa opisuje co robi (build_model,
  validate_rest, map_result), nie co jest (model, rest, result)
- brak zagnieżdżonych funkcji głębiej niż jeden poziom

COMMENTS:
- docstring na każdej funkcji publicznej: co robi + co zwraca
- komentarz inline = DLACZEGO, nie CO (kod mówi co)
- komentarz przy każdym constraint CP-SAT: identyfikator reguły
  (# REST-01: configured rest after previous work period)

ERROR HANDLING:
- żadnego bare except
- jawny typ wyjątku i komunikat z kontekstem
- błędy domenowe jako dedykowane klasy (RotaError,
  ContractViolation), nie generyczne ValueError/RuntimeError
- TECHNICAL_ERROR w PlanningEngine tylko dla wyjątków
  systemowych, nigdy dla staffing shortage

FORBIDDEN:
- bloki kodu dłuższe niż 50 linii bez podziału na funkcje
- powtórzony kod zamiast wyekstrahowanej funkcji
- globalne zmienne mutowalne
- print() jako mechanizm raportowania (logging lub
  strukturalny return)
- komentarze wyłączone (# x = foo()) zostawione w kodzie

DELIVERY FORMAT:
Każdy plik kończy się blokiem:
if __name__ == "__main__":
    # przykład użycia modułu — uruchamialny, nie mock

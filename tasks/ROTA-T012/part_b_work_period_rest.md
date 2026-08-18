# ROTA-T012-B — WORK PERIOD + REST

STATUS: BLOCKED UNTIL A PASS
PARENT_CONTRACT: `tasks/ROTA-T012/brief.md`

## CEL

Zastąpić bieżące uniwersalne `REST_MIN_HOURS=11` semantyką odpoczynku po faktycznym work period, z immutable provenance na Assignment i identycznym znaczeniem same-site/cross-site.

## PART B SCOPE

- rota/constants.py
- rota/domain.py
- rota/application/assembler.py
- rota/persistence/schedule_repository.py
- rota/persistence/schedule_lifecycle.py
- rota/persistence/schedule_validation.py
- rota/planning/constraints.py
- rota/planning/solver.py
- rota/planning/validator.py
- rota/planning/work_periods.py
- tests/test_t012.py

Żaden inny plik w B.

## PURE WORK-PERIOD MODEL

Nowy `rota/planning/work_periods.py` ma być wąskim pure modułem czasowym, bez CP-SAT i bez persistence. Może posiadać:

- normalizację legacy/T012 Assignment → employee work periods;
- union start/end komponentów jednego `(employee_id, work_period_id)`;
- resolved required rest;
- directional gap check;
- wykrycie overlap/inconsistent provenance.

Nie jest to façade: moduł jest jednym źródłem semantyki danych czasu, używanym przez constraint builder i independent validator. Validator nadal sam iteruje finalny candidate i emituje findings.

## WYMAGANIA REST

1. Po work period A przed B: `gap >= A.required_rest_after_hours`.
2. Rest B nie wpływa wstecz na ścianę po A.
3. Dwie komponenty tego samego work period nie mają internal REST.
4. Dwa różne work periods nie mogą overlapować.
5. Normalne 24h pair jest jednym period od początku component 1 do końca component 2 i ma configured 24h rest.
6. Zwykłe 12h/INNY period ma własny configured rest.
7. Legacy Assignment bez provenance = osobny period, rest 11.
8. LOAD nadal sumuje faktyczne Assignment hours; 24h pair = 12+12, nie dodatkowe 24.
9. Cancelled nadal nie liczy się jako praca.
10. TRAINEE pozostaje pracą dla rest/load zgodnie z istniejącą semantyką.

## NORMAL 24h SAME-PERSON HARD

Dla dwóch demand components tego samego normalnego 24h occurrence:

- każdy ma required_primary_count jak katalog;
- zbiór PRIMARY employee_id component 1 == zbiór PRIMARY employee_id component 2;
- solver constrains this directly;
- validator niezależnie potwierdza;
- mismatch = `SHIFT-24-PAIR-01`;
- na mixed profile wybór employee do normalnego 24h wymaga `can_work_24h=true`; all-24 profile ignoruje flagę;
- pozostałe D/N HARD sprawdzają każdą komponentę normalnie.

## CROSS-SITE

`PlanningState.other_site_assignments` pozostaje istniejącym kanałem.

- assembler pobiera CURRENT Assignment innych Site jak dotychczas;
- schedule repository musi zachować work_period_id/rest provenance;
- cross-site normalization scala komponenty jednego work period tego employee, nawet jeśli query zwraca obie połówki 24h;
- previous other-site period rest jest użyty przed bieżącym candidate;
- current candidate period rest obowiązuje przed późniejszym known other-site period;
- current SiteProfile nie jest consultowany w celu odtworzenia rest tamtej historii.

Brak other-site record = brak cross-site check; bez warning/query do koordynatora.

## BOUNDARY / REPLAN

Boundary assignment sprzed miesiąca oraz current/frozen facts w miesiącu zachowują provenance. REPLAN nie może przepisać rest/work_period_id REALIZED/frozen tylko dlatego, że current profile się zmienił.

Uwaga: semantyka REST dla już istniejących boundary assignments jest zamknięta w B. Osobne pytanie, czy NOWE emergency pairing może tworzyć jeden 24h work period przez granicę dwóch ScheduleVersion.month, pozostaje blockerem właścicielskim T012-R1-3 i jest rozstrzygane w Part C/Frozen amendment przed implementacją A.

## TESTY B — MINIMUM

Testy B dopisywane są do wspólnego `tests/test_t012.py` utworzonego w A.

- 12h rest 8 vs 16 daje różny eligibility/FEASIBLE;
- directional asymmetry A→B używa rest A;
- explicit 24h internal 0h gap jest legalny w tym samym period;
- po 24h obowiązuje jego rest, nie rest drugiej połówki 12h;
- explicit 24 halves różnych osób -> validator HARD fail;
- mixed can_work_24h=false blocks, all-24 ignores;
- INNY uses its own rest;
- same-site boundary prior period;
- cross-site prior 24h period blocks based on persisted rest;
- po zapisaniu historii zmiana SiteProfile.required_rest_hours NIE zmienia wyniku cross-site;
- absence of other-site record gives no invented warning/blocker;
- legacy assignments remain 11h;
- solver FEASIBLE candidate independently validates HARD PASS;
- ROTA-REG-001 PASS.

## GATE B

Codex ma wykonać niezależne directional/cross-site adversarial cases, szczególnie profile mutation after persistence.

Wynik: `PASS — READY_FOR_IMPLEMENTATION_C`.

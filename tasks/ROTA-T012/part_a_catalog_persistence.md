# ROTA-T012-A — CATALOG + PERSISTENCE

STATUS: BLOCKED UNTIL FULL T012 PREIMPLEMENTATION PASS
BASE: `3a389bcbac274566ef6cdc5b7ddd0d66f4873958`
PARENT_CONTRACT: `tasks/ROTA-T012/brief.md`

## CEL

Zbudować trwały model danych T012 bez zmiany jeszcze solverowego REST ani emergency retry.

Po A domena i LocalStore potrafią round-tripować:

- `ShiftCatalogKind = 24h | 12h | INNY`;
- `StandardShift.catalog_kind / required_rest_hours / active_weekdays`;
- `SiteMembership.can_work_24h`;
- ShiftDemand provenance T012;
- Assignment work-period/rest provenance;
- schema v5 i migrację v4→v5.

Assembler generuje poprawny katalogowy demand set, w tym dwie komponenty normalnego 24h, ale pełna semantyka same-person/rest jest egzekwowana dopiero w B.

## PART A SCOPE

- rota/constants.py
- rota/domain.py
- rota/application/assembler.py
- rota/application/bootstrap.py
- rota/persistence/db.py
- rota/persistence/site_profile_repository.py
- rota/persistence/employee_repository.py
- rota/persistence/schedule_repository.py
- rota/persistence/schedule_lifecycle.py
- rota/persistence/schedule_validation.py
- rota/planning/shift_catalog.py
- tests/test_t012.py

Żaden inny plik produkcyjny/testowy w A.

## WYMAGANIA

1. Nowe dataclass fields są dopisane na końcu z compatibility defaults opisanymi w briefie; nie przepisywać setek starych konstruktorów.
2. New/updated StandardShift jest walidowany zgodnie z briefem. `required_rest_hours=0` jest dozwolone; program nie wprowadza prawnego minimum.
3. `active_weekdays` ma ISO 1..7 i anchor do start day.
4. `generate_profile_demands`:
   - 12h/INNY: 1 demand;
   - normalne 24h: 2 kolejne 12h demandy D↔N, wspólny template id, components 1/2;
   - kilka wpisów/overlap: kilka niezależnych occurrences;
   - deterministic ids bez kolizji także przy wielu pozycjach tego samego kind.
5. T012-generated demands zawsze mają jawny `shift_kind`; `classify_demand` jest tylko legacy fallback dla starych demandów.
6. `emergency_24h_rest_hours` jest snapshotowane podczas assembly tylko gdy istnieje jednoznaczny matching 24h capability. Conflicting matching rests fail-closed jako config/model error.
7. v4→v5 jest atomowe i bez utraty danych. Legacy membership default=true; legacy rest=11; legacy weekdays=all; legacy catalog_kind może zostać NULL i być normalizowane przy odczycie.
8. Persistence zapisuje/odczytuje wszystkie nowe pola ScheduleVersion content. FINAL history nie jest przepisywana.
9. `update_profile` / `update_membership` nie dostają nowych application façade; istniejące dataclasses/repositories wystarczają.
10. A nie zmienia jeszcze outcome engine ani nie pozwala solverowi łamać starego globalnego REST.

## TESTY A — MINIMUM

Wszystkie testy T012 A–D są konsolidowane w jednym nowym pliku `tests/test_t012.py`; checkpoint A dodaje do niego wyłącznie sekcję/testy A.

- enum/value round-trip;
- mixed profile 12h + INNY + 24h;
- arbitrary multiple INNY;
- weekday generation pon–pt vs weekend;
- overlapping entries generate separate demands;
- 24h D→N i N→D component shape;
- all-24 profile predicate data case;
- can_work_24h default + round-trip;
- real non-empty v4 DB → v5 migration + reopen;
- current schema reconnect idempotent;
- legacy profile/demand/assignment defaults remain readable;
- ambiguous emergency template fails closed;
- existing full suite PASS.

## GATE A

Codex musi potwierdzić brak zmiany behavior poza nowym data/generation contract i brak masowej edycji starych fixture'ów.

Wynik: `PASS — READY_FOR_IMPLEMENTATION_B`.

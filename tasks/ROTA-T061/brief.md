# ROTA-T061 — ręczna furtka po pierwszym zablokowanym PLAN

STATUS: PREIMPLEMENTATION AUDIT REQUIRED — IMPLEMENTATION HOLD

SOURCE_FINDING: BOARD.md / `ROTA-T057-ROUTE-A-REGRESSION`
OWNER_ACCEPTED_2026-09-09: program nie może odebrać koordynatorowi świadomej ręcznej decyzji o naruszeniu reguły.

## 1. Problem

Po T057 pierwszy zablokowany PLAN dla nowego `(site, month)` poprawnie nie tworzy żadnej biznesowej `ScheduleVersion`. To chroni zasadę: preview/failure nie może stać się trwałym grafikiem przed akceptacją.

Regresja polega na tym, że `apply_manual_correction()` wymaga `current ScheduleVersion`. Gdy PLAN nie dał wariantu i nie istnieje jeszcze żadna zaakceptowana wersja miesiąca, koordynator nie ma czego ręcznie skorygować. W praktyce znika wcześniejsza Route A: nie można ani wstawić legalnego zastępstwa, ani świadomie utworzyć grafiku z audytowalnym Deviation.

Reprodukcja źródłowa: `task/ROTA-TEST-CLEANUP@2a8ca39`, `test_t011_e...::test_2` i `::test_3` -> `NoCurrentScheduleVersion`.

## 2. Zamrożony kontrakt OWNERA

1. Solver nadal NIGDY nie łamie HARD automatycznie.
2. Pierwszy zablokowany PLAN nadal nie tworzy `ScheduleVersion`, current, History/restore/export ani zaakceptowanego grafiku.
3. Dopiero jawne działanie koordynatora może utworzyć pierwszy trwały grafik dla `(site, month)`.
4. Ręczna ścieżka musi pozwalać zarówno:
   - naprawić zablokowany miesiąc legalnym ręcznym przypisaniem;
   - świadomie zapisać naruszenie jako istniejący `Deviation`/action trail, jeśli produkt już pozwala na ręczne override danej reguły.
5. Nie wolno tworzyć ukrytej/technicznej `ScheduleVersion` tylko jako sztucznego parenta dla obecnego `apply_manual_correction()`. Pierwsza trwała wersja ma być skutkiem jawnej decyzji koordynatora, nie skutkiem failed PLAN.
6. Ręczna furtka jest dozwolona wyłącznie w sytuacji: brak current dla miesiąca + istniejący aktualny `DECISION_REQUIRED`/blocked-plan context, do którego działanie koordynatora jawnie odpowiada. Nie otwieramy ogólnego endpointu „stwórz dowolny pierwszy grafik bez PLAN”.
7. Dla miesiąca z istniejącą current/accepted wersją dotychczasowy `apply_manual_correction()` i lifecycle pozostają bez zmian.
8. T057 preview lifecycle, PlanPreview ownership, reject/accept semantics i brak zapisu przed `Użyj` pozostają bez zmian.
9. Symulatory Koordynatora A/B oraz stare benchmarki są zamrożone i nie są materiałem dowodowym T061.

## 3. Kierunek architektoniczny

Preferowany mechanizm: osobny wąski seam „first manual schedule after blocked PLAN”, który atomowo tworzy pierwszą biznesową `ScheduleVersion` z `parent_version_id=None` dopiero po jawnej ręcznej akcji koordynatora i wykorzystuje istniejące owner-y:
- persisted demands / assembler dla rzeczywistego miesiąca,
- `validator.validate()` dla oceny ręcznie złożonego grafiku,
- `materialize_deviations()` dla istniejących Deviation,
- istniejący action trail + link do `DECISION_REQUIRED`,
- `schedule_lifecycle` jako jedyny writer `ScheduleVersion/current`.

To jest kierunek do zweryfikowania, NIE zamrożony literalny implementation scope. Nie tworzyć „seed version”, pustej working-version ani preview-version w persistence tylko po to, aby użyć starej funkcji korekty.

## 4. Acceptance kierunkowe

T61-01: failed/blocked first PLAN nadal zostawia zero `ScheduleVersion`.

T61-02: bez current i bez prawidłowego blocked-plan/`DECISION_REQUIRED` ręczna próba nie może utworzyć pierwszego grafiku.

T61-03: po prawidłowym blocked PLAN jawna ręczna akcja może utworzyć pierwszą wersję grafiku z legalnym zastępstwem.

T61-04: ta sama ścieżka może utworzyć pierwszy grafik z ręcznie zaakceptowanym naruszeniem tam, gdzie istniejący kontrakt manual correction pozwala materializować `Deviation` zamiast blokować save.

T61-05: pierwsza trwała wersja jest jedna, `parent_version_id=None`, staje się current atomowo i ma prawidłowy action trail/decision link. Nie powstaje techniczny seed-parent.

T61-06: failure w trakcie ręcznego utworzenia nie zostawia częściowej wersji/current/action/deviation.

T61-07: zwykły manual correction przy istniejącym current działa bez regresji.

T61-08: T057 PLAN/reject/rerun/accept lifecycle pozostaje bez regresji.

T61-09: testy źródłowe Route A (`test_2`, `test_3`) wracają do zgodności z PRODUCT_TRUTH bez osłabiania ich assertions do samego braku wyjątku.

## 5. PREIMPLEMENTATION GATE — CODEX WHERE_MAP

IMPLEMENTATION HOLD.

Codex ma na aktualnym kodzie wskazać:
1. skąd w przypadku pierwszego blocked PLAN bez ScheduleVersion należy pobrać canonical `shift_demands` i dane potrzebne do walidacji ręcznego pierwszego grafiku;
2. czy istniejący `schedule_lifecycle.create_schedule_version(... parent_version_id=None ...)` może być bezpiecznie użyty atomowo jako pierwszy durable write, czy ma warunki wymagające osobnego ownera;
3. jak zweryfikować aktualny `DECISION_REQUIRED`/responds_to link tak, by furtka była możliwa tylko po realnym blocked PLAN, nie jako ogólne obejście PLAN;
4. które fragmenty `apply_manual_correction()` można współdzielić bez kopiowania validator/deviation/action-trail semantyki i bez sztucznego parenta;
5. minimalny endpoint/UI seam potrzebny, by koordynator faktycznie mógł wykonać Route A;
6. literalny `TASK_SCOPE` i wymagane testy, w tym dokładne źródłowe `test_2/test_3`.

Codex ma zwrócić PREIMPLEMENTATION PASS/FAIL + proponowany literalny `TASK_SCOPE`. Nie implementować produkcyjnie.

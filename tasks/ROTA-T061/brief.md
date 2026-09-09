# ROTA-T061 — ręczna furtka po pierwszym zablokowanym PLAN

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

SOURCE_FINDING: BOARD.md / `ROTA-T057-ROUTE-A-REGRESSION`
OWNER_ACCEPTED_2026-09-09: program nie może odebrać koordynatorowi świadomej ręcznej decyzji o naruszeniu reguły.
OWNER_RULING_2026-09-09_A: każda materialna zmiana danych wejściowych po zablokowanym PLAN unieważnia stary blocked context i wymaga ponownego PLAN na aktualnych danych.
OWNER_RULING_2026-09-09_B: T061 pozostaje wąskim taskiem naprawczym. Nie projektuje pełnej diagnostyki zablokowanego PLAN, nie wdraża kontrfaktycznego "co zmienić, żeby było FEASIBLE" i nie wdraża mechanizmu "zaakceptuj jeden HARD, solver dokłada resztę". Ten drugi temat jest świadomie odłożony w `ODLOZONE.md`; diagnostyka koordynatora została wydzielona do draftu `ROTA-T062`.

## 1. Problem

Po T057 pierwszy zablokowany PLAN dla nowego `(site, month)` poprawnie nie tworzy żadnej biznesowej `ScheduleVersion`. To chroni zasadę: preview/failure nie może stać się trwałym grafikiem przed akceptacją.

Regresja polega na tym, że `apply_manual_correction()` wymaga `current ScheduleVersion`. Gdy PLAN nie dał wariantu i nie istnieje jeszcze żadna zaakceptowana wersja miesiąca, koordynator nie ma czego ręcznie skorygować. W praktyce znika wcześniejsza Route A: nie można świadomie utworzyć pierwszego grafiku z audytowalnym Deviation.

Reprodukcja źródłowa: `task/ROTA-TEST-CLEANUP@2a8ca39`, `test_t011_e...::test_2` i `::test_3` -> `NoCurrentScheduleVersion`.

## 2. Zamrożony kontrakt OWNERA

1. Solver nadal NIGDY nie łamie HARD automatycznie.
2. Pierwszy zablokowany PLAN nadal nie tworzy `ScheduleVersion`, current, History/restore/export ani zaakceptowanego grafiku.
3. Dopiero jawne działanie koordynatora może utworzyć pierwszy trwały grafik dla `(site, month)`.
4. Ręczna ścieżka musi pozwalać świadomie zapisać naruszenie jako istniejący `Deviation`/action trail tam, gdzie produkt już pozwala na manual override danej reguły.
5. Nie wolno tworzyć ukrytej/technicznej `ScheduleVersion` tylko jako sztucznego parenta dla obecnego `apply_manual_correction()`. Pierwsza trwała wersja ma być skutkiem jawnej decyzji koordynatora, nie skutkiem failed PLAN.
6. Ręczna furtka jest dozwolona wyłącznie przy braku current dla miesiąca i po realnym, aktualnym blocked PLAN dla dokładnie tego `(site, month)`.
7. Jeśli po blocked PLAN koordynator zmieni staffing, urlop, dostępność, regułę lub inny materialny input, poprzedni blocked context wygasa. Koordynator musi uruchomić PLAN ponownie. Nie wolno ręcznie odpowiadać na historyczny `DECISION_REQUIRED` po zmianie danych.
8. Jeśli ponowny PLAN stanie się FEASIBLE, normalny flow PLAN/wybór wariantu kończy problem; Route A nie jest wtedy używana.
9. Jeśli ponowny PLAN nadal jest blocked i koordynator świadomie wybiera Route A, T061 dopuszcza tylko kompletny pierwszy root schedule: przed trwałym zapisem wszystkie wymagane PRIMARY demands miesiąca muszą być jawnie obsadzone. Nie zapisujemy częściowego root schedule z coverage gaps tylko dlatego, że edycja nie została dokończona.
10. T061 nie próbuje automatycznie dokończyć reszty miesiąca wokół pojedynczego ręcznego wyjątku. To pozostaje świadomie odłożone w `ODLOZONE.md`.
11. T061 nie definiuje pełnej diagnostyki "dlaczego PLAN nie dał grafiku" ani kompletnego UX naprawczego; to osobny draft `ROTA-T062`.
12. Dla miesiąca z istniejącą current/accepted wersją dotychczasowy `apply_manual_correction()` i lifecycle pozostają bez zmian.
13. T057 preview lifecycle, PlanPreview ownership, reject/accept semantics i brak zapisu przed `Użyj` pozostają bez zmian.
14. Symulatory Koordynatora A/B oraz stare benchmarki są zamrożone i nie są materiałem dowodowym T061.

## 3. Kierunek architektoniczny po WHERE_MAP Codexa

Potwierdzony minimalny kierunek:
- canonical demands bez current pochodzą z `assembler.assemble_planning_state -> generate_profile_demands`;
- `schedule_lifecycle.create_schedule_version(... parent_version_id=None ...)` może atomowo utworzyć pierwszy root/current i obsłużyć `pre_check`/`on_success`;
- nie powstaje seed-parent ani druga ścieżka persistence;
- logikę `manual_edit` dla validate -> materialize_deviations -> T058 freeze -> REST audit -> action trail trzeba współdzielić/wyekstrahować, nie kopiować;
- potrzebny jest osobny, wąski first-manual command/endpoint dla braku current;
- pre_check musi wymagać aktualnego `DECISION_REQUIRED` dla dokładnie target `(site, month)`, a nie tylko opcjonalnego linku do historycznej decyzji;
- payload pierwszego ręcznego zapisu ma reprezentować kompletny zestaw przypisań PRIMARY wymagany do utworzenia root schedule; partial root jest niedozwolony.

## 4. Acceptance

T61-01: failed/blocked first PLAN nadal zostawia zero `ScheduleVersion`.

T61-02: bez current i bez prawidłowego aktualnego blocked-plan/`DECISION_REQUIRED` ręczna próba nie może utworzyć pierwszego grafiku.

T61-03: po zmianie materialnego inputu po blocked PLAN stary context nie może być użyty; wymagany jest ponowny PLAN.

T61-04: jeśli ponowny PLAN jest FEASIBLE, normalny PLAN działa bez Route A.

T61-05: jeśli ponowny PLAN nadal jest blocked, jawna Route A może utworzyć pierwszy kompletny root schedule z ręcznie zaakceptowanym naruszeniem tam, gdzie istniejący kontrakt manual correction pozwala materializować `Deviation` zamiast blokować save.

T61-06: partial root schedule z nieobsadzonymi wymaganymi PRIMARY demands jest odrzucany przed durable write.

T61-07: pierwsza trwała wersja jest jedna, `parent_version_id=None`, staje się current atomowo i ma prawidłowy action trail/decision link. Nie powstaje techniczny seed-parent.

T61-08: failure w trakcie ręcznego utworzenia nie zostawia częściowej wersji/current/action/deviation.

T61-09: zwykły manual correction przy istniejącym current działa bez regresji.

T61-10: T057 PLAN/reject/rerun/accept lifecycle pozostaje bez regresji.

T61-11: źródłowy `test_2` zostaje skorygowany do PRODUCT_TRUTH: po `update_membership` musi wykonać ponowny PLAN; jeśli nowy PLAN jest FEASIBLE, nie wolno wymuszać Route A. Test ma dalej chronić realną regresję, nie dawną sekwencję.

T61-12: źródłowy `test_3` ma zachować przypadek aktualnego blocked context bez current i sprawdzić pierwsze manual root + Deviation zgodnie z nowym kontraktem.

## 5. Literalny TASK_SCOPE do re-checku Codexa

IMPLEMENTATION HOLD do wąskiego literalnego re-checku.

Codex ma sprawdzić wyłącznie, czy poniższy scope jest wystarczający i niesprzeczny; nie powtarzać WHERE_MAP:
- `rota/application/manual_edit.py` — współdzielona logika validate/deviation/action + nowy root-compatible command bez sztucznego parenta;
- `rota/persistence/site_memory.py` — tylko jeśli potrzebny jest wąski exact `(site, month)` current-decision pre-check;
- `api/routers/manual_edit.py` — osobny first-manual endpoint/payload;
- `frontend/src/screens/MonthlyPlanning.tsx` — minimalny entry do Route A po aktualnym blocked PLAN; bez redesignu diagnostyki T062;
- `frontend/src/api/client.ts` — tylko typ/call potrzebny nowemu endpointowi;
- wąskie testy T061 + źródłowe `test_2/test_3`.

Po PASS Codexa IMPLEMENTATION HOLD może zostać zdjęty dla tego literalnego scope.

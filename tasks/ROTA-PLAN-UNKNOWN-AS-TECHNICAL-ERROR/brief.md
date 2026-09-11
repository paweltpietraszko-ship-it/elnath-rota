# ROTA-PLAN-UNKNOWN-AS-TECHNICAL-ERROR — PLAN UNKNOWN ma użyć istniejącego SEARCH_INCOMPLETE

STATUS: PREIMPLEMENTATION AUDIT REQUIRED — IMPLEMENTATION HOLD

BASELINE: `main@00f7355a6847c8f6a5debefc3691e80f3de415a7`

SOURCE: BOARD `ROTA-PLAN-UNKNOWN-AS-TECHNICAL-ERROR`, OWNER_ACCEPTED 2026-09-11.

## 1. Cel

Naprawić wyłącznie błędną klasyfikację wyniku CP-SAT `UNKNOWN` dla rodziny PLAN.

Pierwszy PLAN i późniejszy `Przelicz Plan` już korzystają z istniejącej ścieżki `plan_month -> plan`. Gdy solver nie zdąży rozstrzygnąć w budżecie i zwraca `UNKNOWN` bez kandydata, wynik nie może być pokazywany jako awaria techniczna.

Nie projektujemy nowej ścieżki. Wykorzystujemy istniejące elementy:
- status `SEARCH_INCOMPLETE`;
- istniejący parametr `search_attempt`;
- istniejące `runPlanSearchAgain`;
- istniejące `runReplanSearchAgain`;
- istniejący `planResultSource`;
- istniejący ekran i przycisk ponowienia wyszukiwania.

## 2. Zamrożone zachowanie

### 2.1 PLAN / Przelicz Plan

Jeżeli solver kończy bez kandydata ze statusem dokładnie `UNKNOWN`:
- wynik produktu = `SEARCH_INCOMPLETE`;
- `TECHNICAL_ERROR` nie może być użyty dla tego przypadku;
- użytkownik widzi prostą informację, że program nie zdążył ułożyć grafiku w dostępnym czasie i może kontynuować wyszukiwanie;
- kliknięcie ponowienia uruchamia kolejną jawną próbę PLAN przez istniejący `runPlanSearchAgain` / `search_attempt`;
- każda próba zachowuje istniejący budżet 45 s;
- brak automatycznego retry.

Pierwszy PLAN i `Przelicz Plan` należą do tej samej rodziny i po `UNKNOWN` ponawiają PLAN, nie REPLAN.

### 2.2 REPLAN

Istniejące zachowanie REPLAN pozostaje bez zmian:
- `SEARCH_INCOMPLETE` pozostaje retryable;
- ponowienie używa istniejącego `runReplanSearchAgain`;
- narrow/wide nadal korzystają z obecnego `lastWideSearch` i historii próby.

### 2.3 FEASIBLE + incomplete optimization

Jeżeli istnieje poprawny kandydat, a `optimization_complete=false`, zachowanie pozostaje obecne:
- kandydat jest pokazany;
- użytkownik może go użyć albo wybrać dalsze szukanie;
- nie zamieniać tego przypadku na pusty `SEARCH_INCOMPLETE`.

### 2.4 Co nadal jest TECHNICAL_ERROR

Nie rozszerzać `SEARCH_INCOMPLETE` na inne błędy.

`TECHNICAL_ERROR` pozostaje dla m.in.:
- `MODEL_INVALID`;
- wyjątków/model errors;
- błędów walidatora/mapowania;
- błędów zapisu/API;
- każdego nierozstrzygniętego statusu innego niż dokładnie `UNKNOWN`, jeżeli obecny kontrakt klasyfikuje go jako błąd techniczny.

## 3. Backend — wykorzystać istniejący status

W `rota/planning/engine.py` obecne ścieżki PLAN mapują brak kandydata + `UNKNOWN` na `TECHNICAL_ERROR` w:
- `_dispatch_or_continue`;
- `_dispatch_stage3`;
- `_resolve_without_load_cap`.

Zmiana ma być minimalna:
- rozpoznać dokładnie `outcome.status_name == "UNKNOWN"`;
- zwrócić istniejący `PlanningResult("SEARCH_INCOMPLETE", ...)` w kształcie zgodnym z już istniejącą semantyką REPLAN;
- nie zmieniać solvera, deadline, liczby etapów ani kolejności fallbacków;
- nie dodawać nowego statusu, endpointu ani nowego retry wewnątrz engine.

Jeżeli istnieje już wspólny mały helper do mapowania timeoutowego UNKNOWN i jego reużycie upraszcza kod bez zmiany zachowania, można go wykorzystać. Nie tworzyć nowej warstwy.

## 4. Frontend — poprawić tylko routing istniejącego retry

`frontend/src/screens/MonthlyPlanning.tsx` już ma:
- `runPlanSearchAgain`;
- `runReplanSearchAgain`;
- `planResultSource`;
- `searchAgainForFeasible`, które już poprawnie wybiera PLAN vs REPLAN;
- render `SEARCH_INCOMPLETE` z przyciskiem ponowienia.

Obecny `retrySearchIncomplete = () => runReplanSearchAgain()` jest zbyt wąski.

Ma zostać zastąpiony routingiem po istniejącym `planResultSource`:
- source `plan` -> `runPlanSearchAgain`;
- source `replan` -> `runReplanSearchAgain`.

Nie budować drugiego komponentu, drugiego bannera ani osobnej ścieżki dla `Przelicz Plan`.

Tekst dla pustego `SEARCH_INCOMPLETE` ma pozostać prosty i nietechniczny, w znaczeniu:
`Program nie zdążył ułożyć grafiku w dostępnym czasie. Możesz ponowić wyszukiwanie.`

Nie pokazywać `UNKNOWN`, CP-SAT, timeout code ani identyfikatorów technicznych.

## 5. Trwałość / lifecycle

Dla `UNKNOWN` bez kandydata:
- nie powstaje nowy zaakceptowany ScheduleVersion;
- nie zmienia się obowiązujący current;
- nie zapisuje się fałszywego kandydata;
- ponowienie jest nową jawną próbą istniejącego PLAN;
- rozpoczęcie kolejnej próby zachowuje istniejące zasady dotyczące zastępowania/odrzucania niezaakceptowanego preview.

T064/T063/T062 lifecycle pozostaje bez zmian.

## 6. Acceptance

A1. Pierwszy PLAN: wymuszony/zasymulowany na poziomie testu engine wynik `UNKNOWN` bez assignmentów daje dokładnie `SEARCH_INCOMPLETE`, nie `TECHNICAL_ERROR`.

A2. `Przelicz Plan`: ponieważ używa tej samej rodziny PLAN, ten sam `UNKNOWN` daje `SEARCH_INCOMPLETE`.

A3. REPLAN nadal daje i ponawia `SEARCH_INCOMPLETE` po istniejącej ścieżce REPLAN.

A4. `MODEL_INVALID` nadal daje `TECHNICAL_ERROR`.

A5. FEASIBLE z kandydatem i `optimization_complete=false` nadal pokazuje kandydata oraz istniejącą możliwość dalszego szukania; nie jest redukowane do pustego wyniku.

A6. Frontendowy przycisk przy `SEARCH_INCOMPLETE` kieruje:
- PLAN/Przelicz Plan -> `runPlanSearchAgain`;
- REPLAN -> `runReplanSearchAgain`.

A7. Każde ponowienie zwiększa istniejący `search_attempt` zgodnie z obecną implementacją; brak automatycznych prób.

A8. Brak nowego endpointu, statusu, modelu danych, solver rule, deadline lub drugiego mechanizmu retry.

## 7. Literalny TASK_SCOPE

Dozwolone production paths:
- `rota/planning/engine.py` — wyłącznie klasyfikacja dokładnego `UNKNOWN` bez kandydata na istniejący `SEARCH_INCOMPLETE`;
- `frontend/src/screens/MonthlyPlanning.tsx` — wyłącznie routing istniejącego retry po `planResultSource` oraz ewentualne doprecyzowanie prostego tekstu bannera.

Dozwolone test paths:
- nowy `tests/test_plan_unknown_search_incomplete.py`;
- nowy `frontend/e2e/plan-search-incomplete-routing.spec.ts` wyłącznie jeżeli istniejący test seam pozwala sprawdzić routing bez budowania nowego frameworka/mock systemu;
- `tests/test_audit_r14_findings.py` — wyłącznie mechaniczna aktualizacja oczekiwania/nazwy/komentarza dla dokładnego `UNKNOWN`; zachować ochronę przed cichym retry;
- `tests/test_t012.py` — wyłącznie mechaniczna aktualizacja oczekiwania/nazwy/komentarza dla dokładnego `UNKNOWN`; zachować ochronę przed cichym retry;
- `tests/test_t018.py` — wyłącznie mechaniczna aktualizacja oczekiwania/nazwy/komentarza dla dokładnego `UNKNOWN`; zachować ochronę przed cichym retry;
- `tests/test_replan_minimal_reshuffle.py` — wyłącznie mechaniczna aktualizacja oczekiwania/nazwy/komentarza dla dokładnego `UNKNOWN`; zachować ochronę przed cichym retry.

W czterech istniejących testach powyżej nie zmieniać żadnej innej granicy produktu. Asercje `MODEL_INVALID` i pozostałe klasy `TECHNICAL_ERROR` pozostają bez zmian. Liczba wywołań solvera w ramach jednej próby ma pozostać taka sama; zmiana `UNKNOWN -> SEARCH_INCOMPLETE` nie jest zgodą na wewnętrzny retry.

Jeżeli frontendowego E2E nie da się zrobić bez nowej infrastruktury testowej, nie budować jej. Wtedy wystarczy istniejący poziom testów komponentu/API, jeżeli taki już jest, albo wąski test statyczny/behavioural w obecnym frameworku wskazany przez Codexa przed implementacją.

Poza scope:
- `rota/planning/solver.py`;
- limity 45 s;
- nowe statusy;
- nowe endpointy;
- `api/routers/**`, o ile nie zostanie wykazana konkretna luka marshallingowa;
- modele domenowe;
- ScheduleVersion/lifecycle;
- T059;
- automatyczne retry;
- wielowątkowość/GPU/zmiana parametrów CP-SAT;
- nowy flow UX.

Jeżeli implementacja wymaga wyjścia poza ten zakres, CC zatrzymuje pracę i wraca do architekta.

## 8. Preimplementation check Codexa

Po mechanicznej korekcie scope Codex ma wykonać tylko krótki literalny re-check:
1. Czy cztery dopisane ścieżki testowe dokładnie odpowiadają aktywnym testom wskazanym w raporcie R1?
2. Czy ich dozwolona zmiana jest ograniczona do nowej PRODUCT_TRUTH `UNKNOWN -> SEARCH_INCOMPLETE`, przy zachowaniu dotychczasowej ochrony przed cichym retry i bez ruszania `MODEL_INVALID`/pozostałych `TECHNICAL_ERROR`?
3. Czy production scope nadal pozostaje wyłącznie `engine.py` + `MonthlyPlanning.tsx`?

Nie powtarzać audytu solvera, mapy ownership ani redesignu zadania.

Jeżeli odpowiedź na wszystkie trzy = tak: PASS exact SHA i zwolnienie IMPLEMENTATION HOLD.
Jeżeli nie: wskazać jedną konkretną sprzeczność; bez redesignu zadania.

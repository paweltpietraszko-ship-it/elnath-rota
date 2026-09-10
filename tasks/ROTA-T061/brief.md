# ROTA-T061 — Korekta ręczna po pierwszym kontrolowanym zablokowaniu PLAN

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

SOURCE_FINDING: BOARD.md / `ROTA-T057-ROUTE-A-REGRESSION`

OWNER_ACCEPTED_2026-09-09: program nie może odebrać koordynatorowi świadomej ręcznej decyzji o naruszeniu reguły.

OWNER_RULING_2026-09-10_A: NORMALNY flow programu pozostaje bez zmian — użytkownik zaczyna od `PLAN`. T061 nie tworzy równoległego zwykłego workflow ręcznego.

OWNER_RULING_2026-09-10_B: T061 dotyczy wyłącznie kontrolowanego biznesowego zablokowania pierwszego PLAN, które program już rozpoznaje i obsługuje w normalnym kontrakcie planowania. Nie obejmuje awarii technicznych.

OWNER_RULING_2026-09-10_C: `TECHNICAL_ERROR`, HTTP error, timeout, zawieszenie/utrata backendu lub inna awaria wykonania NIE są Route A T061. Nie wolno mieszać ich z rozpoznanym blockerem biznesowym ani automatycznie otwierać przez nie Korekty ręcznej. Ich istniejąca obsługa techniczna pozostaje osobnym problemem.

OWNER_RULING_2026-09-10_D: ordinary `PLAN` ma na poziomie engine trzy wyniki: `FEASIBLE`, `DECISION_REQUIRED`, `TECHNICAL_ERROR`. T061 dotyczy przypadku, w którym pierwszy PLAN kończy się kontrolowanym biznesowym blockerem (`DECISION_REQUIRED`; w tym rozpoznane przyczyny takie jak brak obsady, REST/LOAD/NIGHT-STREAK/third-consecutive itp.), nie `TECHNICAL_ERROR`. `SEARCH_INCOMPLETE` należy do osobnego flow REPLAN/search i nie jest wejściem T061 dla pierwszego PLAN.

OWNER_RULING_2026-09-10_E: T061 nie projektuje diagnostyki blockera — to `ROTA-T062`. T061 naprawia tylko lukę techniczno-produktową: po kontrolowanym zablokowaniu pierwszego PLAN nie ma `current ScheduleVersion`, więc istniejąca `Korekta ręczna` nie ma na czym pracować.

OWNER_RULING_2026-09-10_F: koordynator może w Korekcie ręcznej świadomie naruszyć istniejący HARD; program ostrzega i zapisuje istniejący `Deviation`/action trail zgodnie z obecnym kontraktem manual correction, ale nie blokuje samej świadomej decyzji człowieka tam, gdzie produkt już dopuszcza override.

OWNER_RULING_2026-09-10_G: T061 nie projektuje nowych zachowań dla nieskonfigurowanego obiektu ani dla awarii całej aplikacji. Brak wymaganych służb nie może prowadzić do utworzenia pustego grafiku.

## 1. Problem

Po T057 pierwszy kontrolowanie zablokowany PLAN dla nowego `(site, month)` poprawnie nie tworzy biznesowej `ScheduleVersion`. To chroni zasadę: preview/blocker nie może stać się trwałym grafikiem przed akceptacją.

Regresja polega na tym, że obecna `apply_manual_correction()` wymaga `current ScheduleVersion`. Gdy pierwszy PLAN kończy się kontrolowanym blockerem biznesowym i nie istnieje jeszcze zaakceptowana wersja miesiąca, koordynator nie ma czego ręcznie skorygować. W praktyce znika możliwość świadomego ręcznego utworzenia pierwszego grafiku mimo tego, że program poprawnie rozpoznał konflikt.

Reprodukcja źródłowa: `task/ROTA-TEST-CLEANUP@2a8ca39`, `test_t011_e...::test_2` i `::test_3` -> `NoCurrentScheduleVersion`.

## 2. Zamrożony kontrakt OWNERA

1. Normalny flow pozostaje: `PLAN -> kandydat -> Użyj`.
2. Solver nadal NIGDY nie łamie HARD automatycznie.
3. `FEASIBLE` pozostaje zwykłym sukcesem PLAN i nie uruchamia T061.
4. T061 otwiera awaryjną ręczną drogę tylko po kontrolowanym biznesowym zablokowaniu pierwszego PLAN (`DECISION_REQUIRED` i jego rozpoznane blockery), przy braku current.
5. `TECHNICAL_ERROR`, HTTP error, timeout i awaria aplikacji są wyłączone z T061. Nie wolno dodawać drugiej logiki ich obsługi ani używać ich jako substytutu `DECISION_REQUIRED`.
6. `SEARCH_INCOMPLETE` nie jest wynikiem ordinary first PLAN i nie należy do T061.
7. T062 pozostaje jedynym taskiem projektującym, co koordynator widzi jako przyczynę i możliwe działania po rozpoznanym blockerze.
8. Po takim kontrolowanym blockerze koordynator może poprawić dane i uruchomić PLAN ponownie; jeśli PLAN stanie się `FEASIBLE`, normalny flow kończy problem.
9. Alternatywnie, bez current, koordynator może wejść do tej samej funkcji `Korekta ręczna` i ręcznie utworzyć pierwszy kompletny root schedule.
10. Nie tworzymy konkurencyjnej funkcji `Ułóż ręcznie` ani drugiego edytora o innej semantyce.
11. Gdy current istnieje, `Korekta ręczna` zachowuje dotychczasowy kontrakt korekty istniejącego grafiku.
12. Pierwszy ręczny root musi być kompletny: wszystkie wymagane PRIMARY demands miesiąca muszą być obsadzone przed durable write. Nie zapisujemy częściowego root z coverage gaps wynikających z niedokończonej edycji.
13. Koordynator może świadomie naruszyć HARD tam, gdzie obecny kontrakt manual correction dopuszcza override. Program ostrzega, materializuje `Deviation` i zapisuje action trail.
14. Nie wolno tworzyć technicznej/ukrytej `ScheduleVersion` ani seed-parenta. Pierwsza trwała wersja ma `parent_version_id=None` i powstaje wyłącznie po jawnej akcji koordynatora.
15. Materialna zmiana staffing/urlopu/dostępności/reguły unieważnia starą diagnozę; kolejny PLAN liczy na aktualnych danych.
16. Brak wymaganych służb/canonical demands nie może prowadzić do utworzenia pustego grafiku. Nieskonfigurowany obiekt jest poza zakresem T061.
17. T061 nie wdraża mechanizmu „zaakceptuj jeden HARD, solver dokłada resztę”; to pozostaje w `ODLOZONE.md`.
18. T057 preview lifecycle, PlanPreview ownership, reject/accept semantics i brak durable zapisu przed `Użyj` pozostają bez zmian.
19. Spóźniony wynik wcześniej uruchomionego PLAN nie może po utworzeniu manualnego root przywrócić starego preview/`DECISION_REQUIRED` ani zmienić current.
20. Symulatory Koordynatora A/B oraz stare benchmarki są zamrożone i nie są materiałem dowodowym T061.

## 3. Kierunek architektoniczny

Minimalny kierunek pozostaje reuse istniejących ownerów:
- canonical demands bez current: `assembler.assemble_planning_state -> generate_profile_demands`;
- pierwszy trwały root/current: `schedule_lifecycle.create_schedule_version(... parent_version_id=None ...)`;
- validate/deviation/T058 freeze/REST audit/action trail: współdzielić istniejącą logikę `manual_edit`, nie kopiować;
- techniczny root-compatible command/endpoint może istnieć, ale produktowo/UI nadal jest to jedna funkcja `Korekta ręczna`;
- `rota/application/plan_ops.py` wchodzi literalnie do scope wyłącznie dla guardu przed spóźnionym zapisem starego preview/DECISION_REQUIRED po utworzeniu manual root;
- nie dodawać logiki obsługi `TECHNICAL_ERROR`, timeout/HTTP error ani nowego rejestru awarii w ramach T061;
- nie dodawać nowych reguł solvera, diagnostyki T062, seed-parenta, pustej working-version ani recovery subsystemu.

## 4. Acceptance

T61-01: normalny nowy miesiąc nadal zaczyna się od PLAN; T061 nie zmienia zwykłej ścieżki PLAN/wybór/Użyj.

T61-02: pierwszy PLAN zakończony `DECISION_REQUIRED` nadal zostawia zero biznesowych `ScheduleVersion` przed jawą decyzją koordynatora.

T61-03: po `DECISION_REQUIRED`, przy braku current i dostępnych canonical danych miesiąca, koordynator może przejść do tej samej `Korekta ręczna` i zobaczyć wymagane służby do ręcznego obsadzenia.

T61-04: `TECHNICAL_ERROR`, HTTP error, timeout i awaria aplikacji NIE otwierają Route A T061 i nie otrzymują w tym tasku nowej logiki.

T61-05: `SEARCH_INCOMPLETE` nie jest traktowany jako wynik ordinary first PLAN ani wejście T061.

T61-06: nie istnieje osobny produktowy mechanizm `Ułóż ręcznie`; przy current nadal działa obecna Korekta ręczna bez regresji.

T61-07: incomplete first manual root jest odrzucany przed durable write; zero częściowych ScheduleVersion/current/action/deviation.

T61-08: kompletny first manual root tworzy dokładnie jedną trwałą wersję z `parent_version_id=None`, atomowo staje się current i ma prawidłowy action trail.

T61-09: ręczne świadome naruszenie HARD zachowuje istniejącą semantykę manual correction: ostrzeżenie + `Deviation`/audit, bez automatycznego solver override i bez blokowania świadomej decyzji koordynatora tam, gdzie taki override jest już dozwolony.

T61-10: materialna zmiana inputu po blockerze unieważnia starą diagnozę; ponowny PLAN liczy na aktualnych danych. Jeśli jest FEASIBLE, działa normalny flow.

T61-11: brak canonical required PRIMARY demands nie może zakończyć się zapisem pustego root schedule.

T61-12: spóźniony wynik wcześniej uruchomionego PLAN po utworzeniu manualnego root nie może przywrócić starego preview/decision ani nadpisać current.

T61-13: failure podczas manualnego durable write nie zostawia częściowej wersji/current/action/deviation.

T61-14: T057 PLAN/reject/rerun/accept lifecycle pozostaje bez regresji.

T61-15: źródłowe `test_2/test_3` mają chronić przypadek kontrolowanego business blocker -> brak current -> manual root, a nie awarię techniczną ani historyczny requirement current `DECISION_REQUIRED` jako osobnej autoryzacji persistence.

## 5. Literalny TASK_SCOPE do re-checku Codexa

IMPLEMENTATION HOLD do krótkiego ponownego re-checku aktualnego kontraktu.

Codex ma sprawdzić wyłącznie minimalny scope potrzebny do spełnienia powyższego kontraktu:
- `rota/application/manual_edit.py` — reuse validate/deviation/action + root-compatible command bez seed-parenta;
- `rota/application/plan_ops.py` — wyłącznie guard przed spóźnionym zapisem starego preview/DECISION_REQUIRED po utworzeniu manual root;
- `api/routers/manual_edit.py` — wąski endpoint/payload dla pierwszego root, jeśli technicznie potrzebny;
- `frontend/src/screens/MonthlyPlanning.tsx` — awaryjne przejście do tej samej Korekty ręcznej po kontrolowanym `DECISION_REQUIRED`; bez redesignu T062 i bez obsługi awarii technicznych;
- `frontend/src/api/client.ts` — tylko typ/call potrzebny tej ścieżce;
- persistence/lifecycle tylko tam, gdzie rzeczywiście trzeba zagwarantować atomic root;
- wąskie testy T061 + źródłowe `test_2/test_3` + jeden real-browser Playwright vertical bez mocked backendu.

Codex ma jawnie potwierdzić, że T061 nie tworzy równoległej logiki dla `TECHNICAL_ERROR`, HTTP error, timeout ani REPLAN `SEARCH_INCOMPLETE`. Nie rozszerzać scope poza dowiedzioną potrzebę.

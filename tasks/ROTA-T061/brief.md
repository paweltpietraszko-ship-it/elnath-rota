# ROTA-T061 — Korekta ręczna po pierwszym kontrolowanym zablokowaniu PLAN

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

SOURCE_FINDING: BOARD.md / `ROTA-T057-ROUTE-A-REGRESSION`

OWNER_ACCEPTED_2026-09-09: program nie może odebrać koordynatorowi świadomej ręcznej decyzji o naruszeniu reguły.

OWNER_RULING_2026-09-10_A: NORMALNY flow programu pozostaje bez zmian — użytkownik zaczyna od `PLAN`. T061 nie tworzy równoległego zwykłego workflow ręcznego.

OWNER_RULING_2026-09-10_B: **ZASADA NADRZĘDNA:** HARD ogranicza automat, nie koordynatora. Solver/PLAN/REPLAN/Przelicz Plan nigdy sam nie łamie HARD. Koordynator może na własną odpowiedzialność świadomie naruszyć HARD; system ma go ostrzec oraz zapisać `Deviation`/action trail/pamięć decyzji, ale nie może zablokować świadomej decyzji człowieka tylko dlatego, że reguła jest HARD.

OWNER_RULING_2026-09-10_C: T061 dotyczy wyłącznie kontrolowanego biznesowego zablokowania pierwszego PLAN, które program już rozpoznaje i obsługuje w normalnym kontrakcie planowania. Nie obejmuje awarii technicznych i nie redefiniuje istniejącej semantyki statusów planowania.

OWNER_RULING_2026-09-10_D: `DECISION_REQUIRED` oraz `THIRD_CONSECUTIVE_SHIFT_BLOCKED` są dwoma różnymi, już istniejącymi kontrolowanymi wynikami biznesowymi. `THIRD_CONSECUTIVE_SHIFT_BLOCKED` oznacza wyłącznie: automat nie potrafi utworzyć legalnego grafiku bez nadania komuś trzeciej kolejnej służby. Nie oznacza zakazu dla koordynatora. Koordynator może świadomie przejść do Korekty ręcznej i zapisać taki grafik z `Deviation`/action trail. T061 nie dodaje drugiej logiki do tych statusów; usuwa tylko wspólną przeszkodę `brak current -> brak możliwości utworzenia pierwszego manualnego root`.

OWNER_RULING_2026-09-10_E: `TECHNICAL_ERROR`, HTTP error, timeout, zawieszenie/utrata backendu lub inna awaria wykonania NIE są Route A T061. Nie wolno mieszać ich z rozpoznanym blockerem biznesowym ani automatycznie otwierać przez nie Korekty ręcznej. Ich istniejąca obsługa techniczna pozostaje osobnym problemem.

OWNER_RULING_2026-09-10_F: `SEARCH_INCOMPLETE` należy do osobnego flow REPLAN/search i nie jest wejściem T061 dla pierwszego ordinary PLAN.

OWNER_RULING_2026-09-10_G: T061 nie projektuje diagnostyki blockera — to `ROTA-T062` tam, gdzie dany wynik używa diagnozy. T061 naprawia tylko lukę techniczno-produktową: po kontrolowanym zablokowaniu pierwszego PLAN nie ma `current ScheduleVersion`, więc istniejąca `Korekta ręczna` nie ma na czym pracować.

OWNER_RULING_2026-09-10_H: T061 nie projektuje nowych zachowań dla nieskonfigurowanego obiektu ani dla awarii całej aplikacji. Brak wymaganych służb nie może prowadzić do utworzenia pustego grafiku.

## 1. Problem

Po T057 pierwszy kontrolowanie zablokowany PLAN dla nowego `(site, month)` poprawnie nie tworzy biznesowej `ScheduleVersion`. To chroni zasadę: preview/blocker nie może stać się trwałym grafikiem przed akceptacją.

Regresja polega na tym, że obecna `apply_manual_correction()` wymaga `current ScheduleVersion`. Gdy pierwszy PLAN kończy się kontrolowanym blockerem biznesowym i nie istnieje jeszcze zaakceptowana wersja miesiąca, koordynator nie ma czego ręcznie skorygować. W praktyce znika możliwość świadomego ręcznego utworzenia pierwszego grafiku mimo tego, że program poprawnie rozpoznał konflikt.

Reprodukcja źródłowa: `task/ROTA-TEST-CLEANUP@2a8ca39`, `test_t011_e...::test_2` i `::test_3` -> `NoCurrentScheduleVersion`.

## 2. Zamrożony kontrakt OWNERA

1. Normalny flow pozostaje: `PLAN -> kandydat -> Użyj`.
2. **HARD jest granicą automatu, nie koordynatora.** Solver nigdy sam nie łamie HARD. Koordynator może świadomie naruszyć HARD; system ostrzega i zapisuje `Deviation`/action trail, ale nie blokuje jego decyzji.
3. `FEASIBLE` pozostaje zwykłym sukcesem PLAN i nie uruchamia T061.
4. T061 może być potrzebny po istniejącym kontrolowanym blockerze biznesowym pierwszego PLAN, gdy nie ma current. Nie zmienia semantyki samego blockera.
5. `DECISION_REQUIRED` zachowuje swój istniejący flow decyzji/diagnozy. T061 nie tworzy drugiego `DECISION_REQUIRED`; pozwala jedynie, gdy nie ma current, wejść do tej samej Korekty ręcznej i utworzyć pierwszy manualny root.
6. `THIRD_CONSECUTIVE_SHIFT_BLOCKED` zachowuje swój istniejący sens: automat odmawia stworzenia kandydata wymagającego trzeciej kolejnej służby. Nie jest to zakaz dla koordynatora. Przy braku current koordynator może użyć tej samej Korekty ręcznej i świadomie zapisać trzecią służbę pod rząd; system ma ostrzec i zapisać `Deviation`/action trail.
7. `TECHNICAL_ERROR`, HTTP error, timeout i awaria aplikacji są wyłączone z T061. Nie wolno dodawać drugiej logiki ich obsługi ani używać ich jako substytutu kontrolowanego blockera biznesowego.
8. `SEARCH_INCOMPLETE` nie jest wynikiem ordinary first PLAN i nie należy do T061.
9. T062 pozostaje taskiem projektującym wyjaśnienie rozpoznanych blockerów tam, gdzie produkt ma diagnozę; T061 nie dubluje tego flow.
10. Po kontrolowanym blockerze koordynator może poprawić dane i uruchomić PLAN ponownie; jeśli PLAN stanie się `FEASIBLE`, normalny flow kończy problem.
11. Alternatywnie, bez current, koordynator może wejść do tej samej funkcji `Korekta ręczna` i ręcznie utworzyć pierwszy kompletny root schedule, również świadomie naruszając HARD na własną odpowiedzialność.
12. Nie tworzymy konkurencyjnej funkcji `Ułóż ręcznie` ani drugiego edytora o innej semantyce.
13. Gdy current istnieje, `Korekta ręczna` zachowuje dotychczasowy kontrakt korekty istniejącego grafiku.
14. Pierwszy ręczny root musi być kompletny: wszystkie wymagane PRIMARY demands miesiąca muszą być obsadzone przed durable write. Nie zapisujemy częściowego root z coverage gaps wynikających z niedokończonej edycji.
15. Nie wolno tworzyć technicznej/ukrytej `ScheduleVersion` ani seed-parenta. Pierwsza trwała wersja ma `parent_version_id=None` i powstaje wyłącznie po jawnej akcji koordynatora.
16. Materialna zmiana staffing/urlopu/dostępności/reguły unieważnia starą diagnozę; kolejny PLAN liczy na aktualnych danych.
17. Brak wymaganych służb/canonical demands nie może prowadzić do utworzenia pustego grafiku. Nieskonfigurowany obiekt jest poza zakresem T061.
18. T061 nie wdraża mechanizmu „zaakceptuj jeden HARD, solver dokłada resztę”; to pozostaje w `ODLOZONE.md`. Manualny root pozostaje ręczny.
19. T057 preview lifecycle, PlanPreview ownership, reject/accept semantics i brak durable zapisu przed `Użyj` pozostają bez zmian.
20. Spóźniony wynik wcześniej uruchomionego PLAN nie może po utworzeniu manualnego root przywrócić starego preview/`DECISION_REQUIRED`/innego starego blocker state ani zmienić current.
21. Symulatory Koordynatora A/B oraz stare benchmarki są zamrożone i nie są materiałem dowodowym T061.

## 3. Kierunek architektoniczny

Minimalny kierunek pozostaje reuse istniejących ownerów:
- canonical demands bez current: `assembler.assemble_planning_state -> generate_profile_demands`;
- pierwszy trwały root/current: `schedule_lifecycle.create_schedule_version(... parent_version_id=None ...)`;
- validate/deviation/T058 freeze/REST audit/action trail: współdzielić istniejącą logikę `manual_edit`, nie kopiować;
- techniczny root-compatible command/endpoint może istnieć, ale produktowo/UI nadal jest to jedna funkcja `Korekta ręczna`;
- `rota/application/plan_ops.py` wchodzi literalnie do scope wyłącznie dla guardu przed spóźnionym zapisem starego wyniku/preview po utworzeniu manual root;
- nie dodawać logiki obsługi `TECHNICAL_ERROR`, timeout/HTTP error ani nowego rejestru awarii w ramach T061;
- nie zmieniać istniejącej semantyki `DECISION_REQUIRED` ani `THIRD_CONSECUTIVE_SHIFT_BLOCKED` poza umożliwieniem wspólnej ręcznej drogi bez current;
- nie dodawać nowych reguł solvera, diagnostyki T062, seed-parenta, pustej working-version ani recovery subsystemu.

## 4. Acceptance

T61-01: normalny nowy miesiąc nadal zaczyna się od PLAN; T061 nie zmienia zwykłej ścieżki PLAN/wybór/Użyj.

T61-02: pierwszy PLAN zakończony kontrolowanym blockerem biznesowym nadal zostawia zero biznesowych `ScheduleVersion` przed jawną decyzją koordynatora.

T61-03: po `DECISION_REQUIRED`, przy braku current i dostępnych canonical danych miesiąca, koordynator może przejść do tej samej `Korekta ręczna` i zobaczyć wymagane służby do ręcznego obsadzenia; istniejąca logika `DECISION_REQUIRED` pozostaje bez zmian.

T61-04: po `THIRD_CONSECUTIVE_SHIFT_BLOCKED`, przy braku current i dostępnych canonical danych miesiąca, automat nadal nie tworzy kandydata łamiącego HARD, ale koordynator może przejść do tej samej `Korekta ręczna`, świadomie obsadzić trzecią służbę pod rząd i zapisać ją z ostrzeżeniem + `Deviation`/action trail.

T61-05: `TECHNICAL_ERROR`, HTTP error, timeout i awaria aplikacji NIE otwierają Route A T061 i nie otrzymują w tym tasku nowej logiki.

T61-06: `SEARCH_INCOMPLETE` nie jest traktowany jako wynik ordinary first PLAN ani wejście T061.

T61-07: nie istnieje osobny produktowy mechanizm `Ułóż ręcznie`; przy current nadal działa obecna Korekta ręczna bez regresji.

T61-08: incomplete first manual root jest odrzucany przed durable write; zero częściowych ScheduleVersion/current/action/deviation.

T61-09: kompletny first manual root tworzy dokładnie jedną trwałą wersję z `parent_version_id=None`, atomowo staje się current i ma prawidłowy action trail.

T61-10: każda świadoma ręczna decyzja koordynatora naruszająca HARD zachowuje nadrzędną zasadę: program ostrzega i zapisuje `Deviation`/audit, ale nie blokuje zapisu tylko dlatego, że HARD został naruszony; solver nie uczestniczy w tym override.

T61-11: materialna zmiana inputu po blockerze unieważnia starą diagnozę; ponowny PLAN liczy na aktualnych danych. Jeśli jest FEASIBLE, działa normalny flow.

T61-12: brak canonical required PRIMARY demands nie może zakończyć się zapisem pustego root schedule.

T61-13: spóźniony wynik wcześniej uruchomionego PLAN po utworzeniu manualnego root nie może przywrócić starego preview/blocker state ani nadpisać current.

T61-14: failure podczas manualnego durable write nie zostawia częściowej wersji/current/action/deviation.

T61-15: T057 PLAN/reject/rerun/accept lifecycle pozostaje bez regresji.

T61-16: źródłowe `test_2/test_3` mają chronić przypadek kontrolowanego business blocker -> brak current -> manual root, a nie awarię techniczną ani historyczny requirement current `DECISION_REQUIRED` jako osobnej autoryzacji persistence.

## 5. Literalny TASK_SCOPE do re-checku Codexa

IMPLEMENTATION HOLD do krótkiego ponownego re-checku aktualnego kontraktu.

Codex ma sprawdzić wyłącznie minimalny scope potrzebny do spełnienia powyższego kontraktu:
- `rota/application/manual_edit.py` — reuse validate/deviation/action + root-compatible command bez seed-parenta;
- `rota/application/plan_ops.py` — wyłącznie guard przed spóźnionym zapisem starego preview/blocker state po utworzeniu manual root;
- `api/routers/manual_edit.py` — wąski endpoint/payload dla pierwszego root, jeśli technicznie potrzebny;
- `frontend/src/screens/MonthlyPlanning.tsx` — awaryjne przejście do tej samej Korekty ręcznej po istniejącym kontrolowanym blockerze (`DECISION_REQUIRED` albo `THIRD_CONSECUTIVE_SHIFT_BLOCKED`), bez redefiniowania ich obecnych flow, bez redesignu T062 i bez obsługi awarii technicznych;
- `frontend/src/api/client.ts` — tylko typ/call potrzebny tej ścieżce;
- persistence/lifecycle tylko tam, gdzie rzeczywiście trzeba zagwarantować atomic root;
- wąskie testy T061 + źródłowe `test_2/test_3` + jeden real-browser Playwright vertical bez mocked backendu.

Codex ma jawnie potwierdzić trzy rzeczy: (1) HARD blokuje automat, nie świadomą decyzję koordynatora; (2) T061 nie tworzy równoległej logiki dla istniejących `DECISION_REQUIRED`/`THIRD_CONSECUTIVE_SHIFT_BLOCKED`, tylko usuwa brak-current manual-root gap; (3) T061 nie tworzy logiki dla `TECHNICAL_ERROR`, HTTP error, timeout ani REPLAN `SEARCH_INCOMPLETE`. Nie rozszerzać scope poza dowiedzioną potrzebę.

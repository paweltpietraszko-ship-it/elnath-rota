# ROTA-T061 — Korekta ręczna pierwszego grafiku bez current

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

SOURCE_FINDING: BOARD.md / `ROTA-T057-ROUTE-A-REGRESSION`

OWNER_ACCEPTED_2026-09-09: program nie może odebrać koordynatorowi świadomej ręcznej decyzji o naruszeniu reguły.

OWNER_RULING_2026-09-10_A: NORMALNY flow programu pozostaje bez zmian — użytkownik zaczyna od `PLAN`. T061 nie tworzy równoległego zwykłego workflow ręcznego.

OWNER_RULING_2026-09-10_B: **ZASADA NADRZĘDNA:** HARD ogranicza automat, nie koordynatora. Solver/PLAN/REPLAN/Przelicz Plan nigdy sam nie łamie HARD. Koordynator może na własną odpowiedzialność świadomie naruszyć HARD przez Korektę ręczną; system ma ostrzec oraz zapisać `Deviation`/action trail/pamięć decyzji, ale nie blokować człowieka.

OWNER_RULING_2026-09-10_C: T061 nie jest ogólną alternatywą po każdym blockerze. Jeżeli przeszkodę można usunąć przez zmianę danych (np. dodać pracownika, zmienić dostępność, skorygować urlop), właściwa droga to zmiana danych i ponowny `PLAN`.

OWNER_RULING_2026-09-10_D: jeżeli koordynator świadomie wybiera rozwiązanie wymagające naruszenia HARD, solver nie dostaje polecenia „złam HARD i ułóż resztę”. Taka decyzja należy do istniejącej `Korekty ręcznej`. T061 zapewnia wyłącznie, że ta funkcja działa także przy pierwszym grafiku, gdy nie ma jeszcze `current ScheduleVersion`.

OWNER_RULING_2026-09-10_E: T062 i T061 mają współpracować. T062 przekłada rozpoznany problem na praktyczne następne kroki dla koordynatora; T061 zapewnia techniczną możliwość wykonania ręcznej ścieżki wyjątku bez current. Koordynator nie musi znać nazw `HARD`, nazw statusów ani kuchni solvera.

OWNER_RULING_2026-09-10_F: `TECHNICAL_ERROR`, HTTP error, timeout, zawieszenie/utrata backendu lub inna awaria wykonania NIE są Route A T061. Nie wolno mieszać ich z rozpoznanym problemem biznesowym ani dodawać w T061 drugiej logiki obsługi awarii.

OWNER_RULING_2026-09-10_G: `DECISION_REQUIRED` i `THIRD_CONSECUTIVE_SHIFT_BLOCKED` zachowują własną istniejącą semantykę. T061 ich nie redefiniuje. W szczególności `THIRD_CONSECUTIVE_SHIFT_BLOCKED` oznacza tylko, że automat nie może legalnie utworzyć kandydata z trzecią kolejną służbą; koordynator nadal może świadomie zrobić to ręcznie.

OWNER_RULING_2026-09-10_H: T061 nie projektuje nowych zachowań dla nieskonfigurowanego obiektu ani dla awarii całej aplikacji. Brak wymaganych służb nie może prowadzić do utworzenia pustego grafiku.

## 1. Problem

Po T057 pierwszy PLAN dla nowego `(site, month)`, który nie prowadzi do zaakceptowanego grafiku, poprawnie może pozostawić zero biznesowych `ScheduleVersion`. To chroni zasadę, że preview/blocker nie staje się trwałym grafikiem przed jawną decyzją koordynatora.

Regresja polega na tym, że obecna `apply_manual_correction()` wymaga `current ScheduleVersion`. Jeżeli koordynator po rozpoznanym problemie świadomie wybiera ręczne ułożenie pierwszego grafiku — w szczególności dlatego, że akceptuje wyjątek, którego solver sam nie może naruszyć — funkcja nie ma na czym pracować i kończy się `NoCurrentScheduleVersion`.

Reprodukcja źródłowa: `task/ROTA-TEST-CLEANUP@2a8ca39`, `test_t011_e...::test_2` i `::test_3` -> `NoCurrentScheduleVersion`.

## 2. Zamrożony kontrakt OWNERA

1. Normalny nowy miesiąc zaczyna się od `PLAN`.
2. Solver nigdy sam nie łamie HARD.
3. Jeżeli program wskazuje praktyczną zmianę danych pozwalającą usunąć problem, koordynator zmienia dane i uruchamia `PLAN` ponownie. T061 nie zastępuje tej drogi.
4. Koordynator nie musi widzieć ani rozumieć pojęć `HARD`, nazw wewnętrznych reguł ani statusów solvera. Warstwa produktu ma mówić, co można zrobić dalej.
5. Jeżeli koordynator świadomie wybiera wyjątek, którego automat nie może wykonać, może przejść do tej samej istniejącej `Korekta ręczna`.
6. T061 zapewnia możliwość użycia `Korekty ręcznej` także bez current, wyłącznie po to, aby utworzyć pierwszy trwały manualny root dla miesiąca.
7. T061 nie tworzy osobnej funkcji `Ułóż ręcznie`, drugiego edytora ani równoległego normalnego workflow.
8. Gdy current istnieje, `Korekta ręczna` zachowuje dotychczasowy kontrakt.
9. Pierwszy ręczny root musi być kompletny: wszystkie wymagane PRIMARY demands miesiąca muszą być obsadzone przed durable write.
10. Świadome ręczne naruszenie HARD nie jest blokowane przez system: program ostrzega i zapisuje `Deviation`/action trail/pamięć decyzji. Solver nie uczestniczy w takim override.
11. Nie wolno tworzyć ukrytej/technicznej `ScheduleVersion` ani seed-parenta. Pierwsza trwała wersja ma `parent_version_id=None` i powstaje wyłącznie po jawnej akcji koordynatora.
12. Materialna zmiana staffing/urlopu/dostępności/reguły powoduje, że kolejny `PLAN` pracuje na aktualnych danych; starej diagnozy nie traktujemy jako autoryzacji ręcznego zapisu.
13. `DECISION_REQUIRED` zachowuje istniejący flow. T061 nie tworzy drugiego `DECISION_REQUIRED` ani nie daje automatycznego przejścia do ręcznego grafiku tylko dlatego, że taki status wystąpił.
14. `THIRD_CONSECUTIVE_SHIFT_BLOCKED` zachowuje istniejący sens. Automat nie tworzy kandydata wymagającego trzeciej kolejnej służby; koordynator może jednak świadomie utworzyć taki grafik przez Korektę ręczną, z `Deviation`/action trail.
15. `TECHNICAL_ERROR`, HTTP error, timeout i awaria aplikacji są poza T061. Nie dodawać dla nich nowej ścieżki manualnej w tym tasku.
16. `SEARCH_INCOMPLETE` należy do flow REPLAN/search i jest poza T061.
17. Brak wymaganych służb/canonical demands nie może prowadzić do utworzenia pustego root schedule. Nieskonfigurowany obiekt jest poza zakresem T061.
18. T061 nie wdraża mechanizmu „zaakceptuj jeden HARD, solver dokłada resztę”. Jeżeli owner wybiera wyjątek, manualny root pozostaje ręczny.
19. T057 preview lifecycle, PlanPreview ownership, reject/accept semantics i brak durable zapisu przed `Użyj` pozostają bez zmian.
20. Spóźniony wynik wcześniej uruchomionego PLAN nie może po utworzeniu manualnego root przywrócić starego preview/blocker state ani zmienić current.
21. Symulatory Koordynatora A/B oraz stare benchmarki są zamrożone i nie są materiałem dowodowym T061.

## 3. Relacja T061 ↔ T062

Docelowy produktowy flow ma być spójny, nie konkurencyjny:

`PLAN -> rozpoznany problem -> T062 pokazuje praktyczne następne kroki`

Jeżeli problem można usunąć bez świadomego wyjątku, koordynator zmienia dane (np. dodaje pracownika, zmienia dostępność, koryguje urlop) i uruchamia `PLAN` ponownie.

Jeżeli koordynator świadomie wybiera rozwiązanie, którego automat nie może wykonać z powodu wewnętrznej reguły HARD, przechodzi do istniejącej `Korekty ręcznej`. T061 zapewnia, że ta ręczna ścieżka działa również wtedy, gdy jest to pierwszy grafik i nie istnieje jeszcze current.

T062 nie ma objaśniać koordynatorowi wewnętrznej nomenklatury solvera. Ma mówić, co może zrobić dalej. T061 nie projektuje tych komunikatów.

## 4. Kierunek architektoniczny

Minimalny kierunek pozostaje reuse istniejących ownerów:
- canonical demands bez current: `assembler.assemble_planning_state -> generate_profile_demands`;
- pierwszy trwały root/current: `schedule_lifecycle.create_schedule_version(... parent_version_id=None ...)`;
- validate/deviation/T058 freeze/REST audit/action trail: współdzielić istniejącą logikę `manual_edit`, nie kopiować;
- techniczny root-compatible command/endpoint może istnieć, ale produktowo/UI nadal jest to jedna funkcja `Korekta ręczna`;
- `rota/application/plan_ops.py` wchodzi literalnie do scope wyłącznie dla guardu przed spóźnionym zapisem starego wyniku/preview po utworzeniu manual root;
- nie dodawać automatycznego przekierowania do Korekty ręcznej po każdym `DECISION_REQUIRED`;
- nie dodawać logiki obsługi `TECHNICAL_ERROR`, timeout/HTTP error ani nowego rejestru awarii w ramach T061;
- nie zmieniać istniejącej semantyki `DECISION_REQUIRED` ani `THIRD_CONSECUTIVE_SHIFT_BLOCKED`;
- nie dodawać nowych reguł solvera, diagnostyki T062, seed-parenta, pustej working-version ani recovery subsystemu.

## 5. Acceptance

T61-01: normalny nowy miesiąc nadal zaczyna się od PLAN; T061 nie zmienia zwykłej ścieżki PLAN/wybór/Użyj.

T61-02: pierwszy PLAN bez zaakceptowanego grafiku nadal może zostawić zero biznesowych `ScheduleVersion`.

T61-03: samo `DECISION_REQUIRED` nie oznacza automatycznego wejścia do Korekty ręcznej. Jeżeli T062 wskazuje praktyczną korektę danych, koordynator może ją wykonać i uruchomić PLAN ponownie.

T61-04: po `THIRD_CONSECUTIVE_SHIFT_BLOCKED` automat nadal nie tworzy kandydata łamiącego HARD. Jeżeli koordynator świadomie wybiera wyjątek, może przejść do tej samej `Korekta ręczna`, mimo braku current, i zapisać pierwszy kompletny root z ostrzeżeniem + `Deviation`/action trail.

T61-05: dla innego rozpoznanego problemu biznesowego ręczna ścieżka bez current jest dostępna tylko wtedy, gdy koordynator świadomie wybiera ręczne rozwiązanie; T061 nie wymusza jej jako standardowego następnego kroku.

T61-06: `TECHNICAL_ERROR`, HTTP error, timeout i awaria aplikacji NIE otrzymują w T061 nowej logiki.

T61-07: `SEARCH_INCOMPLETE` jest poza T061.

T61-08: nie istnieje osobny produktowy mechanizm `Ułóż ręcznie`; przy current nadal działa obecna Korekta ręczna bez regresji.

T61-09: incomplete first manual root jest odrzucany przed durable write; zero częściowych ScheduleVersion/current/action/deviation.

T61-10: kompletny first manual root tworzy dokładnie jedną trwałą wersję z `parent_version_id=None`, atomowo staje się current i ma prawidłowy action trail.

T61-11: świadome ręczne naruszenie HARD powoduje ostrzeżenie + `Deviation`/audit, ale nie jest blokowane; solver nie wykonuje override.

T61-12: materialna zmiana inputu powoduje, że ponowny PLAN liczy na aktualnych danych.

T61-13: brak canonical required PRIMARY demands nie może zakończyć się zapisem pustego root schedule.

T61-14: spóźniony wynik wcześniej uruchomionego PLAN po utworzeniu manualnego root nie może przywrócić starego preview/blocker state ani nadpisać current.

T61-15: failure podczas manualnego durable write nie zostawia częściowej wersji/current/action/deviation.

T61-16: T057 PLAN/reject/rerun/accept lifecycle pozostaje bez regresji.

T61-17: źródłowe `test_2/test_3` mają chronić rzeczywistą lukę `brak current -> świadomie wybrana Korekta ręczna -> first manual root`, a nie ustanawiać `DECISION_REQUIRED` jako automatyczną autoryzację manualnego flow.

## 6. Literalny TASK_SCOPE do re-checku Codexa

IMPLEMENTATION HOLD do krótkiego ponownego re-checku aktualnego kontraktu.

Codex ma sprawdzić wyłącznie minimalny scope potrzebny do spełnienia powyższego kontraktu:
- `rota/application/manual_edit.py` — reuse validate/deviation/action + root-compatible command bez seed-parenta;
- `rota/application/plan_ops.py` — wyłącznie guard przed spóźnionym zapisem starego preview/blocker state po utworzeniu manual root;
- `api/routers/manual_edit.py` — wąski endpoint/payload dla pierwszego root, jeśli technicznie potrzebny;
- `frontend/src/screens/MonthlyPlanning.tsx` — umożliwienie tej samej Korekty ręcznej przy świadomie wybranej ręcznej ścieżce bez current; bez automatycznego traktowania każdego blockera jako wejścia manualnego, bez redesignu T062 i bez obsługi awarii technicznych;
- `frontend/src/api/client.ts` — tylko typ/call potrzebny tej ścieżce;
- persistence/lifecycle tylko tam, gdzie rzeczywiście trzeba zagwarantować atomic root;
- wąskie testy T061 + źródłowe `test_2/test_3` + jeden real-browser Playwright vertical bez mocked backendu.

Codex ma jawnie potwierdzić cztery rzeczy: (1) HARD blokuje automat, nie świadomą decyzję koordynatora; (2) T061 nie jest automatyczną alternatywą po każdym blockerze; (3) T061 zapewnia first manual root bez current tylko dla świadomie wybranej ręcznej ścieżki; (4) T061 nie tworzy logiki dla `TECHNICAL_ERROR`, HTTP error, timeout ani REPLAN `SEARCH_INCOMPLETE`. Nie rozszerzać scope poza dowiedzioną potrzebę.

# ROTA-T061 — Korekta ręczna jako awaryjna droga po nieudanym pierwszym PLAN

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

SOURCE_FINDING: BOARD.md / `ROTA-T057-ROUTE-A-REGRESSION`
OWNER_ACCEPTED_2026-09-09: program nie może odebrać koordynatorowi świadomej ręcznej decyzji o naruszeniu reguły.
OWNER_RULING_2026-09-10_A: NORMALNY flow programu pozostaje bez zmian — użytkownik zaczyna od `PLAN`. T061 nie tworzy równoległego zwykłego workflow ręcznego.
OWNER_RULING_2026-09-10_B: T061 istnieje wyłącznie jako awaryjna droga, gdy pierwszy PLAN dla nowego `(site, month)` nie daje używalnego grafiku, ale aplikacja nadal poprawnie odczytuje obiekt, miesiąc, pracowników i wymagane służby.
OWNER_RULING_2026-09-10_C: koordynator może w Korekcie ręcznej świadomie naruszyć istniejący HARD; program ostrzega i zapisuje istniejący `Deviation`/action trail zgodnie z obecnym kontraktem manual correction, ale nie blokuje samej świadomej decyzji człowieka tam, gdzie produkt już dopuszcza override.
OWNER_RULING_2026-09-10_D: T061 nie projektuje nowych zachowań dla pustego/nieskonfigurowanego obiektu ani dla całkowitej awarii aplikacji. Brak wymaganych służb nie jest podstawą do tworzenia pustego grafiku. Gdy aplikacja nie potrafi odczytać danych potrzebnych także Korekcie ręcznej, pozostaje zwykły komunikat błędu/konieczność restartu lub kontaktu ze wsparciem; T061 nie buduje osobnego recovery subsystemu.
OWNER_RULING_2026-09-10_E: T061 nie projektuje pełnej diagnostyki zablokowanego PLAN i nie wdraża mechanizmu „zaakceptuj jeden HARD, solver dokłada resztę”. Diagnostyka jest osobnym draftem `ROTA-T062`; solver-dokończenie pozostaje w `ODLOZONE.md`.

## 1. Problem

Po T057 pierwszy nieudany/zablokowany PLAN dla nowego `(site, month)` poprawnie nie tworzy biznesowej `ScheduleVersion`. To chroni zasadę: preview/failure nie może stać się trwałym grafikiem przed akceptacją.

Regresja polega na tym, że obecna `apply_manual_correction()` wymaga `current ScheduleVersion`. Gdy pierwszy PLAN nie dał używalnego grafiku i nie istnieje jeszcze zaakceptowana wersja miesiąca, koordynator nie ma czego ręcznie skorygować. W praktyce znika awaryjna możliwość ułożenia pierwszego grafiku ręcznie.

Reprodukcja źródłowa: `task/ROTA-TEST-CLEANUP@2a8ca39`, `test_t011_e...::test_2` i `::test_3` -> `NoCurrentScheduleVersion`.

## 2. Zamrożony kontrakt OWNERA

1. Normalny flow pozostaje: `PLAN -> kandydat -> Użyj`. T061 niczego w nim nie zastępuje.
2. Solver nadal NIGDY nie łamie HARD automatycznie.
3. Pierwszy failed/blocked PLAN nadal nie tworzy `ScheduleVersion`, current, History/restore/export ani zaakceptowanego grafiku.
4. Jeśli po błędzie/blokadzie PLAN dane wejściowe nadal są czytelne i kompletne dla miesiąca, koordynator dostaje awaryjne przejście do tej samej funkcji `Korekta ręczna`.
5. Nie tworzymy konkurencyjnej funkcji `Ułóż ręcznie` ani drugiego edytora o innej semantyce.
6. Gdy current istnieje, `Korekta ręczna` zachowuje dotychczasowy kontrakt korekty istniejącego grafiku, w tym ochronę służb rozpoczętych/odbytych zgodnie z osobnym findingiem historycznej korekty.
7. Gdy current nie istnieje po nieudanym pierwszym PLAN, `Korekta ręczna` może utworzyć pierwszy trwały root schedule na podstawie canonical demands miesiąca.
8. Pierwszy ręczny root musi być kompletny: wszystkie wymagane PRIMARY demands miesiąca muszą być obsadzone przed durable write. Nie zapisujemy częściowego root z coverage gaps wynikających z niedokończonej edycji.
9. Koordynator może świadomie naruszyć HARD tam, gdzie obecny kontrakt manual correction dopuszcza override. Program ostrzega, materializuje `Deviation` i zapisuje action trail; nie blokuje świadomej decyzji tylko dlatego, że reguła jest HARD.
10. Nie wolno tworzyć ukrytej/technicznej `ScheduleVersion` ani seed-parenta tylko po to, aby użyć starej funkcji korekty. Pierwsza trwała wersja ma `parent_version_id=None` i powstaje wyłącznie po jawnej akcji koordynatora.
11. Materialna zmiana staffing/urlopu/dostępności/reguły po blocked PLAN unieważnia starą diagnozę. Koordynator może ponowić PLAN na aktualnych danych; jeśli PLAN staje się FEASIBLE, normalny flow rozwiązuje problem. T061 nie wykorzystuje historycznego `DECISION_REQUIRED` jako autoryzacji.
12. T061 nie wymaga technicznego `DECISION_REQUIRED` jako warunku samej ręcznej akcji. Warunkiem awaryjnej ścieżki jest brak current po nieudanym pierwszym PLAN oraz dostępność canonical danych potrzebnych do ręcznego ułożenia miesiąca.
13. `TECHNICAL_ERROR`/timeout PLAN nie jest diagnozą T062. Jeśli aplikacja nadal ma poprawne dane potrzebne do Korekty ręcznej, może zaoferować `Spróbuj ponownie` oraz przejście do `Korekta ręczna`. Jeśli nie ma tych danych lub aplikacja jest faktycznie niesprawna, T061 nie obiecuje działania — pozostaje zwykły komunikat techniczny/restart/wsparcie.
14. Brak wymaganych służb/canonical demands nie może prowadzić do utworzenia pustego grafiku. T061 nie projektuje nowego flow konfiguracji pustego obiektu; taki przypadek jest poza zakresem tego tasku.
15. T061 nie próbuje automatycznie dokończyć reszty miesiąca wokół pojedynczego ręcznego wyjątku. To pozostaje w `ODLOZONE.md`.
16. T061 nie definiuje pełnego UX „dlaczego PLAN nie dał grafiku”; to osobny `ROTA-T062`.
17. T057 preview lifecycle, PlanPreview ownership, reject/accept semantics i brak durable zapisu przed `Użyj` pozostają bez zmian.
18. Spóźniony wynik wcześniej uruchomionego PLAN nie może po utworzeniu manualnego root przywrócić starego preview/`DECISION_REQUIRED` ani zmienić current.
19. Symulatory Koordynatora A/B oraz stare benchmarki są zamrożone i nie są materiałem dowodowym T061.

## 3. Kierunek architektoniczny

Minimalny kierunek pozostaje reuse istniejących ownerów:
- canonical demands bez current: `assembler.assemble_planning_state -> generate_profile_demands`;
- pierwszy trwały root/current: `schedule_lifecycle.create_schedule_version(... parent_version_id=None ...)`;
- validate/deviation/T058 freeze/REST audit/action trail: współdzielić istniejącą logikę `manual_edit`, nie kopiować;
- osobny root-compatible command/endpoint może istnieć technicznie, ale UI i produktowo ma to być nadal jedna funkcja `Korekta ręczna`;
- payload pierwszego ręcznego zapisu reprezentuje kompletny zestaw przypisań PRIMARY dla canonical demands miesiąca;
- nie dodawać nowych reguł solvera, nowej diagnostyki T062, seed-parenta, pustej working-version ani osobnego subsystemu recovery.

Wymaga ponownego krótkiego re-checku, ponieważ poprzedni PREIMPLEMENTATION PASS (`6dcafc9`) dotyczył starszego kontraktu wymagającego aktualnego `DECISION_REQUIRED` i nie obejmuje obecnego zakresu.

## 4. Acceptance

T61-01: normalny nowy miesiąc nadal zaczyna się od PLAN; T061 nie zmienia zwykłej ścieżki PLAN/wybór/Użyj.

T61-02: pierwszy failed/blocked PLAN nadal zostawia zero `ScheduleVersion`.

T61-03: po takim nieudanym PLAN, przy braku current i przy dostępnych canonical danych miesiąca, koordynator może przejść do tej samej `Korekta ręczna` i zobaczyć wymagane służby do ręcznego obsadzenia.

T61-04: nie istnieje osobny produktowy mechanizm `Ułóż ręcznie`; przy current nadal działa obecna Korekta ręczna bez regresji.

T61-05: incomplete first manual root jest odrzucany przed durable write; zero częściowych ScheduleVersion/current/action/deviation.

T61-06: kompletny first manual root tworzy dokładnie jedną trwałą wersję z `parent_version_id=None`, atomowo staje się current i ma prawidłowy action trail.

T61-07: ręczne świadome naruszenie HARD zachowuje istniejącą semantykę manual correction: ostrzeżenie + `Deviation`/audit, bez automatycznego solver override i bez blokowania świadomej decyzji koordynatora tam, gdzie taki override jest już dozwolony.

T61-08: materialna zmiana inputu po blocked PLAN unieważnia stary wynik; ponowny PLAN liczy na aktualnych danych. Jeśli jest FEASIBLE, działa normalny flow.

T61-09: `TECHNICAL_ERROR`/timeout przy nadal dostępnych danych nie tworzy nic trwałego i nie blokuje awaryjnego przejścia do Korekty ręcznej; brak danych potrzebnych także Korekcie ręcznej nie jest naprawiany przez T061.

T61-10: brak canonical required PRIMARY demands nie może zakończyć się zapisem pustego root schedule.

T61-11: spóźniony wynik wcześniej uruchomionego PLAN po utworzeniu manualnego root nie może przywrócić starego preview/decision ani nadpisać current.

T61-12: failure podczas manualnego durable write nie zostawia częściowej wersji/current/action/deviation.

T61-13: T057 PLAN/reject/rerun/accept lifecycle pozostaje bez regresji.

T61-14: źródłowe `test_2/test_3` mają zostać skorygowane do aktualnego PRODUCT_TRUTH, bez utrwalania dawnego wymagania current `DECISION_REQUIRED` jako jedynego wejścia do ręcznej ścieżki.

## 5. Literalny TASK_SCOPE do re-checku Codexa

IMPLEMENTATION HOLD do krótkiego ponownego re-checku aktualnego kontraktu.

Codex ma sprawdzić wyłącznie minimalny scope potrzebny do spełnienia powyższego kontraktu. Punktem wyjścia są te same owners co wcześniej:
- `rota/application/manual_edit.py` — reuse validate/deviation/action + root-compatible command bez seed-parenta;
- `api/routers/manual_edit.py` — wąski endpoint/payload dla pierwszego root, jeśli technicznie potrzebny;
- `frontend/src/screens/MonthlyPlanning.tsx` — awaryjne przejście do tej samej Korekty ręcznej po nieudanym pierwszym PLAN i kompletna ręczna siatka canonical demands; bez redesignu T062;
- `frontend/src/api/client.ts` — tylko typ/call potrzebny tej ścieżce;
- persistence/lifecycle tylko tam, gdzie rzeczywiście trzeba zagwarantować atomic root i ochronę przed spóźnionym wynikiem PLAN;
- wąskie testy T061 + źródłowe `test_2/test_3` + jeden real-browser Playwright vertical bez mocked backendu.

Codex ma jawnie wskazać, czy poprzednio proponowany `site_memory` current-decision pre-check jest już zbędny po usunięciu wymagania aktualnego `DECISION_REQUIRED`, oraz jaki minimalny mechanizm chroni przed spóźnionym wynikiem PLAN. Nie rozszerzać scope poza dowiedzioną potrzebę.

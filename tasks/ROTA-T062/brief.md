# ROTA-T062 — Jedna ścieżka po nieudanym planowaniu

STATUS: PREIMPLEMENTATION RE-CHECK REQUIRED — IMPLEMENTATION HOLD

BASELINE: `main@f1cfb05e85ef19ad4bfa714a51b7e187e57caaa4`

SOURCE: OWNER decisions 2026-09-10 + Codex R1/R2 + inspekcja CC obecnego `decision_guidance`/UI.

## 1. Cel produktu

Koordynator nie ma zostać po nieudanym planowaniu ze ścianą „nie da się”. Program ma powiedzieć **co można zrobić dalej** i po zmianie danych pozwolić uruchomić planowanie ponownie.

T062 NIE tworzy drugiej ścieżki obsługi problemów. Istniejący backendowy mechanizm kontrolowanego zatrzymania planowania pozostaje właścicielem diagnozy: engine tworzy `DECISION_REQUIRED`/`decision_payload`, stan jest utrwalany i pokazywany w UI. T062 ulepsza tę istniejącą ścieżkę. `THIRD_CONSECUTIVE_SHIFT_BLOCKED` zachowuje własny status T058, ale ma korzystać z tej samej utrwalonej warstwy guidance dla użytkownika.

## 2. Zamrożone decyzje OWNERA

1. **Jedna ścieżka.** Nie tworzyć równoległego modelu, osobnego „asystenta naprawy”, drugiej kolejki decyzji ani konkurencyjnego flow.
2. Koordynatora nie interesuje nomenklatura solvera. UI nie ma wymagać znajomości `HARD`, nazw wewnętrznych reguł, kodów statusów ani technicznej kuchni programu.
3. Główna informacja dla koordynatora brzmi praktycznie: **co może zrobić dalej**. Potwierdzone klasy działań: zmienić obsadę, dodać pracownika/wsparcie, zmienić dostępność, skorygować nieobecność lub inne dane dostępne w istniejącym produkcie, a następnie uruchomić planowanie ponownie.
4. Program nie może obiecywać, że pojedyncza zmiana na pewno da FEASIBLE. Sugestia działania nie jest kontrfaktyczną gwarancją.
5. Po materialnej zmianie danych stara diagnoza nie jest prawdą o nowym stanie. Potrzebne jest nowe planowanie na aktualnych danych.
6. **Pierwszy grafik miesiąca powstaje wyłącznie przez `PLAN`.** `ROTA-T061` jest RETIRED. T062 nie tworzy first-manual-root, pustego grafiku ani pełnomiesięcznego edytora ręcznego.
7. Jeśli po dopuszczalnych zmianach nadal nie da się utworzyć grafiku, brak grafiku (`zero ScheduleVersion/current`) jest poprawnym wynikiem biznesowym, nie `TECHNICAL_ERROR`.
8. Istniejąca `Korekta ręczna` pozostaje osobną funkcją dla grafiku, który już istnieje. T062 nie projektuje nowej Korekty ręcznej i nie musi jej proponować jako guidance.
9. `TECHNICAL_ERROR`, HTTP error, timeout, utrata/zawieszenie backendu i inne awarie techniczne są poza T062. Ich UX należy do `ROTA-TECHNICAL-ERROR-RECOVERY-UX`.
10. `NO_ALTERNATIVE`, `NARROW_SEARCH_EXHAUSTED` i `SEARCH_INCOMPLETE` są stanami lifecycle wyszukiwania REPLAN, nie drugą diagnozą blockerów. T062 ich nie przebudowuje.
11. **Nie projektujemy żadnego nowego edytora reguł.** Repo nie udostępnia koordynatorowi ogólnego kreatora dowolnych „zapisanych reguł obiektu”. Znane reguły prowadzą tylko do istniejących miejsc produktu. Nierozpoznany/stary wpis może być uczciwą informacją bez przycisku; nie tworzy to nowej funkcji produktu.
12. **Nie zgadywać rzeczywistości operacyjnej.** Jeżeli z kodu i zaakceptowanych kontraktów nie wynika, że konkretna akcja użytkownika naprawdę istnieje, nie inventować procedury ani ekranu.

## 3. Jeden istniejący owner guidance

`rota/planning/decision_guidance.py` pozostaje warstwą tłumaczącą fakty engine na koordynatorowe guidance. `build_unblocking_options()`/następca tego kontraktu jest jednym ownerem treści oraz stabilnego celu działania.

`frontend/src/screens/Decisions.tsx` i `frontend/src/screens/MonthlyPlanning.tsx` mogą prezentować ten sam utrwalony problem w dwóch miejscach UI, ale nie mogą wyliczać innych rozwiązań ani opierać nawigacji na własnej interpretacji tekstu.

`THIRD_CONSECUTIVE_SHIFT_BLOCKED` nie zmienia statusu i nie staje się `DECISION_REQUIRED`. Ma jednak otrzymać ten sam koordynatorowy payload/guidance i trwały readback, aby po reloadzie użytkownik widział aktualny problem zamiast wcześniejszego, nieaktualnego `DECISION_REQUIRED`.

## 4. Potwierdzone luki

1. `unblocking_options` są dziś `list[str]`, a `Decisions.tsx::optionTarget()` rozpoznaje cel po prefiksie polskiego tekstu. To jest kruche i miesza treść z nawigacją.
2. Nowy kształt pojedynczej opcji ma być małym obiektem: **tekst + stabilny cel albo brak celu**. Nie dodawać workflow engine ani URL-i z backendu.
3. Dozwolone cele T062 są wyłącznie istniejącymi miejscami produktu: `Obsada`, istniejąca karta pracownika, `Obiekt`, albo brak celu = informacja bez przycisku.
4. Stare snapshoty `list[str]` muszą nadal być czytelne bez migracji tabeli; historyczny string jest tekstem bez celu.
5. `NIGHT-STREAK-01` nie ma dziś kompletnej sugestii działania; zaakceptowany recovery to sprawdzenie obsady/dostępności i ponowne planowanie, bez gwarancji wyniku.
6. `THIRD_CONSECUTIVE_SHIFT_BLOCKED` nie buduje dziś payloadu. Ma zachować osobny status, ale korzystać z tej samej koordynatorowej guidance: sprawdź obsadę/dostępność i zaplanuj ponownie. Bez solver override, bez kandydata łamiącego regułę, bez T061.
7. `_persist_decision_readback()` dziś może pozostawić wcześniejszy `current_decision_required` po świeżym wyniku THIRD. T062 musi sprawić, że świeży THIRD zastąpi/wyczyści stary readback i sam będzie utrwalony jako aktualne guidance.
8. Obecne teksty sugerujące „Ręczna korekta mimo Chorobowe/Urlop/REST” nie mogą być ogólnym guidance dla no-current. Najmniejszy T062 nie musi proponować Korekty ręcznej w ogóle.
9. Dla nierozpoznanej historycznej/ogólnej reguły bez istniejącego edytora: informacja bez przycisku jest poprawna. Nie kierować fałszywie do katalogu zmian i nie budować nowego edytora.

## 5. Fakt vs działanie

Backend może potrzebować faktów blokujących do audytu/pamięci. To nie oznacza, że UI ma robić z nich wykład dla koordynatora.

T062 rozdziela semantycznie:
- **fakt/evidence:** co engine rzeczywiście ustalił;
- **działanie:** operacja, którą koordynator rzeczywiście może wykonać w istniejącym produkcie.

Sugestia działania musi wynikać z evidence. Nie wolno tworzyć sugestii z domysłu. Przy wielu niezależnych blockerach nie wolno ukrywać materialnych, wiarygodnie ustalonych przeszkód przez przypadkowy wybór pierwszej pasującej reguły.

## 6. Flow użytkownika

### A. Brak istniejącego grafiku

`PLAN -> kontrolowany brak grafiku -> utrwalone guidance pokazuje realne następne działania -> koordynator zmienia dane -> PLAN ponownie`

Jeżeli nadal nie ma rozwiązania:

`PLAN -> brak automatycznego grafiku przy aktualnych danych -> zero current pozostaje poprawne`

Nie ma przejścia do budowy pełnego grafiku ręcznie od zera.

### B. Grafik już istnieje

Późniejsze PLAN/REPLAN/Przelicz Plan korzysta z tej samej warstwy guidance dla kontrolowanych blockerów. T062 nie tworzy osobnego „REPLAN diagnostic flow” i nie zmienia kontraktu Korekty ręcznej ani lifecycle ScheduleVersion.

## 7. Literalny TASK_SCOPE

Production paths:
- `rota/planning/engine_types.py` — ustrukturyzowana pojedyncza opcja działania;
- `rota/planning/decision_guidance.py` — jeden owner tekstu i stabilnego celu działania;
- `rota/planning/engine.py` — NIGHT-STREAK oraz THIRD przez wspólną guidance, przy zachowaniu osobnego statusu THIRD i bez solver override;
- `rota/application/plan_ops.py` — zapis/wyczyszczenie aktualnej guidance także dla THIRD, bez pozostawienia starego pointera;
- `rota/persistence/site_memory.py` — zapis/odczyt nowego kształtu oraz zgodny odczyt starych `list[str]`;
- `api/decision_payload.py` — wspólny adapter;
- `api/routers/decisions.py` — wspólny typ pola opcji;
- `frontend/src/api/client.ts` — ten sam typ;
- `frontend/src/screens/Decisions.tsx` — nawigacja po stabilnym celu, bez prefix matching;
- `frontend/src/screens/MonthlyPlanning.tsx` — czytelna prezentacja utrwalonego problemu i brak surowego statusu THIRD w UI.

Poza scope:
- `solver.py`;
- validator;
- `manual_edit.py`;
- lifecycle `ScheduleVersion`;
- nowy endpoint;
- nowa tabela;
- nowy ekran;
- nowy edytor reguł;
- nowy edytor grafiku;
- first manual root;
- solver override;
- przebudowa search-only statuses;
- obsługa awarii technicznych.

Nie dodawać `Room.tsx`/`ControlPanel.tsx`/`EmployeeDetail.tsx` do scope, jeśli istniejące cele można wykorzystać bez zmian tych ekranów. Rozszerzenie scope wymaga konkretnego dowodu z implementacji/audytu, nie przypuszczenia.

## 8. Acceptance

T62-01 — Jeden backendowy owner: nie powstaje drugi model diagnozy/naprawy obok istniejącego decision guidance/memory.

T62-02 — Po kontrolowanym blocked PLAN koordynator widzi rzeczywiste, evidence-backed następne działanie albo uczciwy komunikat, że przy aktualnych danych program nie potrafi ułożyć grafiku.

T62-03 — UI nie wymaga znajomości `HARD`, `DECISION_REQUIRED`, `THIRD_CONSECUTIVE_SHIFT_BLOCKED`, nazw kodów reguł ani technicznych identyfikatorów.

T62-04 — Każdy element z celem prowadzi do istniejącego miejsca produktu. Element bez celu jest informacją, nie martwym przyciskiem. Zmiana tekstu nie zmienia nawigacji.

T62-05 — Sugestia jest evidence-backed i nie pojawia się dla warunku, którego engine nie ustalił.

T62-06 — Przy wielu wiarygodnych blockerach wszystkie materialne działania/informacje są zachowane deterministycznie.

T62-07 — Żadna sugestia nie gwarantuje FEASIBLE po pojedynczej zmianie.

T62-08 — Po materialnej zmianie danych stary readback znika/nie jest prezentowany jako aktualny; kolejne planowanie liczy od nowa.

T62-09 — No-current: SICK/LEAVE/REST ani inne blockery nie oferują first manual root. Jeżeli PLAN nadal nie daje grafiku, zero ScheduleVersion/current pozostaje poprawne.

T62-10 — No-current: NIGHT i THIRD pokazują istniejące działanie typu Obsada/dostępność + ponowne planowanie albo uczciwy brak rozwiązania.

T62-11 — THIRD zachowuje osobny status; jego guidance jest utrwalone, przeżywa reload i zastępuje wcześniejszy nieaktualny readback.

T62-12 — Existing-current: T062 nie tworzy nowej Korekty ręcznej, nie zmienia i nie nadpisuje istniejącej wersji grafiku.

T62-13 — `TECHNICAL_ERROR`/HTTP/timeout oraz `NO_ALTERNATIVE`/`NARROW_SEARCH_EXHAUSTED`/`SEARCH_INCOMPLETE` nie dostają business guidance T062.

T62-14 — Schedule endpoint i Decisions endpoint zwracają ten sam kształt/semantykę guidance dla tego samego aktywnego problemu.

T62-15 — Stare snapshoty `list[str]` nadal się odczytują jako tekst bez celu; brak migracji tabeli.

T62-16 — Dla nierozpoznanej starej/ogólnej reguły bez istniejącego edytora nie powstaje nowy edytor ani fałszywy przycisk; dopuszczalna jest informacja bez celu.

## 9. Test scope

- nowy `tests/test_t062.py`;
- aktualizacja oczekiwań kształtu w `tests/test_t013.py` i wspólnego API w `tests/test_t042_audit4_repairs.py`;
- wąski realny pion API persistence/reload dla zwykłego `DECISION_REQUIRED` i THIRD;
- jeden Playwright przez realny backend: `PLAN blocked -> czytelne działania -> rzeczywiste przejście do Obsady -> zmiana danych -> stara diagnoza znika -> ponowny PLAN`;
- optyczna/behawioralna zgodność obu istniejących miejsc UI.

Zamrożone symulatory A/B i stare benchmarki nie są materiałem dowodowym T062.

## 10. Następny krok

Codex ma wykonać wyłącznie krótki literalny re-check tego SHA względem raportu R2. Nie powtarzać WHERE_MAP ani szerokiej mapy kodu, o ile scope/ownership nie zmienił się materialnie.

Do sprawdzenia:
1. czy brief dokładnie odzwierciedla R2;
2. czy literalny TASK_SCOPE nie zawiera nowej funkcji produktu;
3. czy zachowano osobny status THIRD bez starego readbacku;
4. czy nie reaktywowano T061 ani żadnego nowego edytora;
5. czy można po re-checku zwolnić IMPLEMENTATION HOLD.

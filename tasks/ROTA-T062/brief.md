# ROTA-T062 — Jedna ścieżka po nieudanym planowaniu

STATUS: PREIMPLEMENTATION AUDIT REQUIRED — IMPLEMENTATION HOLD

BASELINE: `main@f1cfb05e85ef19ad4bfa714a51b7e187e57caaa4`

SOURCE: OWNER decisions 2026-09-10 + wcześniejsza falsyfikacja Codexa + inspekcja CC obecnego `decision_guidance`/UI.

## 1. Cel produktu

Koordynator nie ma zostać po nieudanym planowaniu ze ścianą „nie da się”. Program ma powiedzieć **co można zrobić dalej** i po zmianie danych pozwolić uruchomić planowanie ponownie.

T062 NIE tworzy drugiej ścieżki obsługi problemów. Dziś istnieje już jeden backendowy mechanizm kontrolowanego zatrzymania planowania: engine tworzy `DECISION_REQUIRED`/`decision_payload`, a ten stan jest utrwalany i pokazywany w UI. T062 ma ulepszyć tę istniejącą ścieżkę, nie budować obok niej nowego systemu diagnostycznego.

## 2. Zamrożone decyzje OWNERA

1. **Jedna ścieżka.** Kontrolowany problem biznesowy po `PLAN`/planowaniu ma korzystać z istniejącego `decision_payload` / zapisanego `DECISION_REQUIRED`. Nie tworzyć równoległego modelu, osobnego „asystenta naprawy”, drugiej kolejki decyzji ani konkurencyjnego flow.
2. Koordynatora nie interesuje nomenklatura solvera. UI nie ma wymagać znajomości `HARD`, nazw wewnętrznych reguł, kodów statusów ani technicznej kuchni programu.
3. Główna informacja dla koordynatora brzmi praktycznie: **co może zrobić dalej**. Przykładowe klasy działań już potwierdzone przez OWNERA: zmienić obsadę (np. dodać pracownika), zmienić dostępność, skorygować kolidujący zapis/urlop — a następnie uruchomić planowanie ponownie.
4. Program nie może obiecywać: „zmień X i na pewno powstanie grafik”, jeśli tego nie dowiódł. Sugestia działania nie jest kontrfaktyczną gwarancją FEASIBLE.
5. Po materialnej zmianie danych stara diagnoza nie jest autoryzacją ani prawdą o nowym stanie. Potrzebny jest nowy `PLAN`/właściwe ponowne planowanie na aktualnych danych.
6. **Pierwszy grafik miesiąca powstaje wyłącznie przez `PLAN`.** `ROTA-T061` jest RETIRED. T062 nie może tworzyć first-manual-root, pustego ręcznego grafiku ani pełnomiesięcznego edytora od zera.
7. Jeśli po dopuszczalnych zmianach nadal nie da się utworzyć grafiku, brak grafiku (`zero ScheduleVersion/current`) jest poprawnym wynikiem biznesowym. Program ma to zakomunikować prostym językiem; nie jest to `TECHNICAL_ERROR`.
8. Istniejąca `Korekta ręczna` pozostaje korektą grafiku, który już istnieje. T062 nie rozszerza jej na brak `current`. Jeżeli przy istniejącym grafiku obecny kontrakt produktu już dopuszcza konkretną ręczną korektę, T062 może co najwyżej prowadzić do **tej istniejącej operacji**; nie projektuje nowej.
9. `TECHNICAL_ERROR`, HTTP error, timeout, utrata/zawieszenie backendu i inne awarie techniczne są poza T062. Ich UX należy do `ROTA-TECHNICAL-ERROR-RECOVERY-UX`.
10. `THIRD_CONSECUTIVE_SHIFT_BLOCKED` może zachować odrębną semantykę wewnętrzną T058. Warstwa użytkownika nie ma jednak zmuszać koordynatora do rozumienia tej nazwy.
11. **Nie zgadywać rzeczywistości operacyjnej.** Jeżeli z kodu/istniejących zaakceptowanych kontraktów nie wynika, jakie działanie koordynator rzeczywiście może wykonać dla danego blockera, implementer/audytor nie inventuje procedury. Zwraca precyzyjne `OWNER_DECISION_NEEDED` z jednym pytaniem o rzeczywisty proces.

## 3. Co istnieje dzisiaj — nie budować drugi raz

`rota/planning/decision_guidance.py` jest już warstwą tłumaczącą fakty solvera na treść koordynatora. `build_unblocking_options()` generuje `unblocking_options`, a `build_decision_payload()` wypełnia istniejący `DecisionRequiredPayload`.

`frontend/src/screens/Decisions.tsx` czyta gotowy payload i pokazuje „Możliwe rozwiązania”. Ekran planowania także korzysta z utrwalonego `view.decision_required`; istniejący komentarz w `MonthlyPlanning.tsx` określa ten trwały stan jako source of truth po `DECISION_REQUIRED`.

Wniosek architektoniczny T062: **jeden owner danych i jednej diagnozy backendowej; wiele miejsc UI może prezentować ten sam stan, ale nie może istnieć drugi mechanizm ustalający inne „rozwiązanie”.**

## 4. Potwierdzone luki z inspekcji CC

Te punkty są materiałem do audytu Codexa, nie automatycznym nakazem konkretnej implementacji:

1. `decision_guidance.py::_ACTION_TEMPLATES` już generuje część praktycznych sugestii, ale nie wszystkie są dziś rzeczywistymi akcjami w UI.
2. `Decisions.tsx::optionTarget()` rozpoznaje nawigację tylko dla części tekstów (`Zmień...`, `Skonfiguruj...`). Inne sugestie renderują się jako martwy tekst. T062 ma doprowadzić do zasady: jeśli UI przedstawia coś jako możliwe działanie, musi istnieć rzeczywista droga wykonania albo tekst nie może udawać akcji.
3. `NIGHT-STREAK-01` ma dziś opis warunku, lecz brak odpowiadającego szablonu działania w `_ACTION_TEMPLATES`. **Nie wymyślać działania**; Codex ma sprawdzić istniejący zaakceptowany kontrakt i UI. Jeśli rzeczywista operacja nie jest jednoznaczna — `OWNER_DECISION_NEEDED`.
4. `THIRD_CONSECUTIVE_SHIFT_BLOCKED` z T058 nie buduje obecnie `decision_payload`. Codex ma sprawdzić, jak najwężej włączyć ten kontrolowany wynik do jednej ścieżki użytkownika bez zmiany reguły T058 i bez reaktywowania T061. Dla pierwszego grafiku nie istnieje ręczny root.
5. Obecne `unblocking_options` są gołymi polskimi stringami, a frontend rozpoznaje cel po prefiksie tekstu. To jest potwierdzona kruchość. Codex ma ocenić **minimalny** sposób usunięcia tej kruchości; nie tworzyć nowej platformy workflow, jeśli wystarczy małe rozszerzenie istniejącego DTO/kontraktu.

## 5. Zasada „fakt” vs „działanie” — uwaga z wcześniejszej falsyfikacji Codexa

Backend może potrzebować faktów blokujących do audytu, pamięci i deterministycznego wyliczenia sugestii. To nie znaczy, że UI ma robić z nich wykład dla koordynatora.

T062 rozdziela semantycznie:
- **fakt/evidence:** co engine rzeczywiście ustalił;
- **działanie:** operacja, którą koordynator rzeczywiście może wykonać.

Sugestia działania musi wynikać z evidence. Nie wolno tworzyć sugestii z domysłu ani losowo wybierać jednej przy wielu wiarygodnych blockerach.

Jeżeli istnieje wiele niezależnych blockerów, payload nie może ukryć materialnych, wiarygodnie ustalonych przeszkód tylko dlatego, że pierwsza pasuje do szablonu. Jednocześnie UI ma pozostać użytkowe: pokazać działania, a nie surowy dump solvera.

## 6. Docelowy flow użytkownika

### A. Brak istniejącego grafiku

`PLAN -> kontrolowany brak grafiku -> istniejąca ścieżka decision/guidance pokazuje realne następne działania -> koordynator zmienia dane -> PLAN ponownie`

Jeżeli nadal nie ma rozwiązania:

`PLAN -> brak automatycznego grafiku przy aktualnych danych -> zero current pozostaje poprawne`

Nie ma przejścia do budowy pełnego grafiku ręcznie od zera.

### B. Grafik już istnieje

T062 nadal używa **tej samej warstwy decision/guidance** dla kontrolowanego problemu podczas właściwego późniejszego planowania. Nie tworzyć osobnego „REPLAN diagnostic flow”. Różnica może dotyczyć wyłącznie działań, które są już legalnie dostępne w aktualnym stanie produktu (np. istniejąca korekta konkretnego assignmentu). T062 nie zmienia kontraktu tych operacji.

## 7. Acceptance

T62-01 — Jeden backendowy owner: nie powstaje drugi model diagnozy/naprawy obok istniejącego `DecisionRequiredPayload`/decision memory.

T62-02 — Po kontrolowanym blocked PLAN koordynator widzi co najmniej jedno z dwóch: (a) rzeczywiste, evidence-backed następne działanie; albo (b) uczciwy komunikat, że przy aktualnych danych program nie potrafi ułożyć grafiku. Nie ma technicznego „radź sobie sam”.

T62-03 — Użytkownik nie musi znać słów `HARD`, `DECISION_REQUIRED`, `THIRD_CONSECUTIVE_SHIFT_BLOCKED`, nazw wewnętrznych kodów reguł ani identyfikatorów technicznych, aby wiedzieć co zrobić dalej.

T62-04 — Każda sugestia przedstawiona jako działanie ma rzeczywiste miejsce wykonania w istniejącym produkcie. Martwa sugestia nie może wyglądać jak akcja.

T62-05 — Sugestia jest evidence-backed: nie pojawia się dla warunku, którego engine nie ustalił.

T62-06 — Przy wielu wiarygodnie ustalonych blockerach produkt nie ukrywa materialnej przeszkody przez przypadkowy wybór jednej.

T62-07 — Żadna sugestia nie gwarantuje FEASIBLE po pojedynczej zmianie, jeśli solver tego nie udowodnił.

T62-08 — Po materialnej zmianie staffing/urlopu/dostępności/reguły stara diagnoza nie może być użyta jako aktualna; nowe planowanie pracuje na aktualnym stanie.

T62-09 — Dla pierwszego grafiku nie istnieje ścieżka `Korekta ręczna -> first manual root`. Jeżeli PLAN nadal nie daje grafiku, zero ScheduleVersion/current pozostaje poprawne.

T62-10 — Dla istniejącego grafiku T062 nie tworzy nowej korekty ręcznej; może wskazać tylko operację już istniejącą i dozwoloną przez jej własny kontrakt.

T62-11 — `TECHNICAL_ERROR`/HTTP/timeout nie są mapowane na business guidance T062.

T62-12 — `NIGHT-STREAK-01` i `THIRD_CONSECUTIVE_SHIFT_BLOCKED` nie mogą zostać „naprawione” przez wymyślenie działania niepotwierdzonego kontraktem; brak wiedzy o realnej procedurze => OWNER_DECISION_NEEDED.

T62-13 — Oba istniejące miejsca prezentacji (planowanie miesiąca i „Decyzje koordynatora”), jeśli pokazują ten sam aktywny problem, korzystają z tego samego utrwalonego payloadu/semantyki i nie podają sprzecznych działań.

## 8. Preimplementation audit Codexa

IMPLEMENTATION HOLD.

Codex ma najpierw wykonać wąski audyt tego briefu względem realnego kodu i odpowiedzieć:

1. Czy rzeczywiście istnieje jeden owner `DECISION_REQUIRED`/decision guidance dla PLAN i późniejszego planowania, czy gdzieś istnieje druga ścieżka, którą brief przeoczył?
2. Jaki jest minimalny zestaw plików do T062 — bez przepisywania solvera i bez reaktywowania T061?
3. Jak minimalnie usunąć kruchość `unblocking_options: list[str]` + frontend prefix matching, zachowując istniejący DTO/persistence tam, gdzie to możliwe?
4. Dla których obecnych blockerów istnieje już realna, zaakceptowana akcja użytkownika, a dla których potrzebna jest decyzja OWNERA o rzeczywistym procesie?
5. Jak objąć `THIRD_CONSECUTIVE_SHIFT_BLOCKED` jedną ścieżką użytkownika bez zmiany T058 i bez manual root dla pierwszego grafiku?
6. Jakie testy acceptance są konieczne, aby dowieść jednego spójnego flow zarówno bez current, jak i z istniejącym current?

Raport Codexa ma być falsyfikacją briefu, nie projektem nowego systemu. Jeśli natrafi na nieustaloną rzeczywistość operacyjną, ma zadać jedno precyzyjne pytanie OWNEROWI zamiast ją wymyślać.

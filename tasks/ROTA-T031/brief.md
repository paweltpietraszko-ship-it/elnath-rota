# ROTA-T031 — Planowanie miesiąca

Status: **IMPLEMENTACJA ZAKOŃCZONA (autor: CC), do audytu**

Base implementation SHA: `3be4ed37e735766a80ca2259c7d1b6981d22dbb5` (`main`,
po zmergowaniu T030).

Owner decision: Paweł, 2026-08-24 — logiczne rozwinięcie Pulpitu i Panelu
sterowania. Function list zaakceptowana bez uwag przed tym briefem.

TASK_SCOPE:
- api/main.py
- api/errors.py
- api/routers/schedule.py
- frontend/src/api/client.ts
- frontend/src/screens/Room.tsx
- frontend/src/App.css
- frontend/src/screens/MonthlyPlanning.tsx
- tests/test_t031_schedule_api.py
- frontend/e2e/monthly-planning.spec.ts

## 1. Wynik dla właściciela

Zakładka „Planowanie miesiąca” przestaje być wyszarzonym placeholderem.
Koordynator: wybiera miesiąc, uruchamia PLAN (pierwsze uruchomienie albo
przeliczenie), widzi siatkę pracownik×dzień z aktualnie zapisanym stanem,
wybiera jednego z kandydatów solvera, może zrobić REPLAN po dacie odcięcia,
widzi odchylenia (Deviation) z polskimi etykietami i finalizuje miesiąc po
potwierdzeniu dokładnie aktualnego zbioru odchyleń. Historia wersji
pozwala wrócić do starszej.

## 2. Istniejący backend jest właścicielem

T031 używa bez zmian (zero zmian w `rota/**`):

- `open_month(conn, site_id, month)` — `rota/application/open_month.py:45`;
  odczyt profilu/obsady/reguł/bilansów + nagłówek current_version, bez treści.
- `months_with_schedule(conn, site_id)` — tamże, linia 62; miesiące z
  istniejącym grafikiem (do date-pickera).
- `get_current_schedule_snapshot(conn, site_id, month)` —
  `rota/persistence/schedule_repository.py:152`; `(header, ScheduleSnapshot)`
  albo `None` — jedyne źródło treści aktualnej wersji (demands, assignments,
  deviations). Nienazwane w żadnym dotychczasowym dokumencie UI (audyt
  `tasks/CURSOR_AUDIT_2026-08-23_backend_ui_coverage/round_01/tests/tests_r1.txt`
  finding A-1/D-4) — ten brief jest jego pierwszym właścicielem ekranu.
- `plan_month(conn, site_id, month, coordinator_id, effective_from=None)` —
  `rota/application/plan_ops.py:95`; zwraca `PlanningResult`.
- `select_candidate(conn, site_id, month, candidate, coordinator_id, note=None, responds_to_decision_required_id=None)`
  — `plan_ops.py:274`.
- `replan(conn, site_id, month, coordinator_id, effective_from, note=None, responds_to_decision_required_id=None)`
  — `plan_ops.py:340`.
- `revalidate(conn, site_id, month, coordinator_id=None)` —
  `rota/application/lifecycle_ops.py:45`.
- `finalize(conn, site_id, month, coordinator_id, acknowledged_deviation_ids, acknowledged_at=None, reason=None, responds_to_decision_required_id=None)`
  — `lifecycle_ops.py:91`.
- `restore(conn, site_id, month, coordinator_id, version_id, note=None, responds_to_decision_required_id=None)`
  — `lifecycle_ops.py:132`.
- `precheck(state)` — `rota/application/precheck.py:37`, czysta funkcja na
  `PlanningState`; API składa `assemble_planning_state(...)` +
  `precheck(...)` sam, bez nowej warstwy aplikacyjnej (ten sam wzorzec co
  `api/routers/site_profile.py` w T030).
- `materialize_deviations`/`category_for_rule` —
  `rota/application/deviation_mapping.py:40/59`; mapowanie
  `Deviation.category`/`source_reference` → polska etykieta jest zadaniem
  TEGO ekranu (audyt finding A-2: `WEEKLY-REST-01`/`REST-01` po 24h nie mają
  dotąd polskiej etykiety w żadnym dokumencie UI).
- `list_employees_by_ids(conn, ids)` —
  `rota/persistence/employee_repository.py` (już używane w `roster.py`);
  API dociąga `display_name` do `Assignment.employee_id` przy złożeniu
  odpowiedzi grid, bez nowej funkcji.

Nie wolno zmieniać `rota/**`, tworzyć drugiego solvera, walidatora ani
warstwy wersjonowania.

## 3. Referencja: realny grafik

`Grafiki/7442.jpg` — rzeczywisty "PLAN PRACY (HARMONOGRAM)" ochrony:
wiersze = pracownicy (z sumami D/N/U/C godzin), kolumny = dni miesiąca,
komórka = kod zmiany (D1-D5 dniówki, N1-N5 nocki, U1-U5 urlopy, C1-C5
chorobowe — per-pracownik numerowane, nie globalny katalog), podwójna
kolumna PLAN/WYK per dzień, podsumowanie godzin efektywnych/urlopowych/
chorobowych na końcu wiersza. Siatka ekranu ma być strukturalnie zgodna:
pracownik×dzień, komórka = kod zmiany.

Różnica względem papieru: T031 pokazuje jedną bieżącą wersję (PLAN =
`state.shift_demands`/kandydat solvera przed wyborem, WYK = zapisane
`Assignment` po `select_candidate`), nie osobne kolumny PLAN/WYK na stałe —
to networkowy stan (WORKING vs FINAL), nie dwie równoległe kolumny. Kody
D1-D5/N1-N5 z papieru to numeracja PO STRONIE ochrony (per-obiekt etat),
nie coś co istnieje w domenie `rota/` — ekran renderuje `Assignment.role`
(PRIMARY/TRAINEE) + `ShiftDemand.shift_kind` (D/N) + godziny, nie kody
papierowe.

## 4. Zamknięte decyzje formularza

1. Wybór miesiąca: trzy opcje — poprzedni/bieżący/następny (nie dowolny
   natywny `<input type="month">`); każda opcja oznaczona, czy ma już
   zapisany grafik (`getScheduleMonths`/`months_with_schedule`). Przy
   zmianie wybranego miesiąca `effective_from` (pole PLAN dla pierwszej
   wersji) resetuje się na 1. dzień nowo wybranego miesiąca.
2. Brak current_version → ekran pokazuje tylko przycisk „Zaplanuj
   (PLAN)” z wymaganym polem `effective_from` (data, domyślnie 1. dzień
   wybranego miesiąca, resynchronizowana przy zmianie miesiąca per pkt 1).
3. Jest current_version, status WORKING → siatka pokazuje zapisany stan
   (`get_current_schedule_snapshot`), plus przycisk „Przelicz (PLAN)”
   (bez `effective_from`) i po przeliczeniu — listę kandydatów do wyboru
   (`PlanningResult.candidates`, każdy render jako osobna siatka-podgląd,
   przycisk „Wybierz” = `select_candidate`).
4. Jest current_version, status FINAL_* → siatka read-only, przyciski:
   „REPLAN” (wymaga `effective_from` odcięcia), „Przywróć starszą wersję”
   (lista `list_schedule_versions` przez `open_month().version_history`).
5. `status == DECISION_REQUIRED` jest TRWAŁYM hard stopem, nie chwilowym
   stanem PlanningResult w pamięci przeglądarki: GET miesiąca dołącza
   istniejący readback `rota.application.memory_read.current_decision_required`
   (bez zmiany `rota/**`). Gdy jest aktualny, ekran pokazuje komunikat i
   ukrywa siatkę oraz WSZYSTKIE akcje (PLAN/select/REPLAN/finalize/
   restore) — stan przeżywa reload. „Decyzje koordynatora” to w
   zaakceptowanym kontrakcie T021 sam NAV ITEM bez zbudowanej treści —
   komunikat tylko wskazuje, że rozstrzygnięcie będzie dostępne na tym
   osobnym ekranie, bez linku donikąd (ten ekran NIE rozstrzyga
   DECISION_REQUIRED).
6. `status == TECHNICAL_ERROR` → komunikat z `error_message`, nic nie
   zapisane, spróbuj ponownie.
7. Finalizacja: przycisk aktywny tylko gdy user zaakceptował widoczną
   listę odchyleń (checkbox per odchylenie albo „potwierdzam wszystkie”);
   wysyła DOKŁADNIE set ID z bieżącego świeżego odczytu — jeśli backend
   odrzuci (rozjazd), UI pokazuje błąd i odświeża listę, nie zgaduje.
8. Etykiety odchyleń: mapa `source_reference` → polski tekst budowana w
   API (thin), np. `REST-01`→"odpoczynek dobowy", `WEEKLY-REST-01`→
   "odpoczynek tygodniowy (35h, OCHRONA)", `LOAD-01`→"obciążenie godzinowe",
   `COVERAGE-01`→"brak pokrycia zmiany"; nierozpoznany kod pokazuje surowy
   `source_reference` zamiast fałszywej etykiety.
9. Ręczna korekta pojedynczych przypisań — POZA zakresem (osobny ekran,
   `manual_edit.py`). Rozstrzyganie DECISION_REQUIRED — POZA zakresem
   (osobny ekran).

## 5. Dozwolony zakres plików

Produkt:
- `api/main.py`;
- nowy `api/routers/schedule.py`;
- `frontend/src/api/client.ts`, `frontend/src/screens/Room.tsx` (odblokowanie
  zakładki), `frontend/src/App.css`;
- nowy `frontend/src/screens/MonthlyPlanning.tsx`.

Testy/delivery:
- nowy `tests/test_t031_schedule_api.py`;
- nowy `frontend/e2e/monthly-planning.spec.ts`.

Brak nowych zależności. Nie modyfikować istniejących testów ani plików poza
listą. Jeżeli implementacja wymaga szerszego zakresu, zgłosić blocker
zamiast tworzyć connector lub nową warstwę.

## 6. Minimalna macierz odbioru

T31-01 — GET otwarcia miesiąca (bez current_version): zwraca
`current_version=null`, puste `demands`/`assignments`/`deviations`,
`version_history=[]`, `decision_required=null`, `warnings`. Miesiące z
zapisanym grafikiem to OSOBNY odczyt (`GET .../schedule/months`, R1-1) —
GET pojedynczego miesiąca nie zwraca profilu/obsady/reguł/bilansów, front
ich tu nie potrzebuje.

T31-02 — POST plan (bez current_version, effective_from wymagane): tworzy
pierwszą wersję, zwraca `PlanningResult`; brak `effective_from` → 422/400
bez zapisu.

T31-03 — GET otwarcia miesiąca (jest current_version, WORKING): zwraca
current_version + pełną treść (`get_current_schedule_snapshot`).

T31-04 — POST plan (przeliczenie istniejącej WORKING): zwraca nowych
kandydatów, nie tworzy drugiej wersji.

T31-05 — POST select-candidate: zapisuje wybraną listę Assignment na
current WORKING; kandydat niezgodny z walidacją → 400, nic nie zapisane.

T31-06 — POST replan: tworzy dziecko, `effective_from` wymagane;
przypisania sprzed cutover niezmienione (backend już to gwarantuje —
test tylko na poziomie API, nie duplikuje solvera).

T31-07 — POST finalize: wymaga DOKŁADNIE bieżącego zbioru odchyleń;
częściowy/rozjechany set → 400 bez zapisu; poprawny → status FINAL_*.

T31-08 — POST restore: przesuwa current_version na starszą wersję z
historii, nic nie usuwa.

T31-09 — Etykiety odchyleń: `WEEKLY-REST-01`/`REST-01`/`LOAD-01`/
`COVERAGE-01` mają polski tekst w odpowiedzi API; nieznany kod nie
crashuje, zwraca surowy kod.

T31-10 — E2E: otwarcie pustego miesiąca → PLAN → wybór kandydata → siatka
pokazuje zapisany stan po reload; REPLAN po dacie odcięcia; finalize
wymaga potwierdzenia dokładnego zbioru odchyleń.

T31-11 — build frontendu, pełna regresja Pythona, diff-scope z §5, zero
zmian w `rota/**`.

## 7. Ustalenia z implementacji (E2E)

Dwa fakty odkryte podczas pisania `frontend/e2e/monthly-planning.spec.ts`,
nieprzewidziane w §2/§4 — obie poprawki mieszczą się w istniejącym §5
(zero zmian poza deklarowanym zakresem plików):

1. **Kalendarz jest twardym warunkiem wstępnym PLAN.**
   `assemble_planning_state` (`rota/application/assembler.py::_assemble_calendar`)
   wymaga rekordu `CalendarDay` dla KAŻDEGO dnia docelowego miesiąca —
   `plan_month`/`replan` rzucają `IncompleteCalendarData` bez tego. Jedyna
   dziś istniejąca ścieżka wypełnienia to modal „Kalendarz” w
   `frontend/src/screens/Workspace.tsx` (przycisk „Wygeneruj kalendarz na
   miesiąc”), poza deklarowanym zakresem plików T031 — nie modyfikowany.
   `CalendarDay` jest globalny (nie per-obiekt), więc wygenerowanie
   kalendarza dla dowolnego obiektu wystarcza dla wszystkich. E2E seeduje
   to jawnie przed każdym PLAN. Ekran „Planowanie miesiąca” sam z siebie
   NIE prowadzi koordynatora do kalendarza — samo pokazuje surowy błąd
   backendu, jeśli brakuje dni. To świadomie zostawione poza T031: naprawa
   UX (link/CTA do kalendarza z tego ekranu) to osobna, mała poprawka do
   rozważenia w kolejnym zadaniu, nie blocker.
2. **Bug znaleziony i naprawiony**: przycisk „Finalizuj” był błędnie
   ukryty, gdy `assignments.length === 0` — ale pusty (zero-osobowy)
   miesiąc jest prawidłowo finalizowalny (brak przypisań = brak odchyleń =
   pusty zbiór do potwierdzenia). Warunek zawężony do samego `!isFinal`
   (`frontend/src/screens/MonthlyPlanning.tsx`), złapane przez E2E
   T31-10, nie przez testy API.

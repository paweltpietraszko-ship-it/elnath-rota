# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC

Każda nowa instancja Architekta przed podjęciem Tasku musi przeczytać w całości
`ARCHITECT_START_HERE.md`. Każda nowa instancja Codexa postępuje zgodnie z
`AGENTS.md` i `CODEX_START_HERE.md`.

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalzem pracy; ten plik tylko rejestruje
przekazanie, żeby nie trzeba było ręcznie przeklejać wiadomości między CC a
Codexem.

Statusy (dokładnie cztery, nic więcej):

- `READY_FOR_CODEX` — CC skończył, czeka na audyt.
- `CODEX_IN_PROGRESS` — Codex audytuje.
- `CODEX_REPORTED` — raport gotowy pod wskazaną ścieżką.
- `OWNER_DECISION_NEEDED` — audyt utknął na decyzji właściciela.

Nowy wiersz dopisuje autor przekazania; zmianę statusu na kolejny etap
wpisuje ten, kto ten etap kończy. Zamknięty wiersz (merge/decyzja, ostatni
status rozstrzygnięty) usuwa z tego pliku ten, kto go zamyka — pełna
historia i tak zostaje w `git log -p BOARD.md`, więc nic nie ginie, tylko
plik nie rośnie w nieskończoność (2026-08-29, OWNER_CORRECTED: wcześniejsza
wersja tej reguły mówiła "nie kasować wierszy" — celowo zmienione).

| ID | Autor | Odbiorca | Branch | Exact SHA | Status | Wiadomość |
|---|---|---|---|---|---|---|
| ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID | CC | Codex | `task/ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID` | impl `c7e047a` (base precheck `c12b840` of brief `64ce44e`, base_main `c4fad96`) | READY_FOR_CODEX | **Implementacja gotowa do realnego audytu IMPLEMENTATION (dotąd tylko PASS PREIMPLEMENTATION R2 na samym briefie).** `api/routers/schedule.py`: nowe DTO `ScheduleEmployeeOut`/`DelegationDayOut`, pola `employees`/`delegation_days` w `PlanPreviewOut`/`PlanningResultOut`/`MonthViewOut`, projekcja licząca się z aktywnych LOCAL memberships + Assignmentów + bieżących aktywnych DELEGACJA (przez istniejące `delegation_records_for_employees`/`delegation_hours_in_range`, bez nowej persystencji). `frontend/src/screens/MonthlyPlanning.tsx::ScheduleGrid`: wiersze z `employees` zamiast wyłącznie z Assignmentów, DEL renderowany tylko gdy komórka bez Assignmentu (DG-07), suma godzin liczy oba fakty. `frontend/src/api/client.ts` zaktualizowany. Testy: nowy `tests/test_delegation_schedule_grid.py` (DG-01..DG-09 + regresja, 9/9 PASS), dopisanie w `tests/test_t031_schedule_api.py`, nowy `frontend/e2e/delegation-schedule-grid.spec.ts` (2/2 PASS na realnym buildzie). `npx tsc --noEmit` czyste. CC-side merit: zgodne z briefem, WHERE_MAP-owe funkcje (`_plan_preview_out`, `_planning_result_out`, `get_month`, `ScheduleGrid`) są jedynymi zmienionymi call site'ami; brak zmian solvera/walidatora/persystencji ScheduleVersion. Live click-through weryfikacja (czy siatka faktycznie sensownie wygląda dla koordynatora) świadomie odłożona — właściciel zrobi ją przy swoim komputerze, nie jest częścią tego audytu. |
| ROTA-HISTORIA-OGRANICZEN-DISPLAY | CC | Codex | `task/ROTA-HISTORIA-OGRANICZEN-DISPLAY` (zmergowany) | impl `8676d07`, merge `5830a50` (base `main@21396b7`) | CODEX_REPORTED | **Codex PASS na exact `8676d07`; merge `5830a50` zawiera poprawkę. Punktowy diff, `tsc -b` i live retest właściciela potwierdzają zamknięcie błędu. Raport: `tasks/ROTA-HISTORIA-OGRANICZEN-DISPLAY/round_01/tests/tests_r1.txt`, commit `aef6702`.** **Żywy bug na obiekcie FF (Anna): `RestrictionList` w `EmployeeDetail.tsx` renderował KAŻDĄ zwróconą komórkę macierzy z surowym `effective_from`/`effective_to` (to drugie zawsze `null` = "bez końca" — `end_employee_matrix_rule_early` nigdy nie dotyka tej kolumny, tylko realnego `applies_from`/`applies_to`), więc już zakończone ograniczenia (potwierdzone bezpośrednio: wszystkie 7 reguł tygodniowych Anny już zakończonych w bazie) pokazywały się jako wciąż aktywne, z pozornie działającym przyciskiem "Zakończ", który zawsze rzucał `ValueError: rule family '...' has already ended`, surfaced jako ogólny "Nieprawidłowe dane wejściowe".** Naprawa: filtr `cells` po `applies_to` (już liczonym przez backend, już używanym gdzie indziej w tym samym pliku przez `isActiveToday`) zamiast po surowym `effective_to`; wyświetlane daty też przełączone na `applies_from`/`applies_to`. Zero zmian backendu/kontraktu — czysto frontendowy filtr istniejącego już pola. Zweryfikowane: `npx tsc -b` czyste, live retest przez właściciela potwierdzony (panel już nie pokazuje zakończonych ograniczeń). |

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
| ROTA-ARCHITECT-START-HERE-MISSING-CC-MERIT-GATE | Codex | CC | — (korekta instrukcji workflow) | `ARCHITECT_START_HERE.md` sekcja 4; fix `26b17da` | CODEX_REPORTED | **UWAGA CC UWZGLĘDNIONA.** Workflow zawiera teraz osobną bramę merytoryczną CC po prechecku Codexa i przed implementacją. CC ocenia sens, zakres i ryzyko nieprzemyślanej logiki oraz może odesłać brief do korekty mimo PASS Codexa. Dopiero po przejściu obu bram CC implementuje literalny `TASK_SCOPE`; nie daje mu to prawa do audytu ani zatwierdzania własnej implementacji. |
| ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE | Architekt | Codex | `task/ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE` | brief `8176f50` (base `main@c4fad96`) | READY_FOR_CODEX | **CC PASS MERYTORYCZNY.** Brief poprawnie odzwierciedla decyzję właściciela (twardy gate na `target_hours` przed PLAN/REPLAN + propozycja "ustaw wszystkim" po pierwszym wpisie) i poprawnie rozszerza jego własną, wcześniej wypowiedzianą zasadę ("urlop + wypracowane = cel") na DELEGACJĘ: `_effective_targets` odejmuje też `delegation_hours_in_range` z aktywnych rekordów `state.availability_records`. Zweryfikowane bezpośrednio w kodzie: `_effective_targets` (solver.py:489), `target_vector_complete`/`add_equal_split_fairness` (linie 1003-1013), `delegation_hours_in_range` (absence.py:296) — wszystkie cytowane sygnatury i linie się zgadzają, brief czytał realny kod. Usunięcie martwego fallbacku po gate jest bezpieczne (fairness_employee_ids i tak zawsze = target_by_employee.keys() po wymuszonym komplecie celów). Solver/FEASIBLE-boundary — pełny proces wymagany, implementacja czeka na `PASS PREIMPLEMENTATION` Codexa. **Uwaga sekwencjonowania (nieblokująca):** dzieli 3 pliki TASK_SCOPE (`api/routers/schedule.py`, `frontend/src/api/client.ts`, `frontend/src/screens/MonthlyPlanning.tsx`) z `ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID` — właściciel zdecyduje kolejność implementacji, żeby uniknąć konfliktu mergowania. |
| ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID | Architekt | Codex | `task/ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID` | brief `8b9c748` (base `main@c4fad96`) | READY_FOR_CODEX | **CC PASS MERYTORYCZNY.** Brief realizuje decyzję właściciela (etykieta "DEL", nie pusty wiersz) czysto prezentacyjnie — bez sztucznego Assignmentu/demandu, bez kopii DEL w snapshotach ScheduleVersion/PlanPreview, poprawnie zachowuje istniejącą precedencję ręcznej korekty na dzień DELEGACJI (DG-07, zgodne z zamrożoną decyzją R2 z `ROTA-DELEGACJA-ABSENCE-KIND`). Zweryfikowane bezpośrednio: `PlanPreviewOut`/`MonthViewOut`/`PlanningResultOut`/`_plan_preview_out`/`_planning_result_out`/`get_month` (schedule.py, linie zgodne z cytowanymi) i `delegation_records_for_employees` (work_balance_repository.py:92) — wszystkie istnieją dokładnie tak, jak brief je opisuje. Poprawnie NIE dokłada etykiet Urlop/L4 do siatki (zgodne z wcześniejszą decyzją "wąski brief"). **Uwaga sekwencjonowania (nieblokująca):** patrz wpis `ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE` powyżej — te same 3 pliki TASK_SCOPE, właściciel decyduje kolejność. |
| ROTA-HISTORIA-OGRANICZEN-DISPLAY | CC | Codex | `task/ROTA-HISTORIA-OGRANICZEN-DISPLAY` (zmergowany) | impl `8676d07`, merge `5830a50` (base `main@21396b7`, brak briefu — jednolinijkowa poprawka wyświetlania, zmergowana na wyraźne polecenie właściciela przed audytem, retroaktywny audyt teraz) | READY_FOR_CODEX | **Żywy bug na obiekcie FF (Anna): `RestrictionList` w `EmployeeDetail.tsx` renderował KAŻDĄ zwróconą komórkę macierzy z surowym `effective_from`/`effective_to` (to drugie zawsze `null` = "bez końca" — `end_employee_matrix_rule_early` nigdy nie dotyka tej kolumny, tylko realnego `applies_from`/`applies_to`), więc już zakończone ograniczenia (potwierdzone bezpośrednio: wszystkie 7 reguł tygodniowych Anny już zakończonych w bazie) pokazywały się jako wciąż aktywne, z pozornie działającym przyciskiem "Zakończ", który zawsze rzucał `ValueError: rule family '...' has already ended`, surfaced jako ogólny "Nieprawidłowe dane wejściowe".** Naprawa: filtr `cells` po `applies_to` (już liczonym przez backend, już używanym gdzie indziej w tym samym pliku przez `isActiveToday`) zamiast po surowym `effective_to`; wyświetlane daty też przełączone na `applies_from`/`applies_to`. Zero zmian backendu/kontraktu — czysto frontendowy filtr istniejącego już pola. Zweryfikowane: `npx tsc -b` czyste, live retest przez właściciela potwierdzony (panel już nie pokazuje zakończonych ograniczeń). |

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
| ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE | CC | Codex | `task/ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE` | impl `cdf389c` (base `c4fad96`) | CODEX_REPORTED | **Codex FAIL na `cdf389c`: zapisany wcześniej `plan_preview` po odpowiedzi `TARGET_HOURS_REQUIRED` ponownie ustawia ekran na `FEASIBLE` i ukrywa blocker z listą osób. Raport: `tasks/ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE/round_01/tests/tests_r3.txt`, commit `4d243f7`.** **TASK_SCOPE gap (141 regresje w 21 plikach spoza briefu) zamknięty na wyraźne polecenie właściciela po przejrzeniu findingu.** Rdzeń briefu: `require_complete_target_hours` w `plan_ops.py` (PLAN/REPLAN/retry/wider-search/precheck), `_effective_targets` odejmuje aktywną DELEGACJĘ, fallback + `_available_local_employee_ids` usunięte z `solver.py`/`fairness.py`, `apply-to-all` endpoint + propozycja w `EmployeeDetail.tsx`, blocker w `MonthlyPlanning.tsx`. Mechaniczna poprawka 21 plików spoza TASK_SCOPE: dopisany `target_hours` do ich PLAN/REPLAN-wywołujących fixture'ów (głównie przez nowy opcjonalny parametr `seed_real_object(..., target_hours=...)`, domyślnie `None` — nie zmienia `test_t009_open_and_assembler.py`'s własnego testu na pustym stanie). `test_t041_checkpoint_a.py`: A01/A02/A04/A05 (testy nieistniejącego już fallbacku) usunięte zgodnie z instrukcją briefu "zastąpić testami gate", A03 zostaje. Nowy `tests/test_target_hours_required.py`: TH-01..TH-10. Zweryfikowane bezpośrednio, dwukrotnie: pełny `pytest tests/ --ignore=tests/property` = dokładnie 43 pre-existing failures (te same co na czystym `main@4c1ed60`), **0 nowych regresji** (dokładny diff test-ID, nie zgadywane). `npx tsc -b` i ruff czyste na wszystkich zmienionych plikach. Gotowe do PASS PREIMPLEMENTATION Codexa dla rozszerzonego TASK_SCOPE (produkcja bez zmian od R2; zmiana dotyczy wyłącznie testów). |
| ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID | Codex | Architekt/CC | `task/ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID` | precheck `c12b840` of corrected brief `64ce44e` (base `c4fad96`) | CODEX_REPORTED | **PASS PREIMPLEMENTATION R2.** Jedyny brak R1 został zamknięty: `WHERE_MAP: REQUIRED` obejmuje `_plan_preview_out`, `_planning_result_out`, `get_month` i `ScheduleGrid`, bez rozszerzenia zachowania ani TASK_SCOPE. Brief jest jednoznaczny i może być implementowany bez nowej decyzji produktowej. Raport: `tasks/ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID/round_01/tests/tests_r2.txt`. Bez testów, where.py i audytu diffu produktu. |
| ROTA-HISTORIA-OGRANICZEN-DISPLAY | CC | Codex | `task/ROTA-HISTORIA-OGRANICZEN-DISPLAY` (zmergowany) | impl `8676d07`, merge `5830a50` (base `main@21396b7`, brak briefu — jednolinijkowa poprawka wyświetlania, zmergowana na wyraźne polecenie właściciela przed audytem, retroaktywny audyt teraz) | READY_FOR_CODEX | **Żywy bug na obiekcie FF (Anna): `RestrictionList` w `EmployeeDetail.tsx` renderował KAŻDĄ zwróconą komórkę macierzy z surowym `effective_from`/`effective_to` (to drugie zawsze `null` = "bez końca" — `end_employee_matrix_rule_early` nigdy nie dotyka tej kolumny, tylko realnego `applies_from`/`applies_to`), więc już zakończone ograniczenia (potwierdzone bezpośrednio: wszystkie 7 reguł tygodniowych Anny już zakończonych w bazie) pokazywały się jako wciąż aktywne, z pozornie działającym przyciskiem "Zakończ", który zawsze rzucał `ValueError: rule family '...' has already ended`, surfaced jako ogólny "Nieprawidłowe dane wejściowe".** Naprawa: filtr `cells` po `applies_to` (już liczonym przez backend, już używanym gdzie indziej w tym samym pliku przez `isActiveToday`) zamiast po surowym `effective_to`; wyświetlane daty też przełączone na `applies_from`/`applies_to`. Zero zmian backendu/kontraktu — czysto frontendowy filtr istniejącego już pola. Zweryfikowane: `npx tsc -b` czyste, live retest przez właściciela potwierdzony (panel już nie pokazuje zakończonych ograniczeń). |

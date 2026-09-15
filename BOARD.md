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
| ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE | CC | Codex | `task/ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE` | impl `35b5bf3` (base `c4fad96`, fix na `cdf389c`) | CODEX_REPORTED | **Codex PASS na `35b5bf3`. R3-01 zamknięty: pierwotny reproduktor Chromium oraz `tsc -b` przeszły. Raport: `tasks/ROTA-EQUAL-SPLIT-FALLBACK-IGNORES-ABSENCE/round_01/tests/tests_r4.txt`, commit `5306369`.** **R3-01 FIX.** Root cause potwierdzony dokładnie jak w raporcie Codexa (`tests_r3.txt`, commit `4d243f7`) — nie regime-specific (OCHRONA/ORDINARY dzielą ten sam kod, sprawdzone bezpośrednio): `loadUnlessFreshPreviewUnpersisted` (MonthlyPlanning.tsx) wołało `load()` po każdej odpowiedzi PLAN/REPLAN oprócz jednego wyjątku (FEASIBLE-not-persisted); `TARGET_HOURS_REQUIRED` też nie dotyka wersji/podglądu, więc `load()` odświeżał `view` i istniejący `useEffect` (linia ~211, kluczowany na `view.plan_preview`) bezwarunkowo nadpisywał świeżo ustawiony `planResult` starym FEASIBLE z zapisanego podglądu. Fix: `loadUnlessFreshPreviewUnpersisted` pomija `load()` też dla `TARGET_HOURS_REQUIRED`, tym samym uzasadnieniem co istniejący wyjątek ("nic nowego do przeładowania"). `npx tsc -b` czyste. **Pozostaje otwarte:** `frontend/e2e/target-hours-required.spec.ts` (nowy plik z TASK_SCOPE) jeszcze nie napisany — brak gotowego helpera do dodawania roster przez UI w `frontend/e2e/helpers.ts`, nie chciałem pisać czegoś na szybko bez sprawdzenia selektorów. Reszta implementacji bez zmian od poprzedniego wpisu (rdzeń brief + mechaniczna poprawka 21 plików fixture, 0 nowych regresji w pytest, zweryfikowane wcześniej). |
| ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID | Codex | Architekt/CC | `task/ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID` | precheck `c12b840` of corrected brief `64ce44e` (base `c4fad96`) | CODEX_REPORTED | **PASS PREIMPLEMENTATION R2.** Jedyny brak R1 został zamknięty: `WHERE_MAP: REQUIRED` obejmuje `_plan_preview_out`, `_planning_result_out`, `get_month` i `ScheduleGrid`, bez rozszerzenia zachowania ani TASK_SCOPE. Brief jest jednoznaczny i może być implementowany bez nowej decyzji produktowej. Raport: `tasks/ROTA-DELEGACJA-ONLY-EMPLOYEE-MISSING-FROM-SCHEDULE-GRID/round_01/tests/tests_r2.txt`. Bez testów, where.py i audytu diffu produktu. |
| ROTA-HISTORIA-OGRANICZEN-DISPLAY | CC | Codex | `task/ROTA-HISTORIA-OGRANICZEN-DISPLAY` (zmergowany) | impl `8676d07`, merge `5830a50` (base `main@21396b7`, brak briefu — jednolinijkowa poprawka wyświetlania, zmergowana na wyraźne polecenie właściciela przed audytem, retroaktywny audyt teraz) | READY_FOR_CODEX | **Żywy bug na obiekcie FF (Anna): `RestrictionList` w `EmployeeDetail.tsx` renderował KAŻDĄ zwróconą komórkę macierzy z surowym `effective_from`/`effective_to` (to drugie zawsze `null` = "bez końca" — `end_employee_matrix_rule_early` nigdy nie dotyka tej kolumny, tylko realnego `applies_from`/`applies_to`), więc już zakończone ograniczenia (potwierdzone bezpośrednio: wszystkie 7 reguł tygodniowych Anny już zakończonych w bazie) pokazywały się jako wciąż aktywne, z pozornie działającym przyciskiem "Zakończ", który zawsze rzucał `ValueError: rule family '...' has already ended`, surfaced jako ogólny "Nieprawidłowe dane wejściowe".** Naprawa: filtr `cells` po `applies_to` (już liczonym przez backend, już używanym gdzie indziej w tym samym pliku przez `isActiveToday`) zamiast po surowym `effective_to`; wyświetlane daty też przełączone na `applies_from`/`applies_to`. Zero zmian backendu/kontraktu — czysto frontendowy filtr istniejącego już pola. Zweryfikowane: `npx tsc -b` czyste, live retest przez właściciela potwierdzony (panel już nie pokazuje zakończonych ograniczeń). |

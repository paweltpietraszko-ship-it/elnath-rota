# BOARD.md — kolejka przekazań CC ↔ Codex

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
| ROTA-T052 | CC | Codex | `task/ROTA-T052-s1-periodic-training-contract` | `be518f9` | READY_FOR_CODEX | Oba R4 findingi poprawione i zweryfikowane (patrz historia BOARD.md dla szczegółów naprawy w `constraints.py`/`schedule_export.py`). `backend.py` (`tasks/ROTA-T052/round_01/tests/backend_output_r4.txt`) `DIFF_SCOPE` czysty po dopisaniu `constraints.py` do `EXACT TASK_SCOPE`. OWNER 2026-09-04 zaakceptował wszystkie pozostałe `SIZE_FILE`/`SIZE_FUNC`/`RATIO`/`TOTAL_LINES` (`RATIO 503/44=11.4:1`, `TOTAL_LINES 547`) -- `constraints.py` 618->649 (pre-istniejący overage, kontynuacja) i nietknięta przeze mnie `add_max_two_consecutive_night_constraints` (61 linii) odsłonięte dopiero po dodaniu pliku do zakresu. Flaga do Codexa: `TEST_ID: test_solver_does_not_hard_block_a_shift_around_s1 — suspected false positive: asserts literal status_name "FEASIBLE", real CP-SAT success on a trivial model also returns "OPTIMAL"` (solver realnie rozwiązuje, tylko literalny string statusu się różni). Proszę o reaudyt. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

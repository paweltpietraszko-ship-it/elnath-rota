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
| ROTA-T052 | CC | Architect | `task/ROTA-T052-s1-periodic-training-contract` | `6d057df` | OWNER_DECISION_NEEDED | Oba R4 findingi poprawione, OWNER 2026-09-04 zgodę na `constraints.py` dał wprost. (1) `rota/planning/constraints.py`: `build_fixed_periods()` teraz zwraca też id komponentów S1; nowy `_rest_conflict()` w `_add_ordinary_fixed_edges`/`_add_merged_pair_edges` nadal blokuje realny overlap z S1, ale nigdy wymóg przerwy; solver.py wyklucza S1 z WEEKLY-REST-01 fixed-occupancy. Reproduktor Codexa: solver realnie znajduje rozwiązanie (poprzednio INFEASIBLE) -- 2 z 4 jego testów nadal "FAIL" tylko dlatego, że assertują dosłowne `"FEASIBLE"`, a solver na trywialnym modelu zwraca `"OPTIMAL"` (oba są sukcesem, używane zamiennie wszędzie indziej w kodzie) -- `TEST_ID: test_solver_does_not_hard_block_a_shift_around_s1 — suspected false positive: asserts literal status_name "FEASIBLE", real CP-SAT success on a trivial model also returns "OPTIMAL"`. Zweryfikowałem 306/308 istniejących testów solvera/REST-01 (`test_t012/t013/t017/t022/t023b/t032/t033/t036`, replan/reg_001) -- 2 FAIL potwierdzone jako identyczne na commicie SPRZED tej poprawki (`8fc022c`), pre-istniejący tie-break flake, zero regresji. (2) `schedule_export.py`: S1 dzielące dzień z inną zmianą bez realnego nakładania łączy się teraz w jedną komórkę ("N1/S1") zamiast wywalać cały PDF; realny overlap nadal blokuje. `backend.py` (`tasks/ROTA-T052/round_01/tests/backend_output_r3.txt`): jedyny mechaniczny blocker to `DIFF_SCOPE` na `rota/planning/constraints.py` -- proszę dopisać do `EXACT TASK_SCOPE`. Nowe drobne przekroczenia do akceptacji OWNERA: `solver.py` 1025->1033, `schedule_export.py` 654->684 (+`_apply_24h_periods` SIZE_FUNC 53 linii, 3 nad limitem), `RATIO 459/31=14.8:1`, `TOTAL_LINES 490`. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

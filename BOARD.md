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
| ROTA-T052 | CC | Codex | `task/ROTA-T052-s1-periodic-training-contract` | `baed8f8` | READY_FOR_CODEX | R5-01 naprawione: `validator._check_rest` i `constraints.py`'s `build_fixed_periods`/`_rest_conflict` teraz kluczują na `(schedule_version_id, assignment_id)` i porównują `component_keys`, nigdy `component_ids`. Reproduktor Codexa: 10/10 PASS. `backend.py` (`tasks/ROTA-T052/round_01/tests/backend_output_r5.txt`) `DIFF_SCOPE` czysty. OWNER 2026-09-04 zaakceptował przyrost `SIZE_FILE` (`validator.py` 767->770, `constraints.py` 649->657 -- kontynuacje już zaakceptowanych overage'ów) oraz `RATIO 514/44=11.7:1`, `TOTAL_LINES 558`. Zweryfikowałem szerszy zestaw testów solvera/REST-01 -- 4 FAIL, wszystkie potwierdzone identyczne na `main@f93685f` sprzed T052 (`NARROW_SEARCH_EXHAUSTED`/tie-break flaki), zero regresji z tej poprawki. Proszę o reaudyt. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

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
| ROTA-T052 | CC | Architect | `task/ROTA-T052-s1-periodic-training-contract` | (implementacja w toku) | OWNER_DECISION_NEEDED | Implementacja (domain.py, schedule_validation.py, balance.py, validator.py, manual_edit.py, site_repository.py, db.py migracja 11, api/routers/export.py, frontend) zrobiona, w EXACT TASK_SCOPE. Dwa otwarte punkty: (1) jak poprzednio -- `rota/planning/constraints.py` (CP-SAT REST-01/WEEKLY-REST-01 builder) NIE jest w TASK_SCOPE, ale bez zmiany tam solver może realnie ODRZUCIĆ poprawny kandydat blisko S1 (T52-05/T52-06), bo CP-SAT nie zna wyjątku już wpisanego do independent validatora -- proszę o decyzję: dodać ten plik do zakresu, czy inne rozwiązanie. (2) `pytest` na istniejącej suite: 234 passed, 4 failed -- 3 to `tests/test_t012.py`/`test_t020.py`/`test_t023b.py` z zaszytym na sztywno `LATEST_SCHEMA_VERSION == 10`, nieuniknioną konsekwencją migracji 11 (potwierdzone: identycznie wysypią się przy każdej nowej migracji); 1 to `test_t009_manual_edit.py::test_12_freeze_affects_later_replan`, potwierdzony jako pre-istniejący flake solvera identyczny na `main@7cd5fde` sprzed T052 (`NARROW_SEARCH_EXHAUSTED` zamiast `FEASIBLE`), zero związku z tą zmianą. Proszę dopisać te 3 pliki testowe do EXACT TASK_SCOPE albo wskazać, kto je poprawi. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

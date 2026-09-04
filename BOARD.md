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
| ROTA-T052 | CC | Architect | `task/ROTA-T052-s1-periodic-training-contract` | (implementacja w toku) | OWNER_DECISION_NEEDED | Podczas implementacji znaleziony realny brak w TASK_SCOPE: `rota/planning/constraints.py` (CP-SAT REST-01/WEEKLY-REST-01 builder) NIE jest w zakresie, ale `fixed_existing_assignments()` w `rota/planning/solver.py` już dziś automatycznie traktuje S1 jako fixed (bo `role != PRIMARY`, dokładnie jak TRAINEE) i przekazuje je do `constraints.build_fixed_periods()`, który buduje realny CP-SAT `WorkPeriod` z S1 i egzekwuje wobec niego REST-01 11h / WEEKLY-REST-01 35h -- dokładnie to, czego brief §2 pkt 4 zabrania. Bez zmiany w `constraints.py` solver może realnie ODRZUCIĆ (INFEASIBLE/DECISION_REQUIRED) poprawny kandydat, który T52-05/T52-06 wymagają jako dopuszczalny -- to nie jest tylko kwestia independent validatora (już poprawionego w `validator.py`/`manual_edit.py`), tylko realnej wykonalności PLAN/REPLAN. Proszę o decyzję: rozszerzyć TASK_SCOPE o `rota/planning/constraints.py`, czy inne rozwiązanie. Reszta implementacji (domain.py, schedule_validation.py, validator.py, manual_edit.py) trwa równolegle. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

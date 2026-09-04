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
| ROTA-T052 | Codex | CC | `task/ROTA-T052-s1-periodic-training-contract` | audited `be518f9d8376d87b6dd33e4d35ab07c3e7643c9d`; report commit `96b86af` | CODEX_REPORTED | **FAIL**. Oba findingi R4 są naprawione; poprawiłem też własny fałszywy oracle `FEASIBLE` tak, by akceptował prawidłowe `OPTIMAL`. Nowy blocker R5-01: wyjątek S1 używa bare `assignment_id`, choć tożsamość jest `(schedule_version_id, assignment_id)`. S1 pracownika E2 może przez zbieżność ID wyłączyć REST-01 dla zwykłego PRIMARY pracownika E1 na innym obiekcie: validator daje błędny SOFT zamiast HARD, solver przydziela zmianę. Wąski reaudyt: 8 pass / 2 fail; frontend build PASS; bez pełnej regresji. Raport: `tasks/ROTA-T052/round_01/tests/tests_r5.txt`. Reproducer: `test_t052_r4_audit.py`. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

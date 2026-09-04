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
| ROTA-T052 | CC | Architect | `task/ROTA-T052-s1-periodic-training-contract` | `7c2ac5d` | OWNER_DECISION_NEEDED | Status po OWNER decyzjach 2026-09-04: (1) `constraints.py` -- OWNER zamyka, solver zostaje nietknięty (S1 jest ręcznym faktem, nie decyzją solvera; ewentualna nadmierna ostrożność solvera nie jest łamaniem prawa). (2) 3 testy ze sztywnym `LATEST_SCHEMA_VERSION` -- naprawione przez CC na bezpośrednią autoryzację OWNERA (`tests/test_t012.py`/`test_t020.py`/`test_t023b.py`, 10->11), zweryfikowane PASS. (3) widoczność SOFT warningu -- wydzielona do osobnego findingu dla architekta (`arch/FINDING_2026-09-04_VALIDATOR_WARNINGS_NEVER_SURFACED.md`, main@a5a4960), nie część T052. `backend.py` (`tasks/ROTA-T052/round_01/tests/backend_output_r1.txt`, before_sha=merge-base f93685f, nie stary BASE_MAIN_SHA z brief.md -- main ma już zmergowane T053): `DIFF_SCOPE` FAIL tylko na tych 3 testach (proszę dopisać do EXACT TASK_SCOPE). `WYMAGA_DECYZJI`: `RATIO 414/24=17.2:1`, `TOTAL_LINES 438`. `SIZE_FILE`/`SIZE_FUNC`: `solver.py` 1025 linii -- nietknięty przeze mnie, już tak wygląda w bazie przed T052, nieistotne dla tego tasku; `validator.py` 712->767 (już był nad limitem przed T052, `_check_rest` też, 51->78 linii -- rósł przez SOFT-warning logikę); `schedule_export.py` 627->654 (też już nad limitem przed T052); `db.py` 590->604 -- to jedyny NOWY overage, 4 linie nad limitem, migracja 11. Proszę o akceptację tych overage'ów (3 kontynuacje istniejących, 1 nowy o 4 linie) oraz RATIO/TOTAL_LINES. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

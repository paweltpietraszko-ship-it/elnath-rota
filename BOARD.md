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
| ROTA-T052 | CC | Architect | `task/ROTA-T052-s1-periodic-training-contract` | `7c2ac5d` | OWNER_DECISION_NEEDED | OWNER 2026-09-04 zaakceptował wszystkie `WYMAGA_DECYZJI`/`SIZE_FILE`/`SIZE_FUNC` z `backend.py` (`tasks/ROTA-T052/round_01/tests/backend_output_r1.txt`): `RATIO 414/24=17.2:1`, `TOTAL_LINES 438`, `solver.py`/`validator.py`/`schedule_export.py` overage (kontynuacje sprzed T052) i `db.py` 590->604 (nowy, 4 linie, migracja 11). Jedyny pozostały mechaniczny blocker: `DIFF_SCOPE` na `tests/test_t012.py`/`test_t020.py`/`test_t023b.py` (naprawione przez CC na OWNER-autoryzację, treść już PASS) -- proszę dopisać te 3 ścieżki do `EXACT TASK_SCOPE` w `tasks/ROTA-T052/brief.md`, dokładnie jak przy T053's e2e. Po tym T052 jest READY_FOR_CODEX. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

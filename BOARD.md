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
| ROTA-T052 | CC | Codex | `task/ROTA-T052-s1-periodic-training-contract` | `8fc022c` | READY_FOR_CODEX | `backend.py` `DIFF_SCOPE` czysty (`tasks/ROTA-T052/round_01/tests/backend_output_r2.txt`). OWNER 2026-09-04 zaakceptował wszystkie `SIZE_FILE`/`SIZE_FUNC`/`RATIO`/`TOTAL_LINES`: `solver.py` (1025 linii, nietknięty przeze mnie), `validator.py` (712->767, `_check_rest` 51->78), `schedule_export.py` (627->654) -- kontynuacje sprzed T052; `db.py` 590->604 (nowy, migracja 11); `test_t012.py`/`test_t020.py` (1735/773 linii, pre-istniejące, odsłonięte dopiero po dodaniu do zakresu, treściowo bez zmian poza 10->11); `RATIO 417/27=15.4:1`, `TOTAL_LINES 444`. Implementacja: nowa rola `AssignmentRole.PERIODIC_TRAINING` (S1) -- liczy się do overlap/LOAD-01/WorkBalance, wyłączona z coverage/mentor/readiness, HARD-zwolniona z REST-01/WEEKLY-REST-01 ale z OWNER-korektą 2026-09-04 daje SOFT warning przy realnym naruszeniu 11h/35h zamiast ciszy; ręczny dodaj/usuń S1 w MonthlyPlanning, konfiguracja domyślnego przedziału w PrintSettings, wydruk pokazuje "S1" z własną legendą. Proszę o audyt implementacji. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

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
| ROTA-T056 | Codex | CC | `task/ROTA-T056` | brief `404580b354648818f61b2de12ea1c4113d08f3f9` | CODEX_REPORTED | **PASS — READY_FOR_IMPLEMENTATION.** Wąski wyjątek `_validate_item` jest związany równocześnie z właściwym site/month/family/date oraz exact start_time/end_time/end_next_day; wszystkie pozostałe rozbieżności pozostają fail-closed. Solver, demand generation, ShiftDemand semantics i `operational_code` są jawnie nietknięte. TASK_SCOPE ma 19 ścieżek, size baseline dokładnie 6/6, WHERE_MAP potwierdza istniejącego ownera. Raport: `tasks/ROTA-T056/round_01/tests/tests_r7.txt`. Przed finalnym delivery przenieść reproduktor R6 do `tests/test_t056.py` i usunąć standalone reproduktor/output z diffu. Końcowy audyt nadal wymaga rzeczywistego pionu oraz optycznej oceny obu PDF. |

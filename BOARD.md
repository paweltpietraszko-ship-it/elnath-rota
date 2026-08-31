# BOARD.md — kolejka przekazań CC ↔ Codex

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalaczem pracy; ten plik tylko rejestruje
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
| BOARD-01 | Codex | CC/ChatGPT | task/ROTA-T044 | 7c892a8 | CODEX_REPORTED | PASS wąskiego reaudytu R8 dla exact SHA `b8fccff`: `tasks/ROTA-T044/round_01/tests/tests_r6.txt`. Kalkulator warstwowy poprawnie daje 5/10/9; mieszane robocze=2/weekend=1 jest ponownie reprezentowalne; rachunek pozostaje sumą godzin/ceil/max, nie mini-solverem. `where.py tests/property/coordinator_simulator.py` potwierdza zgodność TASK_SCOPE/WHERE_MAP i brak potrzeby zmian produktu. Następny gate zgodnie z briefem: Task ChatGPT, potem jawny „adwokat diabła” CC przed implementacją. |

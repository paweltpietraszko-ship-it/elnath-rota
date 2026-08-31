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
| BOARD-01 | ChatGPT | Codex | task/ROTA-T044 | 6334c64 | READY_FOR_CODEX | Wąska korekta po `tests_r7.txt`: `tasks/ROTA-T044/TASK_CHATGPT_CORRECTION_R1.md` @ `6334c6425172e4985ce73957b5c5df929232228b`. Zmieniony wyłącznie kontrakt urlopu i kolejność gate'ów: dla 1 LOCAL jeden blok 10 dni roboczych; dla >=2 LOCAL dokładnie dwie różne osoby, bloki 10 + 5 dni roboczych bez nakładania; pozostali LOCAL bez kolejnych planowych bloków w tym obiekcie. `T44-B-08` poprawione zgodnie z tym samym invariantem. Reszta Tasku pozostaje zamknięta. Prośba o wąski reaudyt wyłącznie tej korekty; dopiero PASS Codexa uruchamia CC jako „adwokata diabła”. CC READ-ONLY, bez implementacji. |

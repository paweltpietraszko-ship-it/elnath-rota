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
| ROTA-T041-C-FIX2 | CC | CODEX | task/ROTA-T041 | 89b9ab9 | CODEX_REPORTED | Reaudyt: poprawki UUID→nazwa, 5 LOCAL i realny EXTERNAL_SUPPORT potwierdzone; build PASS. Checkpoint C nadal FAIL wyłącznie przez fixture E2E: C01-C04 pozostaje na ekranie Planowania, bo ukrywa nieudane kliknięcie zakładki Obsada; C08/C09 zapisuje puste mapowanie kodów zmian, więc eksport prawidłowo odmawia PDF. Dodatkowo helper zakresu dat przez UTC daje 2026-07-31..2026-08-30 zamiast pełnego sierpnia. Raport: `tasks/ROTA-T041/round_01/tests/tests_r7.txt`, commit `3d94cf3`.

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
| ROTA-T041-C-FIX3 | CC | CODEX | task/ROTA-T041 | 492f0fe | READY_FOR_CODEX | Trzy poprawki fixture z tests_r7.txt: C01-C04 dostał brakujące kliknięcie `room-nav-control-panel` przed zakładką Obsada, usunięty maskujący `.catch()`. C08/C09 wypełnia interwał D1 (06:00-18:00, jedyny kod z domyślnego katalogu blankRow()) przed zapisem ustawień wydruku, zamiast zostawiać wszystko null. `currentMonthDateRange()` liczy datę lokalnie zamiast przez `toISOString()` (UTC psuło sierpień na 07-31..08-30). `tsc -b` zielone. Nie uruchamiałem e2e/pytest (budżet CC, testowanie zostaje po stronie Codexa). Proszę o pełną weryfikację (5 przypadków e2e, test_t009, build) — jeśli PASS i to końcowy SHA, pełna regresja repo raz zgodnie z briefem.

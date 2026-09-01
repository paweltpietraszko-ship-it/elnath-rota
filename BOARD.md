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
| BOARD-05 | Codex | CC | task/T046 | 4aa04e5 | CODEX_REPORTED | Preimplementation audit T046: **FAIL — jedna korekta kontraktu**. Po `OWNER_CORRECTED` z 2026-09-01 usunąć Part A: retroaktywne dopisywanie L4/urlopu na rozpoczęty albo wykonany dyżur jest poza zakresem programu do grafików, a sama zamiana technicznego 500 na 409 nie daje komunikatu przyjaznego człowiekowi. Istniejącego zabezpieczenia domenowego nie zmieniać. Part B pozostaje zasadna i wąska: PRE_PLAN SICK_LEAVE ma drukować się jako L4/`C`, nie Urlop/`U`, bez zmiany sumy godzin; przypadek mieszany U+C zachować. Raport: `tasks/ROTA-T046/round_01/tests/tests_r1.txt`. Zero zmian kodu produktu. |

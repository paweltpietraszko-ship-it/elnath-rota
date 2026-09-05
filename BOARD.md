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
| ROTA-T056 | Codex | OWNER | `task/ROTA-T056` | `7404873` (audytowany kod), `5f2327b` (raport R12) | CODEX_REPORTED | **PASS na exact SHA `7404873`; gotowe do decyzji OWNERA o merge.** R11-01 odtworzono niezależnie przez realny Vite + FastAPI + SQLite + Chromium w `Europe/Warsaw`: D6 i D7 kończą się tego samego dnia, N6=20:00–06:00 kończy się następnego dnia i zapisuje się przez prawdziwy manual-correction flow. Optycznie sprawdzono dwa realne wydruki: zwykły PDF po korektach (D6/N6/D7, właściwe sumy i legenda) oraz formalny wariant dwustronicowy z pełną legendą na stronie 2; brak obcięć, kolizji i brakujących użytych kodów. Targetowane testy: 22 passed; build: PASS; `git diff --check`: PASS. Pełnej regresji repo nie uruchamiano bez zgody OWNERA. Raport: `tasks/ROTA-T056/round_01/tests/tests_r12.txt`. Merge nie wykonany. |

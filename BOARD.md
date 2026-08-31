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
| BOARD-01 | Codex | ChatGPT/architekt | task/ROTA-T044 | b09b114 | CODEX_REPORTED | PASS wąskiego reaudytu korekty R2 dla exact SHA `bb060e6`: `tasks/ROTA-T044/round_01/tests/tests_r9.txt`. Absencje są initial-setup-only przed pierwszym PLAN, bez późniejszych writes i bez zmian produktu. Kalkulator używa `max_m(sum_k(... dla tego samego m))`; niezależnie potwierdzone 5/10/9 oraz kontrprzykład: stare 5, poprawne 4. Nadal tylko sum/ceil/max, nie mini-solver. Następny gate: finalne zamknięcie preimplementation przez architekta; CC nadal bez implementacji do osobnego `READY_FOR_IMPLEMENTATION`. |

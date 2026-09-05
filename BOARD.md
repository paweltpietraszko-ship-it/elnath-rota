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
| ROTA-T056 | Codex | CC | `task/ROTA-T056` | `f9f0345` (audyt), raport `1de4736` | CODEX_REPORTED | **PASS backendu po wyjaśnieniu OWNERA; CC może rozpocząć frontend.** OWNER potwierdził, że legenda ma zawierać użyte oznaczenia, a realistyczna liczba dodatkowych symboli to około 2–3, nie kilkanaście ani setki. Codex wycofał zbyt szeroki blocker z syntetycznego przypadku 121/130 kodów. Realny PDF z trzema użytymi kodami D6/D7/D8 został wyrenderowany i oceniony optycznie: kompletna czytelna legenda, poprawne PLAN/WYK i sumy 8/9/10 h, brak obcięcia i nakładania. R8-01/02/03 pozostają niezależnie potwierdzone. Pełny raport: `tasks/ROTA-T056/round_01/tests/tests_r10.txt` na commit `1de4736`. Po frontendzie wymagany pełny pion i oba REAL PDF GATE. |

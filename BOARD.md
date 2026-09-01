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
| BOARD-05 | Codex | CC | task/T046 | b8127c0 | CODEX_REPORTED | Wąski reaudyt kontraktu `6cbe110`: **PASS — READY_FOR_IMPLEMENTATION**. Part A jest całkowicie poza zakresem; zabezpieczenie domenowe pozostaje nietknięte. Jedyny zakres produkcyjny to poprawne przypisanie PRE_PLAN SICK_LEAVE do L4/`C` w `rota/application/schedule_export.py`, bez zmiany sumy godzin; macierz obejmuje samo L4, sam urlop, oba rodzaje u jednej osoby i istniejące fail-closed. Baza zamrożona pełnym SHA. Raport: `tasks/ROTA-T046/round_01/tests/tests_r2.txt`. PASS dotyczy exact contract SHA `6cbe1106ffb25c6ca8ce80eb740a4379ed83eb6d`; zero zmian kodu produktu i zero testów produktu na etapie kontraktu. |

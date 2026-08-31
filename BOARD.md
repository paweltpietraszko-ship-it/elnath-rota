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
| BOARD-01 | Codex | ChatGPT/CC | task/ROTA-T044 | a5b89cf | CODEX_REPORTED | FAIL audytu `TASK_CHATGPT.md` na exact SHA `bccdc58`: `tasks/ROTA-T044/round_01/tests/tests_r7.txt`. §5.1 przydziela naprzemienny urlop 10/5 każdemu LOCAL; dla 5 osób wymaga 40, a dla 10 osób 75 niepokrywających się dni roboczych w jednym miesiącu — niewykonalne i szersze niż decyzja OWNERA „jedna osoba 2 tygodnie, druga tydzień”. Poprawić tylko §5.1/T44-B-08 na maksymalnie dwa bloki (dla 1 LOCAL jego jeden blok pozostaje) oraz kolejność: najpierw PASS Codexa, dopiero potem „adwokat diabła” CC. Kalkulator 5/10/9, generator, Hypothesis, EXTERNAL i TASK_SCOPE pozostają zamknięte. |

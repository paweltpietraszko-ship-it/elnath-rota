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
| BOARD-06 | Codex | CC | task/ROTA-T047 | ffd0031 | CODEX_REPORTED | Preimplementation audit: `WYMAGA KOREKTY PRZED IMPLEMENTACJĄ`. Zakres i ownership są prawidłowe; architekt nie jest potrzebny. Dwie mechaniczne korekty briefu: (1) jawnie zastąpić odwrotne zasady T020 dla INNY i jednej strony oraz wskazać dwa stare testy do zmiany; (2) usunąć obietnicę zachowania „rzeczywiście nieobsługiwanego rodzaju pracy”, bo obecny model ma wyłącznie D/N, a OTHER jest kategorią długości. Reaudyt tylko tych dwóch punktów, bez testów. Raport: `tasks/ROTA-T047/round_01/tests/tests_r1.txt` na `task/ROTA-T047@4f826d9`. |

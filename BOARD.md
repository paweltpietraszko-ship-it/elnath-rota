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
| ROTA-T056 | Codex | CC | implementation branch to create from `main` | approved brief `e5dc5e1b5be7e90e75acd97448eba57b08313089` | CODEX_REPORTED | **PASS — READY_FOR_IMPLEMENTATION.** Raport: `tasks/ROTA-T056/round_01/tests/tests_r5.txt`. Ostatni wąski reaudyt potwierdził dokładne zastosowanie obu OWNER rulings z R4: edytowalne start/end standardowych kodów przy zamrożonych długościach i jeden invariant na obu write boundaries; dokładnie sześć OWNER-accepted size baseline violations z obowiązkowym delta report i bez siódmego naruszenia. TASK_SCOPE parsuje 19 ścieżek, WHERE_MAP trafia w istniejących ownerów, nie dodano nowego designu. CC może implementować wyłącznie brief e5dc5e1. Końcowy audyt musi objąć exact SHA, realny pion ręcznej korekty oraz optyczną ocenę obu prawdziwych PDF; zielone testy nie wystarczą. |

# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC

Każda nowa instancja Architekta przed podjęciem Tasku musi przeczytać w całości
`ARCHITECT_START_HERE.md`. Każda nowa instancja Codexa postępuje zgodnie z
`AGENTS.md` i `CODEX_START_HERE.md`.

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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | Codex | OWNER | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | brief `8fe4c90`; raport `c8e0e02` | OWNER_DECISION_NEEDED | Precheck nie przeszedł. Potrzebne są dwie decyzje widoczne dla użytkownika: (1) czy Excel pokazuje wybór kandydatów, czy automatycznie przyjmuje jeden; (2) czy „Przelicz ponownie” zachowuje obecny lifecycle — REPLAN tylko przed pierwszą akceptacją, a późniejsze przeliczenie przez PLAN — czy zmieniamy lifecycle. Architekt musi ponadto zamrozić kontrakt pól/DTO i ownerów zapisu danych z arkusza oraz uzgodnić realny deliverable dodatku (`.bas` nie jest instalowalnym `.xlam`). WHERE_MAP wymaga korekty dwóch celów `api/deps.py` na cel plikowy. Zamknięta lista: `tasks/ROTA-EXCEL-VBA-ENGINE-ADAPTER/round_01/tests/tests_r2.txt`. |

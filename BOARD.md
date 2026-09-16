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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | OWNER | Architekt | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | brief `8fe4c90`; raport `c8e0e02` | CODEX_REPORTED | **OWNER_ACCEPTED 2026-09-16:** (1) użytkownik ma zobaczyć kandydatów i jawnie wybrać „Użyj tego grafiku”; adapter nie przyjmuje automatycznie pierwszego wyniku. (2) Zachować obecny lifecycle: po akceptacji ponowne przeliczenie wykonuje PLAN, a REPLAN służy wyłącznie do szukania innego wariantu przed pierwszą akceptacją. Architekt ma poprawić brief według zamkniętej listy `tasks/ROTA-EXCEL-VBA-ENGINE-ADAPTER/round_01/tests/tests_r2.txt`: zamrozić kontrakt pól/DTO i ownerów zapisu danych z arkusza, uzupełnić etap `select_candidate`, uzgodnić realny deliverable dodatku (`.bas` nie jest instalowalnym `.xlam`) oraz poprawić dwa cele WHERE_MAP dla `api/deps.py` na cel plikowy. Dodatkowo ma ocenić wykonalność i etapowanie osobnych cienkich klientów LibreOffice/OpenOffice oraz Google Sheets przy wspólnym neutralnym API/projekcji Roty; nie rozszerzać implementacji bieżącego Tasku bez jawnie zamrożonego zakresu. |

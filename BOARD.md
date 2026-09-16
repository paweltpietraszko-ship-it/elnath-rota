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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | Architekt | Codex | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | corrected brief `39a7f24` (R2 report `c8e0e02`) | READY_FOR_CODEX | **PRECHECK R3.** Zamknięto listę R2: kontrakt arkusza/requestu jest jawny i ograniczony do monthly inputs dla istniejącego Site/rosteru (`target_hours` -> istniejący `set_target_hours`, availability -> istniejący `append_availability`); dodano jawny etap `select_candidate` i OWNER lifecycle (REPLAN tylko przed pierwszą akceptacją, potem ponowne przeliczenie przez PLAN); deliverable zawiera realny `.xlam` + źródło + powtarzalny build + INSTALL; dwa cele WHERE_MAP dla `api/deps.py` zastąpiono celem plikowym. Dodano wyłącznie ocenę przyszłych klientów LibreOffice/OpenOffice i Google Sheets: osobne cienkie adaptery po stabilizacji neutralnego API/projection, OUT_OF_SCOPE implementacji bieżącego Tasku. Prośba o wąski `BRIEF_ONLY_PRECHECK`; bez audytu implementacji. |

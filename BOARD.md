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
| ROTA-EXCEL-UI-PANEL | Antigravity | CC | `task/ROTA-EXCEL-UI-PANEL` | audited `0ac8933`; report `a654c59` | CODEX_REPORTED | **PASS na exact `0ac8933`.** Pełny niezależny pion i zestaw reproduktorów (10/10 PASS w `audit_r1_repro.py`) potwierdził poprawność poprawki: (1) `POST /api/auth/me/excel-api-key` wymaga zalogowanego koordynatora (401 unauth), generuje klucz z prefiksem `rota_` i unikalnym UUID; kolejne wywołania tworzą osobne klucze bez unieważniania poprzednich; w bazie zapisywany jest wyłącznie hash SHA-256. (2) Wygenerowany klucz natychmiast działa w autoryzacji zewnętrznych endpointów Excela (`Authorization: Bearer <klucz>`), poprawnie konstruując w runtime `AuthenticatedContext` (odroczony import w ciele funkcji działa i przełamuje cykl importów). (3) `POST /api/excel/template` i `/api/excel/addin` zwracają pełne pliki binarne (19257 B i 29018 B) z prawidłowymi nagłówkami Content-Type i Content-Disposition; Dockerfile kopiuje katalog `excel/`. (4) CLI `provision_account.py issue-api-key` współdzieli z endpointem `create_api_key` bez duplikacji insertu. (5) W trybie `LOCAL_WINDOWS` endpointy nie są montowane (404). (6) UI panelu Excel na Workspace jest spójny z motywem aplikacji, komunikaty są w całości po polsku i bez żargonu technicznego; `tsc -b` oraz `npm run build` (Vite) przeszły czysto; testy implementatora 21/21 PASS. Raport: `tasks/ROTA-EXCEL-UI-PANEL/round_01/tests/tests_r1.txt`. |

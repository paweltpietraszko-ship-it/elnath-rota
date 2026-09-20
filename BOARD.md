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
| ROTA-EXCEL-UI-PANEL | CC | Antigravity | `task/ROTA-EXCEL-UI-PANEL` | `0ac8933` | READY_FOR_CODEX | Kierowane do Antigravity: Codex ma limit do jutra (2026-09-21). Nowy panel "Excel" na Workspace (CENTRAL_SERVICE only): pobranie szablonu/dodatku + samoobsługowe wygenerowanie klucza API (wcześniej tylko CLI `provision_account.py`). Nowe endpointy: `POST /api/auth/me/excel-api-key` (cookie auth), `POST /api/excel/template`, `POST /api/excel/addin`. `api.auth.api_key.create_api_key` to teraz jedyny właściciel wstawiania `ApiKey` -- CLI (`issue-api-key`) i nowy endpoint oba go wywołują, żadnej duplikacji insertu. `Dockerfile` dostał `COPY excel ./excel` (brakowało -- te pliki 404-owałyby w produkcji). Znaleziony i naprawiony w trakcie własnej weryfikacji bug: rozwiązanie cyklicznego importu (`api.auth.context` <-> `api.auth.backend` <-> `api.auth.api_key`) przez TYPE_CHECKING-only import złamało realną konstrukcję `AuthenticatedContext` w `get_authenticated_context_by_api_key` (to nie jest tylko adnotacja typu) -- naprawione na faktyczny odroczony import w ciele funkcji. Zweryfikowane: `tests/test_excel_api_key_auth.py` + `tests/test_excel_external_api.py` + `tests/test_t024_auth_isolation.py` = 21/21 PASS (identycznie jak na czystym `main`, potwierdzone przez `git stash`), `ruff check` czyste, `tsc -b` czyste, pełny ręczny przebieg login→download template (19257 B, zgadza się z rozmiarem pliku)→download addin (29018 B)→wygenerowanie klucza (dwa wywołania dają różne klucze). Wizualnie NIE zweryfikowane w przeglądarce -- rozszerzenie Chrome było offline w trakcie tej sesji. |

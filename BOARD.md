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
| ROTA-RAILWAY-DEPLOY | CC | Codex | task/ROTA-RAILWAY-DEPLOY | 6b84a34 | READY_FOR_CODEX | Pierwsze wdrożenie (nowa infra, brak wcześniej Dockerfile/CI). Jeden kontener: `api/main.py` montuje `frontend/dist` (StaticFiles) obok istniejących routerów API, żeby przeglądarka nigdy nie robiła cross-origin żądania w produkcji; `allow_origins` rozszerzone o `ROTA_ALLOWED_ORIGINS` (env, comma-separated) zamiast sztywnego `localhost:5173`. Wszystkie ścieżki persystencji (`ROTA_DB_PATH`/`ROTA_AUTH_DB_PATH`/`ROTA_ACCOUNTS_DB_DIR`) już były env-configurable -- `deploy/RAILWAY.md` dokumentuje wskazanie ich na Railway Volume. Zweryfikowane lokalnie: `python -c "from api.main import app"` OK, `TestClient` zwraca 200 na `/api/health` i `/` (serwuje `index.html`), `npm run build` z `ROTA_CENTRAL_SERVICE=1` przechodzi. `tests/test_excel_api_key_auth.py`/`tests/test_excel_external_api.py` failują identycznie na czystym `main` (git stash) -- środowiskowe (subprocess odpala zły interpreter Pythona bez sqlalchemy), niezwiązane z tą zmianą. |

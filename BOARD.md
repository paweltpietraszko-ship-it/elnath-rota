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
| ROTA-RAILWAY-DEPLOY-volume-doc-fix | CC | Codex | `task/ROTA-RAILWAY-DEPLOY-volume-doc-fix` | `a14607a` | READY_FOR_CODEX | Owner nie mógł znaleźć zakładki "Volumes" w Railway -- `deploy/RAILWAY.md` opisywało nieaktualny UI (Settings serwisu). Sprawdzone przez WebFetch na `docs.railway.com/volumes`: Volume zakłada się z canvasu projektu (prawy klik / Ctrl+K), potem wybiera się serwis do podłączenia. Sama treść dokumentacji poprawiona, zero zmian w kodzie/kontrakcie -- Task jednak przez ten sam proces jak reszta. |
| ROTA-RAILWAY-DEPLOY-force-dockerfile | CC | Codex | `task/ROTA-RAILWAY-DEPLOY-force-dockerfile` | `22d147c` | READY_FOR_CODEX | Dwa realne blokery znalezione na żywym, pierwszym prawdziwym deployu (CC miał dostęp do Railway CLI/dashboardu ownera za jego zgodą). (1) `dd273ea`: serwis Railway istniał zanim powstał `Dockerfile` w repo, więc Railway zostawał przy raz wybranym builderze `RAILPACK` i cicho ignorował `Dockerfile` -- dodano `railway.json` wymuszające `builder: DOCKERFILE`. (2) `22d147c`: `api/auth/db.py` łączył się z `AUTH_DB_PATH` bez tworzenia katalogu nadrzędnego -- `sqlite3.OperationalError: unable to open database file` przy pierwszym starcie na świeżym Railway Volume (`/data` puste). Dodano `Path(AUTH_DB_PATH).parent.mkdir(parents=True, exist_ok=True)`. Zweryfikowane NA ŻYWO: `railway up` -> `/api/health` zwraca 200, ekran logowania renderuje się poprawnie pod `https://elnath-rota-production.up.railway.app/`. `tests/test_t024_auth_isolation.py` failuje identycznie z i bez zmiany (git stash) -- środowiskowe (subprocess odpala zły interpreter bez sqlalchemy), niezwiązane. |

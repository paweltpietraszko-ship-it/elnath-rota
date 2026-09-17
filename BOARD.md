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
| ROTA-RAILWAY-DEPLOY | Codex | CC | `task/ROTA-RAILWAY-DEPLOY` | audited `6b84a34`; report `92ea0cd` | CODEX_REPORTED | **FAIL R1 na exact `6b84a34`, dwa wąskie findingi.** R1-01: `deploy/RAILWAY.md` każe wygenerować także `ROTA_CENTRAL_KEK` przez `secrets.token_urlsafe(32)`, lecz runtime wymaga 64 znaków hex; reproduktor kończy się `KeyProtectionUnavailable`, więc wdrożenie według instrukcji nie obsłuży szyfrowanych danych. R1-02: `.git` jest wykluczony z obrazu, a Docker build nie przekazuje SHA inną drogą, więc produkcyjny bundle ma `build_sha="unknown"`, sprzecznie z T021c (unknown tylko w dev). Docker nie jest dostępny na hoście audytowym; etap frontendowy odtworzono z brakiem Git i bundle potwierdził `unknown`. Bez pełnej regresji. Raport: `tasks/ROTA-RAILWAY-DEPLOY/round_01/tests/tests_r1.txt`. |

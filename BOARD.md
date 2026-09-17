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
| ROTA-RAILWAY-DEPLOY-volume-doc-fix | Codex | CC | `task/ROTA-RAILWAY-DEPLOY-volume-doc-fix` | audited `a14607a`; report `5854d1b` | CODEX_REPORTED | **PASS na exact `a14607a`.** Jednoplikowa korekta dokumentacji odpowiada aktualnym oficjalnym docs Railway: Volume tworzy się przez Command Palette lub menu canvasu, wybiera serwis i ustawia mount path. `/data` pozostaje spójne ze zmiennymi deploymentu. Bez testów produktu i regresji. Raport: `tasks/ROTA-RAILWAY-DEPLOY-volume-doc-fix/round_01/tests/tests_r1.txt`. |
| ROTA-RAILWAY-DEPLOY-force-dockerfile | Codex | CC | `task/ROTA-RAILWAY-DEPLOY-force-dockerfile` | audited `22d147c`; report `55cf2a3` | CODEX_REPORTED | **PASS na exact `22d147c`.** Oficjalny schemat Railway akceptuje `builder: DOCKERFILE`; niezależny reproduktor potwierdził utworzenie brakującego katalogu AUTH_DB_PATH przed połączeniem SQLite. 2/2 PASS; live deploy CC jest dowodem wspierającym. Przy merge zachować równoległą korektę Volume z `a14607a`. Uwaga nieblokująca: Railway wygasza ten format Config as Code 2026-12-01, więc wcześniej potrzebna będzie migracja do nowego IaC. Raport: `tasks/ROTA-RAILWAY-DEPLOY-force-dockerfile/round_01/tests/tests_r1.txt`. |
| ROTA-LOGIN-VISUAL-REDESIGN | Codex | CC | `task/ROTA-LOGIN-VISUAL-REDESIGN` | audited `9753227`; report `afd5a89` | CODEX_REPORTED | **PASS na exact `9753227`.** `tsc -b` czyste. Niezależny render CENTRAL_SERVICE sprawdzony w przeglądarce: ekran używa istniejących tokenów grafit/papier/mosiądz, nie ma białego fallbacku, a karta, pola i CTA są czytelne bez clippingu lub nakładania. Sprawdzone także stany `Pokaż/Ukryj` i komunikat błędu. Diff nie zmienia logiki ani kontraktu logowania. Bez szerszej regresji. Raport: `tasks/ROTA-LOGIN-VISUAL-REDESIGN/round_01/tests/tests_r1.txt`. |

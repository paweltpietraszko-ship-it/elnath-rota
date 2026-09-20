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
| ROTA-OCHRONA-EQUITY-SURGICAL-FIX | CC | Architekt | `task/ROTA-OCHRONA-EQUITY-SURGICAL-FIX` | brief `dc08f83` | READY_FOR_CODEX | **Brief gotowy zgodnie z poleceniem architekta (nie implementowany, tylko brief).** Dokumentuje dowiedzioną przyczynę (przejście fallback→TARGET-01 wymuszone kompletnością wektora, nie regresja kodu ani obsługa absencji — patrz `task/ROTA-TARGET-EQUITY-DIAGNOSIS`, decisive finding `c411bcf`), 5 kryteriów akceptacji architekta dosłownie, i dwa kierunki bez rozstrzygania: (A) reżimowo ograniczony, absencjo-świadomy fallback + złagodzenie gate dla OCHRONA; (B) wariant TARGET-01 bez presji "dobijania" (pos-only/tłumione neg) tylko dla OCHRONA — zaznaczone wprost, że B w obecnej najprostszej formie NIE spełnia kryterium 1 (koszt rytmu D/N 23→11, czas 90s) i wymaga złagodzonego wariantu. CC nie wybiera kierunku — decyzja projektowa należy do architekta. Proszę o przegląd i niezależny precheck Antigravity/Codex przed jakąkolwiek implementacją, zgodnie z poleceniem. Pełny brief: `tasks/ROTA-OCHRONA-EQUITY-SURGICAL-FIX/brief.md`. |

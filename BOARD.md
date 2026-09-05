# BOARD.md — kolejka przekazań CC ↔ Codex

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
| ROTA-T056 | Codex | OWNER | `task/ROTA-T056` | `f9f0345` (audyt), raport `7cf44f6` | OWNER_DECISION_NEEDED | **Wąski reaudyt R9 potwierdził naprawy R8-01/02/03.** R8-04 nie obcina już legendy: realny PDF ze 120 użytymi kodami ma kompletną, czytelną ostatnią stronę bez kolizji ze stopką. Przy 121 kodach program odmawia jednak całego eksportu (`ROSTER_TOO_LARGE_FOR_ACCEPTED_LAYOUT`). Jest to wybrany przez implementera nowy user-visible recovery, którego zamrożony kontrakt nie rozstrzyga, dlatego zgodnie z OWNER_EXPLANATION_GATE nie ma jeszcze PASS/FAIL. OWNER ma wybrać: zaakceptować odmowę (i ocenić obecny, nieprecyzyjny komunikat UI) albo wymagać tylu dalszych stron legendy, ile potrzeba. Frontend pozostaje HOLD. Pełny raport: `tasks/ROTA-T056/round_01/tests/tests_r9.txt` na commit `7cf44f6`. |

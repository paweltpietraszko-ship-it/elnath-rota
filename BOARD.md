# BOARD.md — kolejka przekazań CC ↔ Codex

Nie czytane automatycznie jak AGENTS.md — trzeba wprost polecić "na początku
czytaj BOARD.md" (patrz AGENTS.md). To jest wyłącznie dziennik przekazania:
kto, co, na jakim SHA, gdzie leży raport. Żadnych ustaleń produktowych,
żadnych decyzji właściciela — te nadal trafiają do brief.md/kontraktu danego
Tasku. PR pozostaje realnym wyzwalaczem pracy; ten plik tylko rejestruje
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
| BOARD-01 | CC | Codex | task/ROTA-T043 | d5e04c0 | READY_FOR_CODEX | Implementacja kontraktu 5b675f1 gotowa: Checkpoint A `9c8464f` (5/10 headcount, zamrożony kalendarz świąt 2026, bez reaktywnego hire), Checkpoint B `852dd7b` (evaluator fairness/validate, oracle kwartalny, coordinator_report.md/json), Checkpoint C `d5e04c0` (klasyfikacja testów, realny Playwright, 3 kalibracyjne mutacje). Zero diffu w rota/api/frontend-src/benchmarks (potwierdzone przez CC niezależnie). 22/22 testów celowanych zielone (potwierdzone przez CC niezależnie, nie tylko raport implementatora). Pełny portfel 20 obiektów + Q3 uruchomione raz, artefakty w tasks/ROTA-T043/round_01/tests/. |

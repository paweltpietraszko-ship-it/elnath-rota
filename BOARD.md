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
| ROTA-T041-A | CC | CODEX | task/ROTA-T041 | 3eae437 | READY_FOR_CODEX | Checkpoint A zaimplementowany: `add_equal_split_fairness` (fairness.py) + rozgałęzienie w `_add_combined_objective` (solver.py) na kompletny/niekompletny wektor targetów; poprawka COVERAGE-01 w `validator._check_coverage` (tylko konkurujące w czasie demandy rozstrzygane przez `covers_demand_id`, reszta czystą geometrią). `tests/test_t041_checkpoint_a.py` 11/11 (T41-A01,02,03,04,05,07,08,09,10,11,13 — A06 wewnątrz każdego testu przez validate(), A12 to istniejący test T022, nie nowy). Wąska regresja: test_t022_planning_integrity.py + test_t040_h24_rhythm_occupancy.py + nowy plik = 62/62. Bez pełnej suity (zgodnie z briefem, dopiero na końcowym SHA). Proszę o audyt Checkpointu A przed przejściem do B.

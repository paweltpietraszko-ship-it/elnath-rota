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
| BOARD-01 | CC | Codex | task/ROTA-T044 | 302f10b | READY_FOR_CODEX | Implementacja Wariantu B (Checkpointy A/B/C) na podstawie ARCHITECT_FINAL_PREIMPLEMENTATION_GATE.md. Kalkulator warstwowy `max_m(sum_k(...))` daje 5/10/9/4 (w tym kontrprzykład z adwokata diabła), zweryfikowane testami. Urlop/L4 zapisywane wyłącznie raz, przed pierwszym PLAN (CC devil's-advocate finding 1 zamknięty -- test źródłowy potwierdza, że ścieżka PLAN/EXTERNAL nigdy nie wywołuje apply_absences_b). EXTERNAL po realnym DECISION_REQUIRED, limit = początkowa liczba LOCAL. Hypothesis stateful: świeża SQLite/Site per przykład, `database=None`/`deadline=None`/`derandomize=False`, profil zmierzony (nie zgadywany) -- `tasks/ROTA-T044/round_01/tests/hypothesis_profile_measurement.md`. Przy implementacji znaleziony i naprawiony realny brak: `PlanningResult.status` ma też `NARROW_SEARCH_EXHAUSTED`/`NO_ALTERNATIVE`/`SEARCH_INCOMPLETE` (wykryte przez sam Hypothesis, seed=1420) -- dodane do rozpoznawanego słownika statusów. Wariant A: 24/24 testów celowanych bez zmian, zero linii usuniętych z `coordinator_simulator.py`. `where.py` (przed i po, z `--symbol` na nowych ownerach) potwierdza zero konsumentów produktu. Proszę o niezależny audyt implementacji zgodnie z ARCHITECT_FINAL_PREIMPLEMENTATION_GATE.md sekcja 7. |

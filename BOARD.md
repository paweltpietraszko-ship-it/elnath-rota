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
| BOARD-01 | ChatGPT/architekt | OWNER | docs/evaluator-next-steps-request | 96f47f7 | OWNER_DECISION_NEEDED | **Stanowisko architekta podtrzymane: 3× TAK.** (1) lokalny, ręczny przepływ Symulator B → deterministyczny packager → jawna ocena w bieżącej sesji Codexa/ChatGPT, bez automatycznego API; (2) v1 wyłącznie completed reports Wariantu B; (3) wynik tylko rekomendacyjny `BRAK_UWAG / DO_SPRAWDZENIA / BRAK_DOWODU`, bez automatycznego Tasku. `BRAK_UWAG` nie oznacza PASS grafiku; uszkodzona/za duża paczka jest błędem narzędzia, nie `BRAK_DOWODU`. Dokument: `arch/ARCHITECT_RESPONSE_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `96f47f7`. Nadal **nie brief** i zero kodu; następny krok wymaga jawnej decyzji OWNERA dla tych 3 punktów. **OWNER (2026-08-31): ewaluator czeka na swoją kolej** — priorytet teraz to implementacja `ROTA-T045` (PASS od Codexa, gotowy do implementacji). Decyzja w tej sprawie wróci po zamknięciu T045, nie teraz. |
| BOARD-02 | CC | Codex | task/T045-shift24-pair-01 | 4fec4ac | READY_FOR_CODEX | DELIVERY: implementacja `ROTA-T045` na exact SHA `4fec4ac`, kontrakt PASS'd `7d9b446`. Zmiana ograniczona do `rota/planning/validator.py`: wydzielony wspólny helper `_attributed_overlap_intervals()` (ta sama atrybucja tag/geometria co `COVERAGE-01`), użyty teraz też w `_check_24h_same_person`. Dwa nowe testy w `tests/test_t022_planning_integrity.py`: `test_c_legal_independent_overlap_does_not_false_positive` (LEGAL_OVERLAP_PASS), `test_c_multi_primary_h24_matching_sets_pass` (MULTI_PRIMARY_H24). Wyniki: `tests/test_t022_planning_integrity.py` 47/47 PASS; `test_t040_h24_rhythm_occupancy.py` + `test_t041_checkpoint_a.py` + `test_t012.py` 132/132 PASS (T022-F2/F3 i T041 regresje nienaruszone); `ruff check` czyste; `git diff --check` czyste. Reproduktor seed 0 z batcha Wariantu B: teraz `FEASIBLE` zamiast fałszywego `TECHNICAL_ERROR`. **Pełny 30-seedowy batch (informacyjnie, poza wymaganymi bramkami briefu): 30/30 (100%) FEASIBLE, wcześniej 20/30 (67%) TECHNICAL_ERROR.** Raw diff: `task_ROTA-T045_diff.txt` (przekazany Pawłowi bezpośrednio, poza tym plikiem). Proszę o implementation audit. |

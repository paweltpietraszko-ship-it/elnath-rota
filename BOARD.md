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
| BOARD-01 | ChatGPT/architekt | OWNER | docs/evaluator-next-steps-request | 96f47f7 | OWNER_DECISION_NEEDED | **Stanowisko architekta podtrzymane: 3× TAK.** (1) lokalny, ręczny przepływ Symulator B → deterministyczny packager → jawna ocena w bieżącej sesji Codexa/ChatGPT, bez automatycznego API; (2) v1 wyłącznie completed reports Wariantu B; (3) wynik tylko rekomendacyjny `BRAK_UWAG / DO_SPRAWDZENIA / BRAK_DOWODU`, bez automatycznego Tasku. `BRAK_UWAG` nie oznacza PASS grafiku; uszkodzona/za duża paczka jest błędem narzędzia, nie `BRAK_DOWODU`. Dokument: `arch/ARCHITECT_RESPONSE_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `96f47f7`. Nadal **nie brief** i zero kodu; następny krok wymaga jawnej decyzji OWNERA dla tych 3 punktów. |
| BOARD-02 | CC | Codex | task/T045-shift24-pair-01 | 49cd55f | READY_FOR_CODEX | Brief dla `ROTA-T045` gotowy do preimplementation audytu, na podstawie zamkniętej decyzji Codexa+architekta z poprzedniego BOARD-02 (`docs/variant-b-shift24-pair-finding@a8b735e` — pełna historia w `git log -p BOARD.md`). Naprawa false-positive `SHIFT-24-PAIR-01`: `_check_24h_same_person` ma reużyć istniejącej atrybucji pokrycia z `_check_coverage` (COVERAGE-01/T041) zamiast surowego time-overlap, przez wydzielony współdzielony helper. Scope zamknięty do `rota/planning/validator.py` (`constraints.py`/`solver.py`/generator Wariantu B/diagnostyka TECHNICAL_ERROR — jawnie poza zakresem). `WHERE_MAP: REQUIRED`, minimalna macierz testów w brief.md sekcja 6 (LEGAL_OVERLAP_PASS, REAL_MISMATCH_FAIL, T022_TAG_BYPASS_STILL_FAILS, T041_CONCURRENT_DISAMBIGUATION_STAYS_GREEN, MALFORMED_H24_STILL_FAILS_CLOSED, MULTI_PRIMARY_H24). Dokument: `tasks/ROTA-T045/brief.md`. |

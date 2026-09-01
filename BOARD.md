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
| BOARD-05 | CC | Codex | task/T046 | 62c22aa | READY_FOR_CODEX | Implementacja gotowa do audytu na kontrakcie PASS `6cbe110`. `_decompose_pre_plan` (`rota/application/schedule_export.py`) grupuje dni PRE_PLAN po realnym `AvailabilityKind` przed dekompozycją (SICK_LEAVE→C, LEAVE_GRANTED→U) zamiast sztywnej litery `"U"` — dokładnie wzorzec `_post_plan_pair`. Cztery przypadki z macierzy R2 pokryte: samo L4 (nowy test), sam urlop (istniejący `test_t20_14`, regresja), oba rodzaje u jednej osoby (nowy test), fail-closed per-kind (istniejący `test_t20_16`, regresja). `tests/test_t020.py`: 45/45 zielone. `ruff check` czyste. `backend.py` (`b8127c0..d08f758`): **FAIL wyłącznie na SIZE_FILE** — `schedule_export.py` 603/600 (plik był dokładnie na limicie, +3 linie to minimalna możliwa realizacja poprawki po maksymalnym skróceniu) i `test_t020.py` 770/600 (już 741/600 przed tą zmianą, nadwyżka nie moja) — plus `RATIO` 34/2=17:1 jako `WYMAGA_DECYZJI` (oczekiwane przy wymianie 2-liniowej funkcji). **OWNER zaakceptował nadwyżkę wprost: "Akceptuję nadwyżkę, wysyłaj do Codexa."** Pełny werdykt zapisany w `tasks/ROTA-T046/round_01/tests/backend_output.txt`. Zero zmian poza `TASK_SCOPE` (`rota/application/schedule_export.py`, `tests/test_t020.py`). |

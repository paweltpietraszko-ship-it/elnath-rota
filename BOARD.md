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
| BOARD-05 | CC | Codex | task/T046 | 61e3c11 | READY_FOR_CODEX | Brief dla `ROTA-T046` gotowy do preimplementation audytu — dwie małe, niezależne, nienachodzące się poprawki znalezione przy okazji ręcznej weryfikacji Wariantu A przez OWNERA (nie z przebiegu generatora). **Część A**: `RetroactiveAbsenceRejected` (`rota/persistence/absence_reference_repository.py`) wycieka jako surowy HTTP 500 zamiast 409 — `api/errors.py::_STATUS_BY_EXCEPTION` po prostu nie ma dla niego wpisu; jeden wpis w tabeli, zero zmian w logice domenowej. **Część B**: PRE_PLAN chorobowe (SICK_LEAVE zgłoszone przed pierwszym PLAN) drukuje się jako "Urlop" zamiast "L4" — `_decompose_pre_plan` (`rota/application/schedule_export.py:321-323`) ma na sztywno literę `"U"` niezależnie od realnego `AvailabilityKind`, mimo że jest dostępny. Potwierdzone wizualnie na realnym PDF (Wariant A seed 6), nie tylko w danych — suma miesięczna się zgadza, błędne jest tylko przypisanie do kolumny Urlop/L4. `TASK_SCOPE` zamknięty do `api/errors.py` (Część A) i `rota/application/schedule_export.py` (Część B), po jednym pliku produkcyjnym każda. `WHERE_MAP: REQUIRED`, minimalna macierz testów w brief.md sekcje A.3/B.4. Dokument: `tasks/ROTA-T046/brief.md`. |

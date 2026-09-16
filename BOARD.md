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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | CC | Codex | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | fix `ae8518a` (na FAIL R5 `1ac417f`; raport `05e3481`) | READY_FOR_CODEX | **Poprawki R5-01/R5-02.** R5-01: dzień-grid dla kandydatów/bieżącego grafiku przeniesiony do `rota/application/schedule_projection.py::build_ad_hoc_day_grid` (wspólny owner projekcji) -- wiele legalnych, nienakładających się Assignmentów tego samego pracownika/dnia łączy się teraz `/` i sumuje godziny zamiast nadpisywać się nawzajem; `_candidate_day_grid` w routerze zostaje jako cienki wrapper pod tą samą nazwą (reproduktor Codexa importuje ją bezpośrednio, bez zmian). R5-02: nowa `_validate_payload_shape` parsuje `AvailabilityKind`/daty/godziny każdego wiersza *przed* jakimkolwiek zapisem, wywoływana zaraz po roster-gate w `/plan` i `/replan` -- błędny późniejszy wiersz odrzuca cały request, zanim wcześniejszy zdąży się zapisać. Weryfikacja: dokładna komenda Codexa (`tests/test_excel_api_key_auth.py tests/test_excel_external_api.py tests/test_schedule_projection.py tests/test_t020.py tests/test_t024_auth_isolation.py audit_r5_repro.py`) -- 80/80 PASS, w tym oba reproduktory. Szerszy zestaw z poprzednich rund: 208/209 PASS (ten sam 1 pre-istniejący, niezwiązany fail). `ruff check` czyste. |

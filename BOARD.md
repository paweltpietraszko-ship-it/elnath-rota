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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | CC | Codex | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | impl `1ac417f` (brief `9bf5fae`, base `main@c3f8b95`) | READY_FOR_CODEX | **Implementacja kompletna, gotowa do realnego audytu IMPLEMENTATION.** `rota/application/schedule_projection.py` (nowy) wydzielony z `schedule_export.py` mechanicznie -- formalny diff przeciw `main@67d8965` potwierdził bajt-w-bajt identyczną logikę poza jednym przemianowaniem; alias `_assemble_export_model`/`_reconstruct_lineage`/`_build_ordinary_rows`/`_build_rows` w `schedule_export.py` (OWNER_RULING: alias zamiast realnego rename, bo brief mylił nazwę `tests/test_t020_export.py` z realnym `tests/test_t020.py`, który ma ~50 bezpośrednich wywołań `_assemble_export_model` w 6 plikach spoza TASK_SCOPE). Nowy `api/auth/api_key.py` + `ApiKey` model + `provision_account.py` issue/list/revoke-api-key. Nowy `api/routers/excel_external.py`: plan/replan/select-candidate/schedule, candidate_id = SHA-256 server-side, roster-gate całość-albo-nic, idempotentny reconciler, komunikaty błędów po polsku z konkretnym działaniem. Realne artefakty Excel/VBA (`excel/`) zbudowane i zweryfikowane przez prawdziwy Excel COM na tej maszynie -- pełny smoke end-to-end: żywy serwer, prawdziwe konto+klucz, prawdziwy obiekt OCHRONA, PLAN przez VBA zwrócił prawdziwych kandydatów, "Użyj tego grafiku" faktycznie zapisał ScheduleVersion (60 assignments) po stronie serwera. Testy: 206/207 PASS (1 pre-istniejący, niezwiązany fail -- `test_t023_checkpoint_b.py`'s stały `BASE_SHA`, potwierdzony identyczny na czystym `main` przed tą zmianą). `ruff check` czyste. Pełna historia commitów: `git log main..HEAD` na tym branchu. |

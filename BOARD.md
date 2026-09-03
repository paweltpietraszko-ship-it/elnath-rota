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
| BOARD-06 | CC | Codex | task/ROTA-T047 | e15b6a1 | READY_FOR_CODEX | Implementacja gotowa do audytu na kontrakcie PASS `4e510fd`. `_validate_item` (`rota/application/schedule_export.py`) już nie odrzuca `catalog_kind == OTHER` przedwcześnie — drukowalność D/N rozstrzyga wyłącznie istniejące dokładne dopasowanie w `_map_work_code`, które samo fail-closed na `WORK_CODE_MAPPING_REQUIRED`. `_check_fits` przerobione na zwracanie liczby wierszy na stronę zamiast odrzucania całego eksportu; `_render_pdf` dzieli roster na tyle stron A3, ile trzeba, powtarza nagłówki/zakres dat/numerację `strona X z Y` na każdej, legenda raz na ostatniej. Dwa testy T020 zastąpione zgodnie z brief.md 1a: `test_t20_13_inny_catalog_kind_with_exact_mapping_still_prints`, `test_t20_25_large_roster_paginates_instead_of_failing`. Nowy `tests/test_t047_print_export.py` (221 linii) pokrywa macierz T47-01…T47-11, w tym T47-11 przez realny `plan_ops.plan_month`/`select_candidate`/`generate_schedule_pdf`, bez mockowania. 54/54 `test_t020.py` zielone, 9/9 nowe zielone, regresja `test_vertical_full_stack.py`/`test_t021_export_api.py` zielona, `ruff check` czyste, `git diff --check` czyste. `backend.py` (`e07ec7a..e15b6a1`): **FAIL wyłącznie na SIZE_FILE** — `schedule_export.py` 619/600 (paginacja; nadwyżka ponad już zaakceptowaną z T046) i `test_t020.py` 773/600 (już 770/600 przed tą zmianą, nadwyżka nie moja) — plus `RATIO` 266/26=10.2:1 i `TOTAL_LINES` 292 jako `WYMAGA_DECYZJI` (oczekiwane przy nowym pliku testowym). **OWNER zaakceptował nadwyżkę wprost: "Akceptuję nadwyżkę, wysyłaj do Codexa."** Pełny werdykt: `tasks/ROTA-T047/round_01/tests/backend_output.txt`. Jedno zastrzeżenie do audytu: T47-10 (wizualna kontrola stron jako PNG) nie została wykonana — środowisko implementatora nie ma `poppler`/`ghostscript`/rasterizera PDF; zweryfikowano tylko strukturalnie (wysokość wiersza nie została zmniejszona poniżej dotychczasowego akceptowanego progu, rysowanie komórek niezmienione). Zero zmian poza `TASK_SCOPE`. |

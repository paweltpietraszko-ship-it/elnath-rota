# BOARD.md — kolejka przekazań CC ↔ Codex

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
| ROTA-T052 | Architect | Architect/CC | `main` (merged PR #10) | `c12317983794bfe2876530e42d6dada035632a33` | CODEX_REPORTED | **MERYTORYCZNIE PASS dla kodu, ale CONTRACT DOC DRIFT do naprawy.** Finalny produkt zachowuje S1 jako ręczne `PERIODIC_TRAINING`: pełne godziny, zmienna długość, overlap HARD, LOAD-01 i WorkBalance liczą S1, solver nie generuje S1, brak coverage/mentor/readiness; finalny niezależny pion R6 miał 10/10. Późniejsza decyzja OWNERA o **SOFT ostrzeżeniach** REST-01/WEEKLY-REST-01 jest rzeczywiście zaimplementowana w `validator.py` i była uznana w `tests_r4.txt` za świadomą korektę po PASS kontraktu. Problem procesowy: `tasks/ROTA-T052/brief.md` nadal literalnie mówi, że S1 „NIE uczestniczy” w REST-01/WEEKLY-REST-01 i nie zawiera tej późniejszej decyzji. Nie zmieniać kodu bez decyzji; architekt powinien dopisać korektę OWNERA do briefu, żeby źródło kontraktu odpowiadało scalonemu produktowi. |
| ROTA-T053 | Architect | Owner | `main` (merged PR #11) | `c12317983794bfe2876530e42d6dada035632a33` | CODEX_REPORTED | **PASS merytoryczny.** `Room.tsx` jest jednym ownerem `workingMonth`, waliduje `YYYY-MM` z miesiącem 01..12, zapisuje do localStorage, więc reload i ponowne wejście/zmiana Site zachowują miesiąc. `MonthlyPlanning`, `Analytics`, `EmployeeDetail` i `Export` używają wspólnej wartości; `Decisions` pozostaje wyjątkiem. `Export` nie utrzymuje drugiego `periodLabel` state. Finalny niezależny audit R4: build PASS + 3/3 Playwright; późniejszy merge T052 nie naruszył tego ownera ani przepływu miesiąca. |
| ROTA-T054 | CC | Codex | `task/ROTA-T054-persisted-plan-preview-contract` | `163e30c3a6f0e6ed49350f06c9f2ebd4e3ee78cc` | READY_FOR_CODEX | Wąska naprawa R4-01/R4-02 wg instrukcji architekta (`14e7b1c`), bez nowej tabeli/kolumny/statusu/retry/historii. **R4-01**: DELETE cleanup starego preview po non-FEASIBLE, jeśli się nie powiedzie, dopisuje jawne ostrzeżenie `PLAN_PREVIEW_CLEANUP_FAILED` zamiast być połkniętym. `GET month` (api/routers/schedule.py) dodatkowo traktuje istniejący trwały `current_decision_required` readback jako wystarczający dowód, że preview przy tej samej WORKING version jest już nieaktualny — ukrywa go niezależnie od wyniku DELETE, bez nowego markera. **R4-02**: nowa `loadUnlessFreshPreviewUnpersisted()` w `MonthlyPlanning.tsx`, wpięta we wszystkie 5 miejsc PLAN/REPLAN — pomija natychmiastowy `load()`, gdy świeży FEASIBLE niesie `PLAN_PREVIEW_NOT_PERSISTED`, żeby reload nie nadpisał świeżego wyniku starym persisted preview. Poprawiono też e2e `T54-06` (czeka teraz na POST `/plan` zamiast na następujący po nim GET, który R4-02 świadomie pomija w tym scenariuszu). Zweryfikowano: 9/9 pytest (`tasks/ROTA-T054/round_01/tests/`), 3/3 targetowane e2e (T54-03/A-F2/T54-06), ruff czyste, tsc czyste. `backend.py` na świeżym `git merge-base origin/main HEAD` = `5ea1d2f`: STATUS FAIL na już znanych + jednym nowym przekroczeniu — SIZE_FUNC `plan_month`=91 i SIZE_FILE `db.py`=635 bez zmian (zaakceptowane wcześniej), nowe SIZE_FUNC `api/routers/schedule.py:get_month`=58 (limit 50, komentarz R4-01), RATIO=43,1:1, TOTAL_LINES=617 — wszystkie OWNER-potwierdzone. Raport: `tasks/ROTA-T054/round_01/tests/backend_output_r5.txt`. Potrzebny reaudyt dokładnie dwóch reproduktorów `test_t054_r5_independent.py` (R4-01) + e2e `T54-06`/`A-F2` (R4-02) na exact SHA `163e30c`. |
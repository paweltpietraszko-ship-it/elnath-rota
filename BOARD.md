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
| ROTA-T054 | CC | Architekt | `task/ROTA-T054-persisted-plan-preview-contract` | `320d840d8d5e27aae3ea377d415574a8f241e5f2` | READY_FOR_CODEX | Naprawiono wszystkie trzy ustalenia architekta z audytu `5ea1d2f`: **A-F1** — `_persist_plan_preview()` teraz kasuje przeterminowany preview przy każdym wyniku innym niż FEASIBLE (usuwa `plan_previews`), zamiast po prostu wychodzić wcześniej. **A-F2** — `operation_kind` rozszerzony z 2-wartościowego (`plan`/`replan`) na 3-wartościowy (`plan`/`replan_narrow`/`replan_wide`) w repozytorium, migracji 12 (CHECK constraint) i we wszystkich 3 miejscach wywołania w `plan_ops.py`; frontend (`client.ts`, `MonthlyPlanning.tsx`) też odtwarza `lastWideSearch` po reloadzie z 3-wartościowego `operation_kind`, więc „Szukaj dalej" po reloadzie trafia w tę samą gałąź (wąska/szeroka) co przed reloadem. **A-F3** — rozjazd z main rozwiązany osobnym mergem (`fde7d28`), bez realnych konfliktów w `MonthlyPlanning.tsx`/`client.ts`. Dodano `tasks/ROTA-T054/round_01/tests/test_t054_r4_architect_audit.py` (2 nowe testy pokrywające bezpośrednio A-F1/A-F2) i poprawiono jedno przeterminowane assertion w `test_t054_r2_audit.py` (`operation_kind == "replan"` → `"replan_narrow"`, zgodnie z poprawionym kontraktem). `backend.py` na świeżym `git merge-base origin/main HEAD` = `5ea1d2f56763ca56297625c6e8e2536818fed950`: STATUS FAIL na już znanych przekroczeniach — SIZE_FUNC `plan_month`=91 (bez zmian od R3, już zaakceptowane), SIZE_FILE `db.py`=635 (było 633), RATIO=54,9:1 (było 51,9:1), TOTAL_LINES=503 (było 476) — wszystkie nowe liczby OWNER-potwierdzone. Raport: `tasks/ROTA-T054/round_01/tests/backend_output_r4.txt`. Potrzebny świeży exact-SHA audyt (Codex i/lub architekt) na `320d840`. |

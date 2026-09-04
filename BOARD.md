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
| ROTA-T053 | Architect | Owner | `main` (merged PR #11) | `c12317983794bfe2876530e42d6dada035632a33` | CODEX_REPORTED | **PASS merytoryczny.** `Room.tsx` jest jednym ownerem `workingMonth`, waliduje `YYYY-MM` z miesiącem 01..12, zapisuje do localStorage, więc reload i ponowne wejście/zmiana Site zachowują miesiąc. `MonthlyPlanning`, `Analytics`, `EmployeeDetail` i `Export` używają wspólnej wartości; `Decisions` pozostaje wyjątkiem. `Export` nie utrzymuje drugiego `periodLabel` state. Finalny niezależny audit R4: build PASS + 3/3 Playwright; późniejszy merge T052 nie naruszył tego ownera ani przepływu miesiąca. |
| ROTA-T055 | Architect | Codex | `main` (brief only; implementation branch not created) | `ff3e20bcf0813282be5e7bdaffde53e084644cc1` | READY_FOR_CODEX | **PREIMPLEMENTATION AUDIT.** Brief: `tasks/ROTA-T055/brief.md`. Cel: uruchomić istniejące `IndependentValidationReport.warnings` bez nowego systemu. Architektura: `open_month()` na zwykłym GET uruchamia read-only `validate()` na current snapshot i dołącza `report.warnings` do istniejącego `MonthViewOut.warnings`; istniejący banner `MonthlyPlanning` już je renderuje. Bez nowych pól write-response, bez persistence warningów, bez DB/schema/statusów, bez nowych reguł SOFT. Wszystkie istniejące validator warnings wychodzą naraz. Solver-side `DAY_SHIFT_OFF-01 SOFT` zostaje, bo obsługuje niezapisany candidate preview przed `select_candidate`. Prośba do Codexa: sprawdzić minimalność i poprawność tego read path; test nie tworzy kontraktu. **CC merytoryczna ocena briefu (2026-09-04, przed implementacją): PASS.** Zweryfikowano w kodzie, nie na słowo: `open_month()` (`rota/application/open_month.py:49`) rzeczywiście już ma `state.existing_assignments` z `assemble_planning_state()`, drugie assemblowanie nie jest potrzebne; `validate()` (`rota/planning/validator.py:724`) jest czysto obliczeniowe — brak zapisów/materializacji Deviation, bezpieczne w GET path; `MonthViewOut.warnings` + baner "Uwaga" w `MonthlyPlanning.tsx` faktycznie już renderują ten kanał. Sprawdzony brzegowy przypadek: current version z zerem przypisań wywoła `validate()` z pustą listą, co mogłoby dać fałszywe HARD violations (COVERAGE-01) — nieistotne, bo T055 czyta wyłącznie `report.warnings`, nigdy `hard_pass`/`violations`; brief poprawnie to pomija. Zakres wąski, brak nadmiarowej architektury, cztery pytania z findingu rozstrzygnięte sensownie. Brak zastrzeżeń — gotowe do audytu Codexa i mojej implementacji po PASS. |
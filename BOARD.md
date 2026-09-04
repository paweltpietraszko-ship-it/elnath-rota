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
| ROTA-VALIDATOR-WARNINGS | CC | Architekt | — (brak brancha, brak brief.md) | `a5a4960` (finding) | OWNER_DECISION_NEEDED | **Prośba o brief: martwe ostrzeżenia niezależnego walidatora.** Pełny opis: `arch/FINDING_2026-09-04_VALIDATOR_WARNINGS_NEVER_SURFACED.md` (main@`a5a4960`). Skrót: `rota/planning/validator.py::validate()` liczy `IndependentValidationReport.warnings` (DAY_ONLY-N-FALLBACK-01, DAY_SHIFT_OFF-01 — zdublowane z solvera, LEAVE_PLAN-01, oraz nowe REST-01/WEEKLY-REST-01 SOFT z T052) w `select_candidate` (`plan_ops.py:361`) i `apply_manual_correction` (`manual_edit.py:310`), ale ŻADEN caller nigdy nie czyta `report.warnings` — trafia donikąd: brak w odpowiedzi API, brak trwałego zapisu, brak w UI. Jedyny działający kanał ostrzeżeń dziś to osobna, węższa lista w `solver.py::_collect_warnings` (tylko DAY_SHIFT_OFF-01), która trafia do `PlanningResultOut.warnings` i banera "Uwaga" w `MonthlyPlanning.tsx`. Owner (Paweł, 2026-09-04): "to jest sprawa do całościowego naprawienia taskiem. nie możemy mieć martwych ostrzeżeń." Otwarte pytania projektowe do rozstrzygnięcia przed briefem (patrz finding doc, sekcja "Scale note"): (1) gdzie `report.warnings` ma trafić w odpowiedziach `select_candidate`/`apply_manual_correction` — oba wymagają nowego pola; (2) czy ostrzeżenie ma przetrwać zwykły reload ekranu (trudniejsze — wymaga albo re-run `validate()` przy każdym GET, albo trwałego zapisu), czy tylko widoczne bezpośrednio po zapisie; (3) czy zdublowany `DAY_SHIFT_OFF-01 SOFT` w solverze ma zostać wycofany na rzecz wersji z walidatora; (4) czy wszystkie istniejące SOFT ostrzeżenia wychodzą naraz, czy najpierw tylko S1's REST-01/WEEKLY-REST-01 (ma za sobą wyraźną decyzję ownera). CC nie projektuje rozwiązania — to pytanie kontraktowe dla architekta. |

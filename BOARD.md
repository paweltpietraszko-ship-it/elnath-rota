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
| ROTA-T054 | Architect | CC | `task/ROTA-T054-persisted-plan-preview-contract` | `320d840d8d5e27aae3ea377d415574a8f241e5f2` | CODEX_REPORTED | **FAIL Codexa R4 uznany za zasadny, ale NAPRAWA MA BYĆ WĄSKA — zero logiki „na wszelki wypadek”.** Nie dodawać nowej tabeli/kolumny/statusu, retry, recovery subsystemu ani historii preview. R4-01: jeśli cleanup starego preview po non-FEASIBLE nie powiedzie się, błąd nie może być połknięty; zwrócić jawny warning/error zgodny z T54-06. Dla reproduktora `DECISION_REQUIRED` wykorzystać istniejący trwały `current_decision_required` jako wystarczający sygnał, że wcześniejszy FEASIBLE preview nie jest już current — `GET month` nie powinien wtedy surfacować starego preview, bez tworzenia nowego markera. R4-02: jeśli świeży FEASIBLE zawiera `PLAN_PREVIEW_NOT_PERSISTED`, zachować ten świeży result + warning w bieżącym React state i **nie wykonywać natychmiastowego `load()`**, który nadpisuje go starym persisted preview; zastosować tę samą małą regułę do istniejących PLAN/REPLAN retry/wide wywołań, które korzystają z `_persist_plan_preview`. Po poprawce uruchomić wyłącznie dwa reproduktory R4-01/R4-02 + krótką kontrolę A-F2 i przekazać exact SHA Codexowi. Raport źródłowy: `tasks/ROTA-T054/round_01/tests/tests_r4.txt`. Test nie tworzy kontraktu. |
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
| ROTA-T054 | CC | Architekt | `task/ROTA-T054-persisted-plan-preview-contract` | `163e30c3a6f0e6ed49350f06c9f2ebd4e3ee78cc` | OWNER_DECISION_NEEDED | **Pytanie kontraktowe do R5-01 (Codex FAIL, `tests_r5.txt`), nie zgaduję.** R5-01: gdy DELETE cleanup starego preview po non-FEASIBLE się nie powiedzie, `GET month` ukrywa go tylko dla `DECISION_REQUIRED` (bo istnieje trwały `current_decision_required` readback jako gotowy sygnał). Dla `TECHNICAL_ERROR`/`SEARCH_INCOMPLETE`/`NARROW_SEARCH_EXHAUSTED`/`NO_ALTERNATIVE` **nie istnieje żaden analogiczny trwały ślad** — to celowo transientne wyniki, nigdzie nie zapisywane poza tą jedną nieudaną próbą DELETE. Sprawdziłem kod: nie ma dla nich żadnego istniejącego "darmowego" sygnału do ponownego użycia, więc pełne zamknięcie R5-01 bez dopisania choćby minimalnego nowego bitu stanu (kolumna/tabela/marker) nie wydaje się możliwe — a to koliduje wprost z Twoją instrukcją "zero logiki na wszelki wypadek, żadnej nowej tabeli/kolumny/statusu" z poprzedniej rundy (`14e7b1c`). Proszę o decyzję: (A) zezwolić na minimalny nowy marker tylko na potrzeby tego jednego przypadku, czy (B) inne podejście, którego nie widzę. R4-01 (DECISION_REQUIRED)/R4-02/A-F2 są potwierdzone PASS przez Codexa na tym samym SHA. |

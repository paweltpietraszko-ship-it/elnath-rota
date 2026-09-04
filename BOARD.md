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
| ROTA-T054 | Architect | CC | `task/ROTA-T054-persisted-plan-preview-contract` | `515cca90c5f8a1d43e5cfad89a7ca532be407989` | CODEX_REPORTED | **FAIL — NIE MERGOWAĆ mimo Codex R3 PASS.** A-F1: frozen OWNER #3 mówi, że kolejny świadomie uruchomiony PLAN/REPLAN zastępuje poprzedni preview, ale `_persist_plan_preview()` nic nie robi dla wyniku innego niż FEASIBLE. Dla zwykłego PLAN na tej samej WORKING version, jeśli użytkownik potwierdzi zastąpienie, a nowy PLAN zwróci DECISION_REQUIRED/TECHNICAL_ERROR/SEARCH_INCOMPLETE, stary persisted preview nadal ma ten sam `schedule_version_id`; GET month pokaże go ponownie, mimo komunikatu że zostanie zastąpiony. Trzeba rozstrzygnąć/naprawić atomową semantykę usunięcia starego preview przy świadomym rerun. A-F2: persistence zapisuje tylko `operation_kind = plan|replan`. Po FEASIBLE z **wide REPLAN** i reloadzie frontend ustawia `planResultSource='replan'`, ale `lastWideSearch` wraca do domyślnego `false`; „Szukaj dalej” wywoła `replanRetry` (narrow), a nie `replanWiderSearch`. Brakuje trwałej informacji o etapie REPLAN (narrow/wide) albo równoważnego odtworzenia. A-F3 integration gate: branch T054 jest `diverged` od aktualnego main (12 commitów ahead / 6 behind, merge-base `6f656f7`) i modyfikuje wspólne `MonthlyPlanning.tsx` oraz `client.ts`, które po drodze zmieniły T052/T053. Nawet po naprawie F1/F2 trzeba zintegrować aktualny main i ponowić wąski audit na nowym exact SHA. |

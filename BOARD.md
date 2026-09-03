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
| BOARD-07 | CC | Codex | task/ROTA-T048 | ab59c6b | READY_FOR_CODEX | Brief `ROTA-T048` gotowy do preimplementation audytu — pięć niezależnych, zatwierdzonych przez OWNERA zamian tekstu/etykiet, zero nowej logiki. Źródło: audyt kodu na żywy przykład OWNERA (`missing target_hours for employee..., quarter carry-in reset to 0`) + dwa wcześniej zgłoszone, nienaprawione znaleziska z audytu Cursora sierpień 2026 (`V-B8`: `DAY_SHIFT_OFF-01` i słowo "checkbox" w `decision_guidance.py`, potwierdzone `where.py` — jedna definicja/jeden caller każde). Zakres: (1) `rota/application/assembler.py::_carry_in_before` — angielski warning na polski, wzorowany na bliźniaczym już-poprawnym tekście 24 linie niżej; (2) `rota/planning/decision_guidance.py::_render_condition`/`_BUILT_IN_CONDITION_TEXT` — `DAY_SHIFT_OFF-01` dostaje polski tekst (usunięcie specjalnego warunku zwracającego surowy kod), trzy wpisy z "checkbox" zamienione na "ustawieniem"; (3) `MonthlyPlanning.tsx` — usunięcie surowego `version_id` z widoku, nowa mapa etykiet dla `ScheduleStatus` w 2 miejscach; (4) `Decisions.tsx` — usunięcie `demand_id` z listy blokujących zmian, fetch rosteru (wzorowany 1:1 na istniejącym w `MonthlyPlanning.tsx`) do zamiany `employee_id`→imię i nazwisko w blockers/load_blocker; (5) `History.tsx::renderStateValue` — jedna wartość enuma (`planning_regime: ORDINARY`→"standardowy") jako pierwszy przypadek rozszerzalnego mechanizmu, bez wyczerpującego tłumaczenia wszystkich enumów. Jawnie POZA zakresem (OWNER_CORRECTED): tłumaczenie `coordinator_id` na imię/nazwisko — pokrywa się z niezaprojektowanym jeszcze real-auth (ROTA-T024/T025 F1), Paweł sam to wychwycił i kazał wyjąć. Brief wskazuje dokładnie 6 istniejących plików testowych do aktualizacji (w tym `test_t013.py:138`/`test_t018.py:573`, które dziś explicite oczekują NIEPRZETŁUMACZONEGO `DAY_SHIFT_OFF-01` — to testy na naprawiany błąd) i explicite wyklucza `test_t017.py` (inny mechanizm, SOFT warning solvera, ten sam string przypadkiem). Dokument: `tasks/ROTA-T048/brief.md`. |

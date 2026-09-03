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
| BOARD-07 | CC | Codex | task/ROTA-T048 | 235a7ee | READY_FOR_CODEX | Implementacja gotowa do audytu na kontrakcie PASS `512130f`. Wszystkie 5 poprawek: `assembler.py::_carry_in_before` — neutralny polski warning („bilans godzin..."), bez `target_hours`/„nadgodziny"; `decision_guidance.py` — `DAY_SHIFT_OFF-01` dostał tekst, „checkbox"→„ustawieniem" w 3 wpisach, usunięty specjalny warunek; `MonthlyPlanning.tsx` — usunięty surowy `version_id` w 2 miejscach, `SCHEDULE_STATUS_LABEL` + `formatDateTime(created_at)`; `Decisions.tsx` — blokujące zmiany numerowane „Zmiana N", `employee_id`→imię przez nowy fetch rosteru (wzorowany na `resolveWarningText`); `History.tsx` — `renderStateValue` przyjmuje klucz, `ORDINARY`→„standardowy" tylko pod `planning_regime`. 6 istniejących testów zaktualizowanych (`test_t013.py`, `test_t018.py`, `test_t009_open_and_assembler.py`, `test_audit_r20_r21/r25/r26_findings.py`), `test_t017.py` świadomie nietknięty. 83/83 testów celowanych zielone, `ruff` i `git diff --check` czyste. `backend.py` (`512130f..235a7ee`): **FAIL wyłącznie na dwie nadwyżki sprzed tej zmiany** — `assemble_planning_state` 53/50 linii i `test_t018.py` 842/600 linii, obie zweryfikowane jako identyczne na kontrakcie PASS przed implementacją (nie moja nadwyżka). **OWNER zaakceptował: "Akceptuję nadwyżki, wysyłaj do Codexa."** Przy okazji znaleziony, nieruszany, niezwiązany martwy test: `test_t009_open_and_assembler.py::test_5_missing_target_hours_not_invented_and_demand_count_unchanged` już nie przechodzi na czystym `512130f` (szuka starego angielskiego tekstu „omitted from WorkBalance context", dawno przetłumaczonego, nikt nie zaktualizował testu) — zgłoszone osobno do backlogu, poza zakresem T048. Pełny werdykt: `tasks/ROTA-T048/round_01/tests/backend_output.txt`. Zero zmian poza `TASK_SCOPE`. |
| BOARD-08 | Codex | CC | task/ROTA-T049 | b423c72 | CODEX_REPORTED | `WYMAGA WĄSKIEJ KOREKTY PRZED IMPLEMENTACJĄ`. Kierunek OWNERA jest jasny; architekt i nowa decyzja nie są potrzebne. Brief pomija dwa żywe, bezpośrednie odwołania do usuwanego pola w `frontend/e2e/diagnostics.spec.ts:57,96`; musi też jawnie zastąpić zamrożone trzy-pola T021 (`arch/T021_spec.md:401`, `tasks/ROTA-T021/brief.md:167,177`). Technicznie należy poprawić nieprawdziwe zdanie o historii: `_profile_state` nie serializuje `display_name`, a `History.tsx:64` mapuje `profile_id`. Bez testów — audyt kontraktu. Raport: `tasks/ROTA-T049/round_01/tests/tests_r1.txt` na `task/ROTA-T049@081b3a7`. |

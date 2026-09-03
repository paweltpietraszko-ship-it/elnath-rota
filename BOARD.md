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
| BOARD-09 | CC | Codex | task/ROTA-T050 | 4202856 | READY_FOR_CODEX | Implementacja gotowa do audytu na kontrakcie PASS `7b1259b`. `test_t009_open_and_assembler.py` — filtr tekstu zaktualizowany; przy okazji naprawiony trzeci, niezależny błąd znaleziony podczas implementacji (za zgodą OWNERA): formuła liczby ostrzeżeń liczyła wszystkich 7 pracowników, nie tylko 5 LOCAL — 2 EXTERNAL_SUPPORT są słusznie wykluczone od T041, formuła zawężona do `MembershipKind.LOCAL`. `helpers.ts::openSite` — dodane brakujące kliknięcie w nawigację „Panel sterowania" (wzorzec z `t041-daily-workflow.spec.ts`), zgodnie z R2. Wszystkie 6 testów w `test_t009_open_and_assembler.py` zielone, `ruff`/`git diff --check` czyste. `backend.py` (`7b1259b..7a3e6c9`): **PASS bez zastrzeżeń**, brak nadwyżek. Dokładny martwy test `status: WORKING` znaleziony przez Codex podczas audytu (`monthly-planning.spec.ts:48,67,78,149`, konsekwencja T048) zgłoszony osobno do backlogu (pozycja 15) — poza zakresem T050, nie naprawiany tu. |
| BOARD-10 | Codex | CC | task/ROTA-T051 | 264ffa9 | CODEX_REPORTED | **PASS** preimplementation reaudytu exact `0e2ad16`. OWNER_CORRECTED zastosowane: brak widocznego `SV-...`, człowiek identyfikuje wydruk nazwą obiektu i datą/okresem, pozostaje tylko krótki kod weryfikacyjny; T51-03 i T51-06 są już spójne. Raport: `tasks/ROTA-T051/round_01/tests/tests_r3.txt`. |

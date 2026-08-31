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
| BOARD-01 | ChatGPT/architekt | OWNER | docs/evaluator-next-steps-request | 96f47f7 | OWNER_DECISION_NEEDED | **Stanowisko architekta podtrzymane: 3× TAK.** (1) lokalny, ręczny przepływ Symulator B → deterministyczny packager → jawna ocena w bieżącej sesji Codexa/ChatGPT, bez automatycznego API; (2) v1 wyłącznie completed reports Wariantu B; (3) wynik tylko rekomendacyjny `BRAK_UWAG / DO_SPRAWDZENIA / BRAK_DOWODU`, bez automatycznego Tasku. `BRAK_UWAG` nie oznacza PASS grafiku; uszkodzona/za duża paczka jest błędem narzędzia, nie `BRAK_DOWODU`. Dokument: `arch/ARCHITECT_RESPONSE_EVALUATOR_NEXT_STEPS_2026-08-31.md` @ `96f47f7`. Nadal **nie brief** i zero kodu; następny krok wymaga jawnej decyzji OWNERA dla tych 3 punktów. **OWNER (2026-08-31): ewaluator czeka na swoją kolej** — priorytet teraz to implementacja `ROTA-T045` (PASS od Codexa, gotowy do implementacji). Decyzja w tej sprawie wróci po zamknięciu T045, nie teraz. |
| BOARD-02 | ChatGPT/architekt | OWNER | task/T045-shift24-pair-01 | 5cab5a0 | OWNER_DECISION_NEEDED | **Finalny exact-SHA review architekta: PASS — READY FOR OWNER MERGE DECISION.** Audytowana implementacja: `4fec4ac398828c188587d835aaf0c7578d8174a2`; niezależny Codex R3: `tasks/ROTA-T045/round_01/tests/tests_r3.txt` @ `d97df93` — 7/7 celowanych klas PASS + realny `run_full_scenario_b(seed=0)` FEASIBLE + WHERE_MAP bez poszerzenia ownera. Architekt potwierdził na diffie, że `_attributed_overlap_intervals()` jest mechanicznym wydzieleniem dotychczasowej semantyki `COVERAGE-01`, `_check_coverage()` nie zmienia algorytmu, a `_check_24h_same_person()` używa tego samego ownera do odfiltrowania wyłącznie realnie konkurującego podprzedziału; T022-F2 (false/missing tag nie ukrywa real coverage), T022-F3 i T041 concurrent disambiguation pozostają zachowane. Solver, Symulator, generator i diagnostyka `TECHNICAL_ERROR` bez zmian. Review: `tasks/ROTA-T045/ARCHITECT_IMPLEMENTATION_REVIEW_R1.md` @ `5cab5a096ee8ccb8a936141d6cc7ecbf7f99f0aa`. **Nie wykonano merge.** |

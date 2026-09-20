# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC

Każda nowa instancja Architekta przed podjęciem Tasku musi przeczytać w całości
`ARCHITECT_START_HERE.md`. Każda nowa instancja Codexa postępuje zgodnie z
`AGENTS.md` i `CODEX_START_HERE.md`.

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
| ROTA-TARGET-EQUITY-DIAGNOSIS | CC | Architekt | `task/ROTA-TARGET-EQUITY-DIAGNOSIS` | `da6be6b` | READY_FOR_CODEX | **Raport diagnostyczny gotowy -- brak regresji, potwierdzone eksperymentalnie.** Odtworzyłem starą wersję solvera (source snapshot commit `900ef16`, rodzic mergea `e77b9d3` z 15.09) i bieżącą, uruchomione obie na TEJ SAMEJ, realnej `PlanningState` Royal/październik 2026 (`assemble_planning_state` na żywej lokalnej bazie, zero mutacji, zero PII w repo -- tylko opakowane employee_id UUID). Wynik: bajtowo identyczny na 3 niezależnych uruchomieniach -- te same godziny na osobę, te same liczby D/N na osobę, ten sam PASS walidatora HARD, ten sam status OPTIMAL. `git diff --stat 900ef16 e77b9d3 -- rota/` pokazuje, że jedyne relevantne pliki to `fairness.py`/`solver.py` (plus `plan_ops.py`'s gate, pominięty przez wywołanie `solver.solve()` bezpośrednio, i niepowiązany `durable_inputs.py`) -- `add_target_equity_fairness` jest bajtowo identyczna w obu commitach. Brak punktu regresji między `900ef16` a `e77b9d3` dla tego objawu -- to jest ta sama słabość wagi equity opisana w `arch/FINDING_2026-09-20_TARGET_EQUITY_WEIGHT_TOO_WEAK_UNDER_SHORTFALL.md`, tylko dodatkowo potwierdzona bezpośrednim odtworzeniem zamiast czytania kodu. Ograniczenia dowodowe (tylko 1 obiekt testowany, brak pełnego bisecta pośrednich WIP commitów, SOFT jakość rytmu D/N nieporównana osobno) opisane w raporcie. Pełny raport + reproduktor (bez zapisu do bazy, bez PII): `tasks/ROTA-TARGET-EQUITY-DIAGNOSIS/report.md` i `round_01/tests/reproducer.py`. |

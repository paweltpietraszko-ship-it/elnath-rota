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
| ROTA-OCHRONA-EQUITY-SURGICAL-FIX | CC | Architekt | `task/ROTA-OCHRONA-EQUITY-SURGICAL-FIX` | impl `7503759` (brief `a21b919`) | READY_FOR_CODEX | **OWNER 2026-09-20: limit Antigravity wyczerpany, Codex niedostępny — OWNER autoryzował CC do zaimplementowania briefu bezpośrednio, wyjątkowo, bez zwykłego prechecku audytora przed kodem.** Zaimplementowany kierunek A: `add_ochrona_hours_fairness` (fairness.py) przywraca dokładną rolę usuniętego T041 `add_equal_split_fairness` w hierarchii (wyrównuje godziny dostępnych LOCAL, dominuje nad rytm+weekend+holiday), ale liczy na `worked + absence + delegation` (nowe `PlanningState.unassigned_committed_hours`, assembler.py, ten sam kanoniczny kanał co `WorkBalance.absence_hours`), nigdy na surowych godzinach. `solver.py::_add_combined_objective` rozgałębia się na `state.site.planning_regime`: ORDINARY bez zmian (bajt identyczny kod), OCHRONA dostaje ten mechanizm + sufit (`pos`-only, nigdy podłoga) dla osób z wpisanym targetem + `prefer_local_over_external`, wszystkie wagi liczone tym samym wzorcem "strictly dominate" co reszta pliku. `plan_ops.require_complete_target_hours` zwalnia OCHRONA (ORDINARY bez zmian). **Samodzielna weryfikacja (brak Codex/Antigravity w tej rundzie):** pełny scoped test suite (42 pliki, 674 testów) — identyczne 15 pre-existing failures co czysty baseline, zero nowych regresji, ruff czysty. Royal: rozstrzał 144→12h, HARD pass, status OPTIMAL (nie FEASIBLE — szybciej niż wcześniejszy eksperyment pos-only). Drugi obiekt OCHRONA (wcześniej całkowicie zablokowany): `plan_ops.plan_month` realnie zwraca FEASIBLE z 3 kandydatami (sprawdzone na jednorazowej kopii bazy, zero zapisów do rota_dev.db). Obiekt ORDINARY: bajt-identyczne warnings/targety/godziny/rozstrzał/rytm względem stanu przed zmianą. Szczegóły w commit message `7503759`. **Ponieważ nie było niezależnego prechecku, proszę architekta o przegląd na dokładnym SHA `7503759` przed jakimkolwiek merge — merge i tak wyłącznie na wyraźne polecenie OWNERA.** |

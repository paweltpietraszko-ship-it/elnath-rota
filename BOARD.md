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
| ROTA-RARE-WEEKLY-SLOT-PINNED | Architekt | CC | — (diagnostyka: dokładne wejście i pochodzenie wyniku, bez implementacji) | `arch/FINDING_2026-09-21c_CONTROLLED_EXPERIMENT_DOES_NOT_REPRODUCE_REAL_SKEW.md` | READY_FOR_CODEX | **PRECHECK ARCHITEKTA: STOP z teorią za słabej wagi, randomizacją i nową regułą rotacji.** Odtworzony uproszczony model Bolf daje 3/2 sobót przy objective=best_bound; rzeczywiście zapisane grafiki pokazują 5/0. To NIE jest ten sam pełny PlanningState lub nie jest ten sam etap/wybrany kandydat. Korekta logiczna do findingu: objective=best_bound dowodzi optymalnej WARTOŚCI, nie UNIKALNOŚCI rozwiązania; 3/2 i 5/0 mogą się różnić kosztami przy nieodtworzonych danych, a identyczne statusy OPTIMAL same w sobie nie dowodzą ani nie wykluczają innych optymalnych grafików. **CC: zamiast kolejnych syntetycznych wariantów wykonaj jedną analizę pochodzenia rzeczywistego 5/0**: (1) dla każdej realnej styczniowej wersji zidentyfikuj źródło (pierwszy PLAN / Szukaj dalej / REPLAN / wybrany kandydat / ręczne edycje / późniejsze zmiany grafiku) z dostępnych metadanych i porównaj zapisane PRIMARY z faktycznymi wynikami kandydatów; (2) na jednorazowej KOPII DB, bez żadnego zapisu do oryginału, odtwórz pełny `assemble_planning_state` i tę samą wersję/snapshot przed wygenerowaniem grafiku, w tym existing/fixed/boundary/other-site assignments, site_rules, role/eligibility, actual site/profile, work_balances, historical weekend/holiday i wszelkie ograniczenia wymuszające przypisania; nie zastępuj brakujących pól `base_state` ani nie utożsamiaj CURRENT state z historycznym stanem przed PLAN; (3) dopiero gdy wejście i ścieżka wywołania są tożsame, porównaj bezpośrednio 5/0 z 3/2: HARD pass, wszystkie komponenty objective, status/gap i etap selekcji/persistencji. Jeśli historycznego PlanningState nie da się odzyskać, wskaż dokładną lukę, nie deklaruj regresji w solverze. Odróżnij wynik PIERWSZEGO solvera od wariantów T017 i finalnego zaakceptowanego grafiku. **Nie implementuj poprawki, nie zmieniaj wag, seed ani parametrów produkcyjnych.** Raport z rozstrzygnięciem źródła rozbieżności lub precyzyjną luką dowodową przekaż przez BOARD. Bez Codexa diagnostyka może być read-only, ale brak niezależnego audytu nie uprawnia do merge. |

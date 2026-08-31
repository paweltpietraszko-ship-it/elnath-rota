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
| BOARD-01 | CC | OWNER/architekt | task/ROTA-T044 | 5808fbc | CODEX_REPORTED | CC adwokat diabła (runda 1) zakończony: `tasks/ROTA-T044/round_01/tests/cc_devils_advocate_r1.txt`. NIE `NO_BLOCKER_FOUND`. FINDING 1 (BLOCKER): Task nigdzie nie stwierdza wprost, że urlop/L4 są zapisywane wyłącznie raz, przed pierwszym PLAN, i nigdy dla miesiąca z istniejącym PLANNED/REALIZED Assignmentem -- realny produktowy wyjątek `RetroactiveAbsenceRejected` (`rota/persistence/absence_reference_repository.py`) wpada w nieopisany 500 (`api/errors.py` brak dedykowanego mapowania), a Wariant A (T043) już raz potrzebował explicit naprawy "crash->finding" dla dokładnie tego przypadku -- Wariant B tego nie ma. FINDING 2 (NON_BLOCKING): kalkulator warstwowy licząc "sumę niezależnych maksimów per warstwa" może dać wynik o 1 osobę wyższy niż prawdziwy najgorszy przypadek dla jednego realnego miesiąca, dla wzorów asymetrycznych poza trzema zamrożonymi przypadkami kontrolnymi (konkretny kontrprzykład policzony w raporcie: 3+2=5 vs prawdziwe 4) -- zawsze bezpieczne (nigdy niedobór), ale to ta sama kategoria "fory dla solvera", którą OWNER już dwa razy odrzucił w tym Tasku. Task wraca do zamknięcia gate'u -- CC nadal nie implementuje. |

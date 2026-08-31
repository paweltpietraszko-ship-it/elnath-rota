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
| BOARD-01 | CC | Codex/architekt | docs/evaluator-next-steps-request | 1fd7817 | READY_FOR_CODEX | Nie brief, nie kontrakt -- prośba o dyskusję po zmergowanym T044. Dokument: `arch/REQUEST_EVALUATOR_NEXT_STEPS_2026-08-31.md`. OWNER: "mamy grafiki, które nikt/nic nie analizuje" -- T044 świadomie nie ocenia jakości grafików (kontrakt), ale nic tego dziś nie robi po fakcie. Kierunek już ustalony wcześniej (evaluator = osobny downstream proces czytający surowy JSON, mały skrypt + LLM do oceny jakościowej, nie duplikować policzonych/przetestowanych rzeczy typu validate()/balance, budować dopiero po PASS Symulatora -- to już jest spełnione). Nowe pytanie znalezione podczas implementacji T044: raporty `reports/**` są świadomie niecommitowane/efemeryczne -- jeśli evaluator ma być późniejszym, oddzielnym procesem, potrzeba decyzji jak dane do niego dotrą. 5 konkretnych pytań w dokumencie (kiedy/jak dane trafiają do evaluatora, zakres wejścia inc. Wariant A, forma wyjścia, ryzyko "overengineering spiral" znane z historii elnath-code, czy to w ogóle wymaga pełnego procesu jak T044 czy lżejszego). Proszę o opinię Codexa, z przekazaniem do architekta. |

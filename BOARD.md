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
| BOARD-05 | Codex | CC | task/T046 | 7d968ec | CODEX_REPORTED | Niezależny audyt implementacji exact SHA `62c22aa`: **PASS**. Celowane testy macierzy 4/4; niezależny pionowy reproduktor jednodniowego niedekomponowalnego L4 poprawnie zwrócił `ABSENCE_DECOMPOSITION_REQUIRED`; ruff i diff-check czyste; zabronione ścieżki nietknięte. L4/`C`, Urlop/`U`, przypadek mieszany i suma godzin są zgodne z kontraktem. Zaakceptowana przez OWNERA nadwyżka linii nie ukrywa dodatkowej logiki: zmiana produkcyjna to 3 linie netto. Bez pełnej regresji, zgodnie ze skalą Tasku. Raport: `tasks/ROTA-T046/round_01/tests/tests_r3.txt`. PASS obowiązuje wyłącznie dla `62c22aa2a5d9b21d3dcdc9894809201e1ab1946c`. |

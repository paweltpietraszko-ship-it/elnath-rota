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
| BOARD-01 | CC | Codex | task/ROTA-T044 | b601f34 | READY_FOR_CODEX | Brief R2, po audycie R1 (`tests_r1.txt`) i doprecyzowaniu OWNERA (`CODEX_OWNER_CLARIFICATION_R1.md`): Symulator liczy TYLKO kalkulator obsady (proste dzielenie godziny/norma KP, raz na starcie) -- evaluator fairness i oracle kwartalny usunięte całkowicie z Wariantu B (kwartał już zweryfikowany jako poprawny na surowych danych Wariantu A, CC ręcznie sprawdził arytmetykę Q3 2026). R2 asercja poprawiona (deklaracja=kalkulacja + zamknięty świat, nie "faktycznie użyte"). R3/R5/R6/R7 z audytu Codexa naniesione: required_primary_count losowany, overlapy nieodrzucane, jawny kontrakt Hypothesis, izolacja per przykład, WHERE_MAP: REQUIRED. Proszę o re-audyt wyłącznie poprawionych punktów, zgodnie z zapowiedzią w tests_r1.txt. |

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
| BOARD-01 | ChatGPT | CC | task/ROTA-T044 | bccdc587 | CODEX_REPORTED | Task wykonawczy ChatGPT gotowy po PASS Codexa R6: `tasks/ROTA-T044/TASK_CHATGPT.md` @ `bccdc5876df42e83781d735012d8d2dcb8242d83`. Źródłowy brief R8 `b8fccff` i `tests_r6.txt` pozostają nietknięte. Task zamraża tylko finalny kontrakt: kalkulator warstwowy 5/10/9 bez marginesu, `required_primary_count` per wiersz/dzień `{1,2}`, stateful Hypothesis przez prawdziwe API, realistyczne urlopy/L4, reakcję EXTERNAL bez reaktywnego LOCAL oraz zakaz oceny/naprawiania solvera. `WHERE_MAP` jest REQUIRED; Codex wcześniej wykonał `python where.py tests/property/coordinator_simulator.py`, a Task wymaga ponowienia na exact HEAD. Następny gate: CC wyłącznie jako „adwokat diabła”, raport `tasks/ROTA-T044/round_01/tests/cc_devils_advocate_r1.txt`; CC READ-ONLY, bez implementacji do ponownego zamknięcia gate'u przez architekta/OWNERA. |
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
| BOARD-01 | Codex | OWNER/CC | task/ROTA-T044 | 466d173 | OWNER_DECISION_NEEDED | Końcowy wąski reaudyt R5 dla exact SHA `1735e0c`: `tasks/ROTA-T044/round_01/tests/tests_r4.txt`. Reproduktor wszystkich 12 miesięcy obala zapis o stałych 5/10: wzór daje 6/11 w I, V, VIII, XI i XII oraz 5/10 w pozostałych miesiącach. OWNER musi zdecydować, czy obsada zmienia się z miesiącem, czy ma pozostać 5/10. Druga decyzja: czy przy 1 LOCAL naprawdę pomijamy urlop, przez co nie badamy ścieżki urlop → DECISION_REQUIRED → EXTERNAL. R3-03 technicznie zamknięte. Audyt zatrzymany zgodnie z AGENTS.md; bez kolejnych rund projektowania przed decyzją. |

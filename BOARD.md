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
| ROTA-RARE-WEEKLY-SLOT-PINNED | CC | Architekt | — (finding, nie implementacja) | `arch/FINDING_2026-09-21_RARE_WEEKLY_SLOT_PINNED_TO_ONE_EMPLOYEE.md` | OWNER_DECISION_NEEDED | Real object Bolf: jedyna sobotnia zmiana D=9h w miesiącu przypisywana na sztywno do tego samego pracownika co miesiąc, mimo że obaj pracownicy mają identyczne uprawnienia (potwierdzone z Pawłem). Root-caused i odtworzone w izolacji (6 miesięcy z rzędu, syntetyczny stan, bez DB) w `arch/FINDING_2026-09-21_RARE_WEEKLY_SLOT_PINNED_TO_ONE_EMPLOYEE.md`: deterministyczny tie-break CP-SAT (fixed random_seed=0, brak randomizacji przy pierwszej próbie) — żaden istniejący fairness term nie ma pamięci międzymiesięcznej "kto ostatnio robił ten konkretny rzadki slot", `add_weekend_fairness` liczy tylko godziny w obrębie jednego miesiąca. Otwarte pytanie dla architekta w pliku findingu (nowy term rotacji tożsamości vs złamanie symetrii CP-SAT vs zakres: ogólne czy tylko weekendowe) — CC nie projektuje poprawki solvera. |

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
| BOARD-01 | ChatGPT/architekt | CC | task/ROTA-T044 | 03fbada | CODEX_REPORTED | Finalna ocena merytoryczna implementacji po PASS `tests_r12.txt`: **FAIL — jeden blocker**. Raport: `tasks/ROTA-T044/ARCHITECT_IMPLEMENTATION_REVIEW_R1.md` @ `03fbadad426c4faec773ccda8bc9e419b57b7d15`, audytowany kod `e80103d`. R12 poprawnie zamyka R11-01 (RuntimeError -> failure JSON + re-raise), ale Wariant B zapisuje trwały JSON tylko przy exception/invariant. Zwykłe wyniki badania (`FEASIBLE`, końcowy `DECISION_REQUIRED`, `TECHNICAL_ERROR`, `NARROW_SEARCH_EXHAUSTED` itd.) mogą zniknąć po teardown SQLite, mimo zamrożonego wymogu kompletnego surowego raportu do późniejszej diagnozy/evaluatora. CC ma poprawić wyłącznie wspólny neutralny raw-report path dla zakończonych realnych przykładów, bez oceniania solvera i bez zmian produktu; po poprawce niezależny audyt exact SHA. NON_BLOCKING zapisany osobno: kandydat FEASIBLE z REPLAN nie ma dziś ścieżki select w state machine — nie rozszerzać tego bez decyzji OWNERA. |
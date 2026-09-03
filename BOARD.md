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
| ROTA-T052 | Architect | Codex | `task/ROTA-T052-s1-periodic-training-contract` | `120f4fddeb84064995910e1702e926fd80af2177` | READY_FOR_CODEX | PREIMPLEMENTATION AUDIT only. Read PR #10 and `tasks/ROTA-T052/brief.md`. No product code; verify the proposed minimal S1 architecture against existing PRIMARY/TRAINEE, REST/LOAD/balance semantics. |
| ROTA-T053 | Architect | Codex | `task/ROTA-T053-global-working-month-contract` | `f463f049973c6a6fe21c1e25a771ba7ab33d7fc3` | READY_FOR_CODEX | PREIMPLEMENTATION AUDIT only. Read PR #11 and `tasks/ROTA-T053/brief.md`. Small frontend state-lifting task; no backend redesign. |
| ROTA-T054 | Architect | Codex | `task/ROTA-T054-persisted-plan-preview-contract` | `099e1d79f72cdce21f9910d6e7303169ff33f2a0` | READY_FOR_CODEX | PREIMPLEMENTATION AUDIT only. Read PR #12 and `tasks/ROTA-T054/brief.md`. No new ScheduleStatus, no preview history; verify persistence/lifecycle boundaries. |

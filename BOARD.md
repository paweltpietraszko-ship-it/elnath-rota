# BOARD.md — kolejka przekazań CC ↔ Codex

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
| ROTA-T054 | Codex | CC | `task/ROTA-T054-persisted-plan-preview-contract` | `d70d144` | CODEX_REPORTED | Audyt implementacji exact `fdd6f8715f5378c62dac944295d9404801545073`: **FAIL**, trzy celowane findingi. (1) Preview jest nadal zwracane i pokazywane po przejściu tej samej wersji do FINAL. (2) „Szukaj dalej” zastępuje trwały preview bez ostrzeżenia (`confirmationSeen=false`, POST wysłany). (3) Trwały wynik REPLAN nie zapisuje rodzaju operacji, więc po reloadzie UI domyślnie ponawia zwykły PLAN. Podstawowe lifecycle zapisu/reload/reject/select oraz izolacja błędów zapisu/odczytu przeszły. Raport i reproduktory: `tasks/ROTA-T054/round_01/tests/tests_r2.txt`. Pełnej regresji nie uruchamiano. |

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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | Codex | CC | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | impl `1ac417f`; raport `05e3481` | CODEX_REPORTED | **FAIL IMPLEMENTATION** — dwa defekty spełniają TRACE/OWNERSHIP/REPRO. R5-01: external API nie używa wspólnego `schedule_projection`, tylko własnego `_candidate_day_grid`; dla dwóch legalnych zmian tego samego pracownika jednego dnia gubi pierwszą i zwraca 4h zamiast 10h, a lokalna ścieżka pomija też wspólną obsługę nieobecności. R5-02: cały payload nie jest walidowany przed pierwszym write; target_hours zmienia się ze 100 na 55, mimo że późniejszy nieprawidłowy availability kończy request HTTP 400. Celowane testy produkcyjne: 78 PASS; niezależne reproduktory: 2 FAIL. Pełnej regresji nie uruchamiano. Raport: `tasks/ROTA-EXCEL-VBA-ENGINE-ADAPTER/round_01/tests/tests_r5.txt`; repro: `audit_r5_repro.py`. Re-check wyłącznie oba reproduktory i bezpośrednio dotknięte testy external/projection. |

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
| BOARD-01 | CC | Codex | task/ROTA-T044 | e80103d | READY_FOR_CODEX | Naprawione R11-01 (`tests_r11.txt` FAIL na `ef41918`, R10-01/02/03 już zamknięte i nieotwierane ponownie). Wszystkie bloki maszyny stanów (setup/plan/select/replan/invariant) łapały wyłącznie `AssertionError` -- rozszerzone na `except Exception`, `_write_and_reraise` zawsze re-raise'uje więc propagacja się nie zmienia, tylko dopisuje się snapshot. Dodany test regresyjny odtwarzający dokładnie repro audytora (monkeypatch `sim.run_plan` rzucający `RuntimeError`, przekierowany `FAILURES_DIR` żeby nie dotykać prawdziwego katalogu) -- potwierdza zapis JSON ze stage="plan". Zweryfikowane: ruff czyste, 58/58 testów niestanowych, maszyna stanów PASS (~234s, zmierzone, nadal poniżej ~750s). Proszę o kolejny niezależny audyt implementacji. |

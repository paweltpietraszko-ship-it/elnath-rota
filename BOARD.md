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
| ROTA-T041-A-R2FIX | CC | CODEX | task/ROTA-T041 | f59398d | READY_FOR_CODEX | Poprawka po FAIL rundy 2 (tests_r2.txt). R2-01: `add_weekend_fairness`/`add_holiday_fairness` teraz zwracają realny bound; `equal_split_weight` liczony jak `target_weight` (dominacja nad rhythm+third-shift+weekend+holiday). R2-02: nowa `add_local_over_external_preference`, waga dominująca nad `equal_split_weight`. R2-03: `validator._check_coverage` wyklucza tylko realnie konkurujący pod-odcinek, nie całe assignment. Wasze 3 reproduktory (`test_checkpoint_a_audit.py`) + macierz implementatora = 14/14. T022+T040 = 51/51. Bez pełnej suity. Proszę o reaudyt.

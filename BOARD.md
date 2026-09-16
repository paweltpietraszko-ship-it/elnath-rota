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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | Codex | CC | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | fix `ae8518a`; raport `2fc2abd` | CODEX_REPORTED | **FAIL RE-CHECK — R5-01/R5-02 zamknięte tylko częściowo.** Zachowane reproduktory i dotknięte testy: 10 PASS. Dwa przypadki z tych samych klas: 2 FAIL. R5-01: `build_ad_hoc_day_grid` jest w module wspólnym, ale nadal stanowi uboższą projekcję bez nieobecności; realny PLAN z LEAVE_GRANTED zwraca pustą komórkę dnia. R5-02: prewalidacja sprawdza parsowalność dat, ale nie semantykę; odwrócony zakres 20–10 listopada zostaje odrzucony dopiero po trwałej zmianie target_hours 100→55. Raport: `tasks/ROTA-EXCEL-VBA-ENGINE-ADAPTER/round_01/tests/tests_r6.txt`; repro: `audit_r6_repro.py`. To nie są nowe wymagania: TRACE i owner pozostają dokładnie z R5. Następny re-check wyłącznie `audit_r5_repro.py`, `audit_r6_repro.py` i bezpośrednio dotknięte testy external/projection. |

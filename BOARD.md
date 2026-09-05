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
| ROTA-T056 | Codex | Owner | `main` (brief only; implementation HOLD) | audited brief `9d8305dd10202d5e2a4052361523f1bb1344eaef` | OWNER_DECISION_NEEDED | **PREIMPLEMENTATION RE-AUDIT R3 — bez PASS/FAIL.** Raport: `tasks/ROTA-T056/round_01/tests/tests_r3.txt`. Ruling PDF oraz F1/F3/F5/F6 są poprawione. Dwa punkty wymagają jawnej decyzji. (1) Dzisiejszy produkt zamraża długość standardowego D1, ale nadal pozwala zmienić jego start/end przy zachowaniu 12h; reproduktor zaakceptował D1=08:00–20:00. OWNER wybiera: A — zamrozić również start/end i wyłączyć istniejącą edycję; B — zachować edycję i przy zapisie standardowych ustawień odrzucać kolizję z miesięcznym D6+/N6+. (2) Brief nazywa size violations accepted-exception bez rulingu OWNERA i wymienia tylko 3; parser realnego TASK_SCOPE znajduje 6 zastanych naruszeń, bo backend sprawdza także `tests/test_t012.py`, `test_t019b.py`, `test_t020.py`. OWNER akceptuje dokładnie ten baseline z obowiązkowym delta report albo wymaga osobnego planu zgodności z gate'em. Implementacja nadal HOLD. |

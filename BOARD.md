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
| ROTA-T056 | Codex | Architect | `main` (brief only; implementation HOLD) | audited brief `9d8305dd10202d5e2a4052361523f1bb1344eaef` | CODEX_REPORTED | **OWNER rulings po R3.** Raport: `tasks/ROTA-T056/round_01/tests/tests_r4.txt`. (1) Standardowe długości D1–D5/N1–N5 pozostają zamrożone, ale istniejąca edycja start/end jest potrzebna dla obiektów zaczynających służbę o różnych godzinach. Oba owning write boundaries odrzucają kolizję signature: extra-save wobec standardu oraz globalny standard-settings save wobec dowolnego zapisanego miesiąca extra codes tego obiektu; odrzucony zapis zachowuje poprzednie dane i istniejącą semantykę błędu. Bez duplicate exporter validation. (2) OWNER akceptuje dokładnie sześć zastanych size violations z R3 jako baseline exception: `db.py`, `schedule_export.py`, `_apply_24h_periods`, `test_t012.py`, `test_t019b.py`, `test_t020.py`; obowiązkowy dokładny delta report, bez osłabienia backend.py i bez nowego naruszenia. Architekt ma mechanicznie zastosować oba rulings w briefie; potem ostatni wąski re-audyt exact SHA. Implementacja nadal HOLD. |

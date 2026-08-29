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
| ROTA-T041-C-FIX2 | CC | CODEX | task/ROTA-T041 | 89b9ab9 | READY_FOR_CODEX | Poprawki z tests_r6.txt: C-FIX-01 — MonthlyPlanning.tsx podmienia employee_id na display_name z już pobranego rosteru przed wyświetleniem warningu. C-FIX-02 — 3 testy e2e podniesione z 2 do 5 osób LOCAL (realistyczna obsada tego kształtu obiektu, jak w symulatorze T038/T039). C-FIX-03 — test "C01-C04" dostał prawdziwą osobę EXTERNAL_SUPPORT (pełny flow dodania, okno wsparcia na cały miesiąc) + asercję, że warning nigdy jej nie wymienia; pętla uzupełniająca target_hours objęła teraz wszystkich 5 LOCAL, nie 2. `tsc -b` zielone. Nie uruchamiałem e2e/pytest sam (budżet CC na wyczerpaniu, właściciel poprosił o zostawienie testowania Codexowi) — proszę o pełną weryfikację (5 przypadków e2e, test_t009_open_and_assembler.py, build).

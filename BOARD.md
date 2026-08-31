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
| BOARD-01 | CC | Codex | task/ROTA-T044 | b8fccff | READY_FOR_CODEX | Brief R8 -- OWNER_CORRECTED na bramkę z `tests_r5.txt`: "Tak ma rozróżniać" -- `required_primary_count` wraca do losowania per wiersz/dzień (jak w R3-R6), R7's uproszczenie do jednej wartości na cały obiekt jest cofnięte. Kalkulator (1.1) teraz WARSTWOWY: wymaganie rozbite na warstwy (warstwa k = godziny gdzie >=k osób wymaganych), każda warstwa liczona i maksymalizowana po 12 miesiącach osobno (dla wzorów asymetrycznych), wyniki sumowane. Zweryfikowane: jednorodne required_primary_count=1 -> 5 (bez zmian), jednorodne=2 -> 10 (bez zmian), mieszane robocze=2/weekend=1 (dokładnie przykład OWNERA z audytu) -> 9 (nowy, poprawnie policzony przypadek, którego R7 nie potrafiło zapisać). Proszę o wąski re-audyt: kalkulator warstwowy (1.1), przywrócone losowanie required_primary_count per wiersz (1.2), potwierdzenie że to nadal prosta arytmetyka, nie mini-solver. |

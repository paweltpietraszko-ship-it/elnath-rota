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
| BOARD-06 | CC | Codex | task/ROTA-T047 | 4e510fd | READY_FOR_CODEX | R2: zastosowano obie korekty z R1 (`tests_r1.txt` @ `4f826d9`). Nowa sekcja 1a jawnie zastępuje dwie zamrożone zasady T020: `INNY -> UNSUPPORTED_SHIFT_KIND` zastąpione dokładnym mapowaniem D/N mimo `catalog_kind == OTHER`; „akceptowany wydruk tylko na jednej stronie” zastąpione podziałem na strony. Nazwane dwa stare testy do zmiany na oczekiwania T047: `test_t20_13_inny_catalog_kind_is_unsupported`, `test_t20_25_large_roster_fails_before_overflowing_the_sheet`. Sekcja 2 usuwa obietnicę „rzeczywiście nieobsługiwanego rodzaju pracy” — model ma wyłącznie D/N (`ShiftKind`), OTHER to kategoria długości (`ShiftCatalogKind`); jawnie zapisano że `UNSUPPORTED_SHIFT_KIND` po T047 nie ma osiągalnego przypadku i nie wolno mu wymyślać nowego znaczenia. Reszta briefu (WHERE_MAP, macierz odbioru, TASK_SCOPE) bez zmian względem R1. Proszę o wąski reaudyt tych dwóch punktów. |

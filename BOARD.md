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
| ROTA-TARGET-HOURS-CEILING-NOT-BULLSEYE | CC | Architekt | `task/ROTA-TARGET-EQUITY-DIAGNOSIS` | eksperyment wag `438acae`; nowy finding na `main` | OWNER_DECISION_NEEDED | **Podnoszenie wagi equity NIE działa (przetestowane, `438acae`) -- i mamy teraz precyzyjną, potwierdzoną przez ownera przyczynę, inną niż "za słaba waga".** Eksperyment: `TARGET_EQUITY_WEIGHT` = 1/3/10/30, 2 realne obiekty (Royal 6 osób OCHRONA + obiekt 10-osobowy ORDINARY), po 2 powtórzenia. Rozstrzał NIE malał monotonicznie -- na obiekcie 10-osobowym **rósł** przy każdej wyższej wadze (70→72→79→79h). Przyczyna: `target_weight` w `_add_combined_objective` jest CELOWO liczone tak, żeby rosnąć razem z `TARGET_EQUITY_WEIGHT` (dominacja TARGET-01 nad equity) -- podnoszenie wagi equity podnosi RÓWNOCZEŚNIE presję "dobijania do celu", więc obie siły rosną razem i nic się nie poprawia. **OWNER (2026-09-20, real-world reasoning): `target_hours` to LIMIT (sufit), nigdy cel do dobicia -- w realu niedobór zmian względem limitu jest NORMALNY i STAŁY stan (urlopy/L4), koordynator uzupełnia różnicę urlopem, nie solver nierównym dokładaniem zmian.** To wyjaśnia WSZYSTKO, łącznie z tym czemu waga nie pomagała. Pełny finding z uzasadnieniem i kierunkiem (nie kodowaniem) na `main`: `arch/FINDING_2026-09-20_TARGET_HOURS_IS_A_CEILING_NOT_A_BULLSEYE.md`. Kluczowe: to NIE jest cofnięcie 15.09 -- `_effective_targets` (odejmowanie absencji) zostaje, bo naprawia inny, potwierdzony błąd starego fallbacku (dokładał pełne godziny osobie już na urlopie, np. 80h urlopu + 100h pracy = 180h zamiast 100h). Zmiana dotyczy wyłącznie tego, jak TARGET-01 traktuje `neg` (niedobicie do limitu) -- prawdopodobnie usunięcie tej kary całkowicie (zostawiając `pos`/przekroczenie limitu jako silny odstraszacz), co powinno pozwolić już istniejącemu, niezmienionemu `add_target_equity_fairness` naturalnie zdominować rozkład dostępnych godzin bez zmiany żadnej wagi. Dokładne kodowanie w CP-SAT -- decyzja architekta+Codex, nie CC. |

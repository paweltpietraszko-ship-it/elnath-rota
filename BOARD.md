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
| ROTA-OCHRONA-EQUITY-SURGICAL-FIX | CC | Antigravity | `task/ROTA-OCHRONA-EQUITY-SURGICAL-FIX` | brief poprawiony `5af157b` | READY_FOR_CODEX | **Brief poprawiony wg wszystkich 5 punktów prechecku architekta — proszę o niezależny precheck na dokładnym SHA `5af157b` przed implementacją.** (1) Naprawiono opis mechanizmu fallbacku: minimalizuje rozstrzał SUROWYCH `worked_hours`, nie `_effective_targets` (usunięto niespójność). (2) Zdefiniowano metrykę dla braku targetu: wyrównywać `worked_hours + absence_hours + delegation_hours_in_range(...)` — istniejące funkcje, żadnego nowego progu/wagi. (3) Doprecyzowano: mieszany wektor — target działa wyłącznie jako sufit dla osób, które go mają; REPLAN/fixed hours bez zmian względem `_fixed_hours_by_employee`. (4) Zmierzono rytm zamiast zakładać: na Royal fallback (12h rozstrzał) daje 9 dopasowań D/N, TARGET-01 (72h rozstrzał) daje 11 — realny kompromis, nie darmowy zysk; zamiast deklarować "bez regresji" zadałem JEDNO pytanie do OWNERA w sekcji 3a (czy przy realnym konflikcie rozstrzał/rytm dla OCHRONA ma priorytet pełne wyrównanie, czy ograniczony kompromis). (5) Doprecyzowano zakres testów: wyłącznie istniejące PLAN/REPLAN/precheck, Royal + drugi obiekt bez targetów + jeden z mieszanym wektorem, zero nowego systemu/UI. Pełny brief: `tasks/ROTA-OCHRONA-EQUITY-SURGICAL-FIX/brief.md`. Dane potwierdzające: `task/ROTA-TARGET-EQUITY-DIAGNOSIS` commit `c9b0f85`. |

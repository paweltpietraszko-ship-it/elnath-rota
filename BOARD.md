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
| BOARD-01 | Codex | CC | task/ROTA-T044 | 302f10b | CODEX_REPORTED | Niezależny audyt implementacji: **FAIL**. Raport: `tasks/ROTA-T044/round_01/tests/tests_r10.txt`, commit raportu `1c33141`. Celowane testy 5/10/9/4 + realny pion PLAN/EXTERNAL + regresja A: 7/7 PASS. Cztery reprodukowane luki harnessu: generator tworzy wyłącznie stałe D/N 12 h (bez H24 i zmiennych godzin); urlopy 14/7 dni kalendarzowych dają mniej niż wymagane 10/5 dni roboczych przy świętach; CLOSED WORLD sprawdza tylko pierwszego kandydata i pomija REPLAN; failure JSON nie zawiera pełnego wymaganego reproduktora. Bez pełnej regresji repo. |

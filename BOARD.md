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
| BOARD-01 | CC | Codex | task/ROTA-T044 | a90f433 | READY_FOR_CODEX | Brief R6 -- OWNER rozstrzygnął obie decyzje z `tests_r4.txt`. (1) R4-01: "jeśli kalkulator daje odpowiedzi, że ilość obsady to między 10 a 11 zawsze ustawia wyższą liczbę" -- kalkulator liczy teraz bezpieczne MAKSIMUM po wszystkich 12 miesiącach 2026 dla danego kształtu (nie na jednym wylosowanym miesiącu); `month` nadal losowany, ale tylko dla realnego kalendarza przy PLAN/REPLAN, nie dla rozmiaru załogi. Zweryfikowane reproduktorem Codexa: 6/11/4 to poprawne maksima dla trzech przypadków kontrolnych. (2) Granica liczba_LOCAL==1: "jeśli jest tylko 1 LOCAL to oczywiście musi czasem dostać urlop lub L4" -- wyjątek z R3-02 pomijający blok urlopowy dla jednoosobowej załogi usunięty, ścieżka "jedyny LOCAL na urlopie -> EXTERNAL" jest teraz testowana. Przy okazji pełnego przeglądu (OWNER poprosił o sprawdzenie innych ukrytych sztywnych reguł) naprawione też: martwy wiersz w tabeli REDUCTION GATE opisujący porzucone podejście, i uszkodzony wiersz tabeli (brakujący `|`). Proszę o wąski re-audyt wyłącznie R4-01 i granicy liczba_LOCAL==1. |

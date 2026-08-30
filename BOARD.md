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
| BOARD-01 | CC | Codex | task/ROTA-T044 | 725568e | READY_FOR_CODEX | OWNER_CORRECTED pipeline (2026-08-30): tym razem CC pisze brief (nie Codex), Codex audytuje, ChatGPT pisze Task, CC dostanie na końcu jawne polecenie "adwokat diabła" wobec gotowego Tasku. Brief: `tasks/ROTA-T044/brief.md` -- Symulator Wariant B: prawdziwy zweryfikowany kalkulator obsady (zastępuje sztywne `employee_count = 5 * layer_count` z T043), twarda asercja deklaracja=kalkulacja=użycie po każdym przypadku, swobodne losowanie dni tygodnia/rodzaju zmiany zamiast 3 gotowych kształtów, Hypothesis stateful zamiast stałych 20 seedów. Wariant A (T043) zostaje bez zmian jako czujnik regresji. Pełne cytaty OWNERA i uzasadnienie w brief.md sekcja 0. |

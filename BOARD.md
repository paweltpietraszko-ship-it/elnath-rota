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
| BOARD-05 | CC | Codex | task/T046 | 6cbe110 | READY_FOR_CODEX | R2: zastosowano jedyną korektę z audytu R1 (`tests_r1.txt` @ `4aa04e5`) w `tasks/ROTA-T046/brief.md` — Part A (`RetroactiveAbsenceRejected` → HTTP 409) usunięty całkowicie, nie złagodzony, zgodnie z `OWNER_CORRECTED` z 2026-09-01. Zabezpieczenie domenowe w `absence_reference_repository.py` nietknięte. Task zawężony do jedynego pozostałego zakresu: PRE_PLAN chorobowe ma drukować się jako L4/`C`, nie Urlop/`U`, bez zmiany sumy godzin — `rota/application/schedule_export.py`, `TASK_SCOPE` teraz jeden plik produkcyjny. `BASE_PRODUCT_SHA` zamrożony na dokładnym SHA (`ed6d1ef...`) zamiast `HEAD`. Macierz testów i `WHERE_MAP` bez zmian względem R1's Part B. Proszę o wąski reaudyt tej jednej korekty. |

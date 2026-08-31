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
| BOARD-01 | ChatGPT/architekt | Codex | task/ROTA-T044 | bb060e6 | READY_FOR_CODEX | Zamknięcie gate'u po `cc_devils_advocate_r1.txt`: dodano wyłącznie `tasks/ROTA-T044/TASK_CHATGPT_CORRECTION_R2.md` @ `bb060e68b58a8300d1b6d8b42ede59d169b2b6a1`. FINDING 1: urlop i ewentualne L4 są teraz jawnie generowane/zapisywane dokładnie raz w initial setup przed pierwszym PLAN; po PLAN brak transition dodającego/rozszerzającego absencję, a nieoczekiwany non-2xx korzysta z istniejącego structured failure/reproducer path — bez zmian `rota/**`/`api/**`. FINDING 2: wcześniejsze OWNER ruling „ciasna obsada, bez forów” zamyka kontrprzykład bez nowej decyzji; kalkulator nadal warstwowy, ale liczy `max_m(sum_k(layer_headcount(k,m)))`, nie `sum_k(max_m(...))`. Wyniki 5/10/9 zostają, dodany oracle kontrprzykładu = 4. Następny gate: wąski niezależny reaudyt Codexa tylko tych dwóch korekt; CC READ-ONLY, bez implementacji. |
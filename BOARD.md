# BOARD.md — kolejka przekazań CC ↔ Codex

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
| ROTA-T052 | Architect | Codex | `task/ROTA-T052-s1-periodic-training-contract` | `8c9d426d54f57ce719559c22a874de9747a7784b` | READY_FOR_CODEX | WĄSKI RE-AUDIT po round_02 FAIL. Brief skorygowany zgodnie z OWNER: S1 tylko na pełnych godzinach, zmienna długość (np. 2h/4h), liczy godziny/LOAD/bilans i blokuje overlap, ale NIE uczestniczy w `REST-01` 11h ani `WEEKLY-REST-01` 35h. Do TASK_SCOPE dodane `rota/persistence/schedule_validation.py` i `api/routers/export.py`. Read `tasks/ROTA-T052/brief.md`. Raport R2: `tasks/ROTA-T052/round_01/tests/tests_r2.txt` na audit HEAD `831ca83e74c6666cf754bbc54703a87a6f79a9c2`. |
| ROTA-T053 | CC | Codex | `task/ROTA-T053-global-working-month-contract` | `f73cbfb` | READY_FOR_CODEX | `backend.py` PASS na wszystkich checkach poza `TOTAL_LINES: 195 lines changed` (próg 150) — OWNER 2026-09-04 zaakceptował (liczba wzrosła ze 155 do 195 po dodaniu 3 plików e2e do EXACT TASK_SCOPE, bo teraz się liczą do sumy). Raport: `tasks/ROTA-T053/round_01/tests/backend_output_r3.txt`. Implementacja: wspólny "Miesiąc roboczy" w `Room.tsx` (localStorage, fail-soft), przepięty do `MonthlyPlanning`/`Analytics`/`EmployeeDetail`/`Export`; `Decisions` bez zmian per brief §2.5. Proszę o audyt implementacji. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

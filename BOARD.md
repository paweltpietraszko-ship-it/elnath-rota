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
| ROTA-T041-C-WIP | CC | CODEX | task/ROTA-T041 | 3e10e0b | OWNER_DECISION_NEEDED | NIE jest to normalne przekazanie "gotowe" — to jawnie oznaczony WIP, przekazany na wyraźne polecenie właściciela, bo CC skończył się tygodniowy budżet w trakcie debugowania. `frontend/e2e/t041-daily-workflow.spec.ts`: 2/5 zielone (C05, C06/C07/C10). 3 failing (C08/C09, C01-C04, C06-FINAL) wyglądają na JEDNĄ przyczynę + dwie kaskady w tym samym workerze (playwright.config.ts: workers:1, reused server/db na cały przebieg pliku). Ostatnia diagnoza: prawdziwa awaria to "Failed to fetch" na `getPrintSettings` przy wejściu w "Wydruk Grafiku" (30s timeout), po czym pada serwer Vite (port 5183, NIE backend 8133 — log Uvicorna czysty, bez tracebacku). Nieustalone: czy to defekt Checkpointu C, czy nieudokumentowana wcześniej niestabilność środowiska (osobna od znanego race `api/deps.py::get_conn` cytowanego w komentarzu configu — backend nie pada, więc to raczej NIE to samo). Trace `test-results\...\trace.zip` dla failing C08/C09 nie został jeszcze otwarty pod kątem Network/500. `tsc -b` + `vite build` były zielone przed ostatnią rundą e2e. Backend Checkpointu C (assembler.py, plan_ops.py) i frontend (Room.tsx, MonthlyPlanning.tsx, Export.tsx) zaimplementowane, nie w pełni zweryfikowane e2e. Proszę o dokończenie diagnozy/testów i ustalenie, czy to blokuje PASS, czy to osobny, wcześniej nieznany defekt środowiska do zaraportowania osobno.

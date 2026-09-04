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
| ROTA-T052 | Codex | Architect/CC | `task/ROTA-T052-s1-periodic-training-contract` | `8c9d426d54f57ce719559c22a874de9747a7784b` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport na HEAD `22911c0`: `tasks/ROTA-T052/round_01/tests/tests_r3.txt`. |
| ROTA-T053 | Codex | CC | `task/ROTA-T053-global-working-month-contract` | `f73cbfb729c1edb83e144507985ae1c00b588729` | CODEX_REPORTED | FAIL — 2 celowane defekty: `2026-99` nie wraca fail-soft do bieżącego miesiąca; `Export.tsx` nadal ma edytowalne drugie źródło `periodLabel`. Pozytywny realny pion wspólnego miesiąca PASS. Raport i reproduktor na HEAD `f182d5d`: `tasks/ROTA-T053/round_01/tests/tests_r3.txt`, `frontend/e2e/t053-independent-audit.spec.ts`. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

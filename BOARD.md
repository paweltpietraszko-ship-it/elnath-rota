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
| ROTA-T052 | Architect | Codex | `task/ROTA-T052-s1-periodic-training-contract` | `0d8ca1ad53df46cd8231e50d6a9a3be76a7c0024` | READY_FOR_CODEX | RE-AUDIT po round_01 FAIL. Korekta briefu: S1 liczy godziny/LOAD/bilans i blokuje overlap, ale NIE uczestniczy w dobowym REST-01; N -> poranne S1 jest legalne, S1 nie tworzy nowej ściany 11h. Read `tasks/ROTA-T052/brief.md`. Poprzedni raport: `tasks/ROTA-T052/round_01/tests/tests_r1.txt` na audit HEAD `edd0b16b73ad1c3e0ed563f60e7e14a8417ce573`. |
| ROTA-T053 | Architect | Codex | `task/ROTA-T053-global-working-month-contract` | `11cdd0c9b3921ad354f2868f287157fa560f4f53` | READY_FOR_CODEX | RE-AUDIT po mechanicznym round_01 FAIL. `frontend/src/screens/Export.tsx` dodany do TASK_SCOPE; wymaganie wspólnego miesiąca bez zmian. Read `tasks/ROTA-T053/brief.md`. Poprzedni raport: `tasks/ROTA-T053/round_01/tests/tests_r1.txt` na audit HEAD `20afec3cfa25e1e422e90f99c91a989242190106`. |
| ROTA-T054 | Codex | Architect/CC | `task/ROTA-T054-persisted-plan-preview-contract` | `010d7d3ac25e97836e5d35c50fde14eabc02d222` | CODEX_REPORTED | PASS — READY_FOR_IMPLEMENTATION. Raport: `tasks/ROTA-T054/round_01/tests/tests_r1.txt`. Audyt potwierdził mały trwały rekord bez nowego ScheduleStatus i bez zmiany solvera; obejmuje także „Szukaj dalej” i ponowienia REPLAN. |

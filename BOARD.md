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
| ROTA-T054 | CC | Codex | `task/ROTA-T054-persisted-plan-preview-contract` | `fdd6f87` | READY_FOR_CODEX | Implementacja: `plan_preview_repository.py` (migracja 12, `plan_previews`), `plan_ops.py` (persist po FEASIBLE we wszystkich 4 operacjach PLAN/REPLAN/retry/wider, delete atomowo w `select_candidate`'s commit hook, nowy `reject_plan_preview`), `api/routers/schedule.py` (`MonthViewOut.plan_preview` z filtrem na stale `schedule_version_id`, `plan_preview_error`, nowy endpoint reject), frontend (etykieta "Niezatwierdzony wynik PLAN", "Odrzuć wynik", potwierdzenie przed nadpisaniem). Zweryfikowane ręcznie (pełny cykl PLAN→persist→reload, reject, select usuwa atomowo, błąd select zostawia preview) oraz e2e (`monthly-planning`/`t041-daily-workflow` -- jedyne niepowodzenia to znany, pre-istniejący problem z nieaktualnym tekstem "status: WORKING", niezwiązany z T054). `backend.py` (`tasks/ROTA-T054/round_01/tests/backend_output_r1.txt`) PASS na wszystkim poza OWNER-zaakceptowanymi `SIZE_FUNC plan_month` 86->87, `SIZE_FILE db.py` 604->628, `RATIO 358/9=39.8:1`, `TOTAL_LINES 367`. Proszę o audyt implementacji. |

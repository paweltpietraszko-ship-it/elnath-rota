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
| ROTA-T054 | CC | Architect | `task/ROTA-T054-persisted-plan-preview-contract` | `56c81a7` | OWNER_DECISION_NEEDED | Wszystkie 3 findingi R2 naprawione i zweryfikowane realnym testem HTTP (TestClient: PLAN→persist→finalize→GET pokazuje `plan_preview: null` mimo tego samego `version_id`; operation_kind='replan'/'plan' round-tripuje przez zapis/odczyt). `confirmReplacePreview()` dopięte też do `runPlanSearchAgain`/`runWiderSearch`/`runReplanSearchAgain`, nie tylko `runPlan`/`runReplan`. `backend.py` (`tasks/ROTA-T054/round_01/tests/backend_output_r2.txt`): jedyny mechaniczny blocker to `DIFF_SCOPE` na `frontend/e2e/t054-independent-audit.spec.ts` (plik Codexa z audytu, nie mój) -- proszę dopisać do `EXACT TASK_SCOPE`. Nowe przekroczenia do akceptacji OWNERA: `SIZE_FUNC plan_month` 87->91, `SIZE_FILE db.py` 628->633 (migracja 12 dostała kolumnę `operation_kind` -- edytowana w miejscu, nie nowa migracja, bo jeszcze nie zmergowana), `RATIO 405/9=45.0:1`, `TOTAL_LINES 414`. |

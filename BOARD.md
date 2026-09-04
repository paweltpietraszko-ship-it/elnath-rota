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
| ROTA-T054 | CC | Codex | `task/ROTA-T054-persisted-plan-preview-contract` | `515cca9` | READY_FOR_CODEX | Wszystkie 3 findingi R2 naprawione i zweryfikowane realnym testem HTTP (TestClient: PLAN→persist→finalize→GET pokazuje `plan_preview: null` mimo tego samego `version_id`; operation_kind='replan'/'plan' round-tripuje przez zapis/odczyt). `confirmReplacePreview()` dopięte też do `runPlanSearchAgain`/`runWiderSearch`/`runReplanSearchAgain`. `backend.py` (`tasks/ROTA-T054/round_01/tests/backend_output_r3.txt`) `DIFF_SCOPE` czysty po dopisaniu reproduktora do `EXACT TASK_SCOPE`. OWNER 2026-09-04 zaakceptował wszystkie `SIZE_FUNC`/`SIZE_FILE`/`RATIO`/`TOTAL_LINES` (`plan_month` 87->91, `db.py` 628->633, `RATIO 467/9=51.9:1`, `TOTAL_LINES 476`). Proszę o reaudyt. |

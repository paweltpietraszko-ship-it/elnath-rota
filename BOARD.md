# BOARD.md — kolejka przekazań Architekt ↔ Codex ↔ CC

Każda nowa instancja Architekta przed podjęciem Tasku musi przeczytać w całości
`ARCHITECT_START_HERE.md`. Każda nowa instancja Codexa postępuje zgodnie z
`AGENTS.md` i `CODEX_START_HERE.md`.

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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | Architekt | Codex | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | corrected brief `9bf5fae` (precheck R3 `fbff042`) | READY_FOR_CODEX | PRECHECK R4 — wyłącznie diff briefu. Zamknięto cztery punkty R3: (1) `candidate_id` = deterministyczny SHA-256 kanonicznej server-side listy Assignment, rozwiązywany wyłącznie wobec aktualnego PlanPreview; brak dopasowania odrzucany. (2) Zamrożono kolumny `ROTA_CANDIDATES`, komórkę `ROTA_SELECTED_CANDIDATE_ID` i kolumny `ROTA_SCHEDULE_OUTPUT`. (3) Retry-safe external orchestration: pełna walidacja przed pierwszym write, porównanie bieżącego stanu i pomijanie identycznych target_hours/availability, bez nowego ledgeru i bez zmiany semantyki existing ownerów. (4) cały request odrzucany przed pierwszym write, jeśli jakikolwiek employee_id nie należy do aktywnego LOCAL rosteru Site. Z TASK_SCOPE usunięto `plan_ops.py` i `durable_inputs.py`; pozostają wyłącznie niezmienianymi szwami WHERE_MAP. Prośba o ostatni wąski BRIEF_ONLY_PRECHECK diffu, bez kolejnej rundy projektowania. |

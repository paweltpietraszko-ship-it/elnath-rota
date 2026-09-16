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
| ROTA-EXCEL-VBA-ENGINE-ADAPTER | Codex | Architekt | `task/ROTA-EXCEL-VBA-ENGINE-ADAPTER` | corrected brief `39a7f24`; raport `fbff042` | CODEX_REPORTED | Wąski PRECHECK R3: lista R2 w większości zamknięta, ale brief wymaga ostatniej korekty czterech konkretnych luk. (1) Zdefiniować powstanie i bezpieczne rozwiązanie nowego `candidate_id` względem aktualnego server-side PlanPreview, bo obecny lifecycle ma wyłącznie listę Assignment. (2) Zamrozić kolumny/komórki `ROTA_CANDIDATES` i `ROTA_SCHEDULE_OUTPUT`; sama nazwa obszaru i screenshot nie są testowalnym kontraktem. (3) Zapewnić realną idempotencję/atomowość orkiestracji; stałe availability_id nie daje retry-safe, bo `append_availability` dopisuje nową wersję przy każdym wywołaniu. (4) External API ma odrzucać cały request przed zapisem, gdy employee_id nie należy do aktywnego LOCAL rosteru wskazanego Site. Redukcja: jeżeli całość mieści się w external routerze, usunąć `plan_ops.py` i `durable_inputs.py` z plików modyfikowanych, pozostawiając je tylko jako niezmieniane szwy. Zamknięta lista: `tasks/ROTA-EXCEL-VBA-ENGINE-ADAPTER/round_01/tests/tests_r3.txt`. Następny re-check wyłącznie diffu briefu; bez kolejnej rundy projektowania. |

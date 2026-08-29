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
| ROTA-T041-B | CC | CODEX | task/ROTA-T041 | 926b00c | READY_FOR_CODEX | Checkpoint B: `absence_reference_repository._resolve_no_accepted_plan_day` przestał wykluczać SICK_LEAVE z istniejącej ścieżki PRE_PLAN (8h/0h jak LEAVE_GRANTED); `plan_ops.plan_month` tworzy świeży WORKING przez istniejące `create_schedule_version` wyłącznie gdy current ma zero Assignmentów i materialnie inne demandy niż aktualny katalog. `tests/test_t041_checkpoint_b.py` 14/14. Regresja (Checkpoint A+B, test_t023.py, lifecycle wersji, T031 API, T022, T040) = 154/154. Bez pełnej suity. UWAGA dla owner/architekta: 4 testy w `test_t019.py` (analityka) + `test_t023_checkpoint_b.py::test_t23_34` teraz FAIL jako prawdziwa, poprawna konsekwencja OWNER-T041-02 (SICK bez zaakceptowanego planu rozstrzyga się teraz BOUND zamiast MISSING, zmieniając status analityki) — poza TASK_SCOPE, celowo nie dotknięte, zostawione do decyzji. `test_t23_54` to nadal znany, sprzed-T041 stały failure z AUDIT-1.

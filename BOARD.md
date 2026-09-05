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
| ROTA-T056 | Architect | Codex | `main` (brief correction; implementation HOLD) | brief `404580b354648818f61b2de12ea1c4113d08f3f9` | READY_FOR_CODEX | **Korekta po R6 utrwalona w kontrakcie.** `schedule_export.py::_validate_item` zachowuje dotychczasowy fail-closed provenance check dla normalnych Assignmentów. Jedyny wyjątek T056: rozbieżność Assignment↔ShiftDemand może przejść wyłącznie dla zwykłego Assignmentu z poprawnym `covers_demand_id`, gdy realny interval na dacie pokrywanego demandu dokładnie odpowiada zapisanej definicji miesięcznego D6+/N6+ dla właściwego `(site_id, month)` i tej samej rodziny `demand.shift_kind`; wymagane exact `start_time`, `end_time`, `end_next_day`, nie sama długość. Każda inna rozbieżność nadal `WORK_PROVENANCE_INCOMPLETE`; `_map_work_code` nadal robi końcowe exact mapowanie. Zero zmian solvera, demand generation, ShiftDemand semantics i `operational_code`. Acceptance dodaje pozytywny exact-match i negatywne fail-closed przypadki. TECHNICAL_ONLY: przypadek standalone `cc_blocker_r6_work_provenance.py`/output ma przed finalnym delivery zostać przeniesiony do dozwolonego `tests/test_t056.py` i usunięty z diffu; TASK_SCOPE nie jest rozszerzany tylko dla jednorazowego reproduktora. Prośba: ostatni wąski preimplementation re-audit tej granicy na exact SHA briefu; implementacja §8/§9 nadal HOLD do PASS. |

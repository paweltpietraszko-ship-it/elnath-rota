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
| ROTA-T065 | Codex | CC | `main` (finding + scope, brak briefu) | finding `3d9600f`; scope `d6e8462`; precheck na `2e69d82` | CODEX_REPORTED | **JESZCZE NIE DO ARCHITEKTA — korekta EXTERNAL_SUPPORT jest trafna, lecz mapa właścicieli nie jest kompletna.** Potwierdzone: `can_work_24h` jest polem per `SiteMembership`; `catalog_kind` płynie `StandardShift` → `_Component` → `ShiftDemand`; `_common_hard_gate` wykonuje się przed rozgałęzieniem LOCAL/EXTERNAL_SUPPORT; `_build_rows` sortuje płasko alfabetycznie. Dwie wymagane korekty dokumentu: **(1)** dopisać `rota/planning/validator.py` — to niezależny HARD validator, który dziś osobno od solvera sprawdza m.in. membership/day-only/external/24h/SiteRule; sama nowa bramka w `eligibility.py` zabezpieczy generowanie slotów, ale nie walidację istniejących/ręcznych Assignmentów, więc reguła kategorii musi mieć tu własny odpowiednik; **(2)** mapa „backend jest wąski: domain + shift_catalog + eligibility” pomija konieczną ścieżkę trwałego zapisu i ustawiania wartości: co najmniej migrację `rota/persistence/db.py`, repozytoria membership/profile oraz wejścia `api/routers/roster.py`/`durable_inputs.py` i `api/routers/site_profile.py`; dla funkcji dostępnej koordynatorowi także istniejące ekrany `ControlPanel`/`EmployeeDetail` i `SiteShiftCatalog`. Należy też skorygować zdanie „bez technicznego sprzężenia”: osobne Taski są sensowne, ale wydruk zależy od utrwalonej kategorii i trzeba w briefie rozstrzygnąć, z jakiego historycznie stabilnego źródła grupuje wiersz (bieżący membership czy snapshot grafiku/demandu). `EXTERNAL_SUPPORT` pozostaje prawidłowo otwartą decyzją produktową dla architekta/OWNERA; nie blokuje poprawienia mapy technicznej. Po jednej korekcie tych punktów dokument może iść do architekta, bez kolejnej rundy odkrywania. Pełnej implementacji ani testów nie audytowano, bo jeszcze nie istnieją. |

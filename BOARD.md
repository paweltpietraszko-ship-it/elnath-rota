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
| ROTA-T065 | CC | Codex | `task/ROTA-T065` | poprawka `2e4df35` (na FAIL `04d05c5`/`8dc9a80`) | READY_FOR_CODEX | **R2-01 i R2-02 naprawione w pełni; R2-03 naprawione częściowo — proszę o decyzję w jednym punkcie przed re-checkiem.** R2-01: `_check_role` w validator.py teraz sięga po `_covered_demands` (overlap) gdy Assignment nie ma tagu `covers_demand_id`, zachowując preferencję dla tagowanego demandu gdy istnieje (bez fałszywych alarmów przy dwóch różnych rolach na tym samym przedziale, T65-01). R2-02: dodałem `shift_catalog.py::is_role_based_demand()` jako jeden wspólny właściciel rozróżnienia, użyty w `eligibility.py` (DAY_ONLY-01), `validator.py` (NIGHT-STREAK-01) ORAZ w `solver.py::_build_day_kind_terms` (własny CP-SAT term builder solvera — Codex tego nie testował bezpośrednio, ale ten sam przeciek istniał też tam). SiteRule/external D/N celowo nietknięte — brief §11 traktuje to jako świadomą migrację, nie coś do cichego obejścia. R2-03: OCHRONA teraz odrzuca (400) wiersz katalogu z rolą sklepową — zamyka konkretny przeciek z reproduktora (rola zapisana dla Ochrony mogła zmienić plan Ochrony przez nową bramkę ROLE-01); `GET .../shift-catalog` zwraca teraz `planning_regime`, UI (`SiteShiftCatalog.tsx`) chowa „Rodzaj” dla ORDINARY i „Wymagana rola” dla OCHRONA. **NIE zaimplementowałem odrzucania wiersza ORDINARY bez `required_role`** (drugi reproduktor R2-03) — `tests/test_t030_shift_catalog_api.py`, istniejący wcześniej test niezwiązany z rolami sklepowymi, buduje katalog ORDINARY z zerem ról na każdym wierszu i oczekuje sukcesu (204); literalne wdrożenie żądania reproduktora złamałoby to już zaakceptowane zachowanie. Brief §16/T65-10 mówi o „new ORDINARY bez kompletu ról ma failować jawnie jako niegotowy” w tym samym zdaniu co „poprawny pusty grafik” — czytam to jako wymóg na etapie PLAN (nie fałszywy sukces pustego grafiku), nie na etapie zapisu katalogu. Zgodnie z brief §12 („jeśli kontrakty są sprzeczne, STOP + finding”) nie rozstrzygałem tego sam. **Pytanie do Codexa/architekta: czy ORDINARY bez żadnej roli na żadnym wierszu ma pozostać legalną konfiguracją (jak dziś w T030), czy T030 ma zostać zaktualizowane pod nowy, twardszy kontrakt wyłącznie dla obiektów używających ról sklepowych?** Zweryfikowane: wszystkie 5 reproduktorów Codexa poza tym jednym punktem PASS; 136 passed na testach Tasku + wskazanych celowanych regresjach; ruff i `tsc -b` czyste. Pełnej regresji nie uruchamiałem — zgodnie z instrukcją Codexa wystarczy wąski re-check. |

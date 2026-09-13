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
| ROTA-T065 | CC | Codex | `task/ROTA-T065` | implementacja `04d05c5` (brief `1145c9a`, precheck PASS `37bc7f7`) | READY_FOR_CODEX | **Implementacja gotowa do audytu, dokładnie wg literalnego TASK_SCOPE briefu (§19) — 23 pliki, żaden poza listą.** Jedyna nowa logika biznesowa: `EmployeeRole` (`KIEROWNIK`, `SPRZEDAWCA_ZALOGA`), `SiteMembership.allowed_roles`, `StandardShift`/`ShiftDemand.required_role`. Reużyty istniejący generator/eligibility/solver/validator/persistence/lifecycle — bez drugiego solvera, drugiego validatora, drugiego przebiegu per rolę, automatycznego fallbacku ról czy automatyki external. Nowa twarda bramka `ROLE-01` w `eligibility.py::_common_hard_gate` (identycznie LOCAL/EXTERNAL_SUPPORT) + niezależne lustro w `validator.py` — świadomie po **tagowanym** `covers_demand_id` (`_covering_demand`), nie po nakładających się demandach (`_covered_demands`), bo brief T65-01 wymaga dwóch różnych ról na dokładnie tym samym przedziale czasu i overlap-matching dałby fałszywe alarmy. `classify_demand`/D-N niezmienione; nowe demandy ORDINARY zawsze mają jawny `shift_kind` (generator już go zawsze ustawiał, ta ścieżka bez zmian) — żadnego dodatkowego "znacznika legacy vs nowy" nie było potrzeba, bo `required_role` sam pełni tę rolę. Migracja 19 (3 nullable kolumny), pełna ścieżka zapisu/UI (`ControlPanel`/`SiteShiftCatalog`/`MonthlyPlanning`; `EmployeeDetail` świadomie nietknięty — brief §19 zawęził go tylko do "nie wprowadzać nowego konfliktu D/N", nie dodałem tam nic). `MonthlyPlanning.tsx::cellLabel` dla demandu z rolą pokazuje realne godziny (np. „5–12”), nie D/N i nie „?” (T65-08/A9); istniejący picker miesięcznych kodów D6+/N6+ jawnie wyłączony dla demandów z rolą (brief §14). 16 nowych testów w `tests/test_t065_ordinary_roles.py` (T65-01/02/03, ROLE-01 w obu miejscach, LOCAL/EXTERNAL parytet, generator 24h+INNY, brak przecieku NIGHT-STREAK-01 na przejściu przez północ, regresja D/N Ochrony, pełny round-trip persystencji z domyślaniem dla wierszy legacy). `npx tsc -b` czyste, ruff czyste (poza jednym nietkniętym, wcześniej istniejącym `fairness.py` E501, niezwiązanym). **Pełna regresja: 1481 passed, 4 failed, 2 skipped — wszystkie 4 zweryfikowane niezależnie jako identyczne na czystym stanie main@8199143 sprzed tego Tasku (osobny worktree), więc nie są tu naprawiane.** (1) `tests/property/test_coordinator_simulator*.py` — 3 awarie niezwiązane z rolami (409 Conflict na REPLAN; status `THIRD_CONSECUTIVE_SHIFT_BLOCKED` spoza własnej starej listy `_KNOWN_PLAN_STATUSES` testu). (2) `test_t23_54_t012_legality_rest_modules_unmodified_by_checkpoint_b` — test-diff z ery T023 względem stałego starego `BASE_SHA`; już wcześniej czerwony przez `constraints.py` (nieznane mi pochodzenie), teraz dodatkowo wymienia `eligibility.py` — dokładnie ten plik brief jawnie autoryzuje do zmiany (PRE_IMPLEMENTATION_REDUCTION_GATE pkt 4). Nie modyfikowałem tego testu — to test granicy legalności z historycznym znaczeniem, decyzja czy go zaktualizować należy do Codexa/architekta, nie do CC. |
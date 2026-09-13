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
| ROTA-BACKEND-TASK-SCOPE-FORMAT-DRIFT | CC | Architekt | — (finding, brak briefu) | `backend.py` niezmieniony od `03e5353` (jeden commit w całej historii); brief `tasks/ROTA-T065/brief.md` | OWNER_DECISION_NEEDED | **`backend.py` nie był nieautoryzowanie zmieniony — sprawdzone `git log --oneline -- backend.py`, dokładnie jeden commit w historii, baseline projektu. Przyczyna jest odwrotna: format brief.md architekta odjechał od kontraktu, którego `backend.py` mechanicznie wymaga, i nikt tego nie złapał, bo mechaniczna bramka nie jest już uruchamiana w bieżącym procesie CC↔Codex/BOARD.md (ostatni realny przebieg: `tasks/ROTA-T055/round_01/tests/backend_output_r4.txt`, 4 września).** `backend.py::read_task_scope()` wymaga LITERALNEJ linii `TASK_SCOPE:` (dwukropek, bez nagłówka markdown) z listą plików jako myślniki (`- plik.py`) — dokładnie tak wyglądał `tasks/ROTA-T055/brief.md` (`TASK_SCOPE:` + myślniki), i wtedy `SIZE_FILE`/`SIZE_FUNC`/`RUFF`/`DIFF_SCOPE` realnie działały. `tasks/ROTA-T065/brief.md` sekcję nazywa `## 19. Literalny TASK_SCOPE` (nagłówek markdown, nie literalne `TASK_SCOPE:`) i wypisuje pliki jako listę numerowaną (`1. `, `2. `...), nie myślnikami. Zweryfikowane bezpośrednim uruchomieniem `read_task_scope()` na tym pliku: `ValueError: TASK_SCOPE missing in brief` — parser nie znajduje sekcji wcale, więc `check_sizes`/`check_ruff`/`check_scope_and_files`/`find_importers` dostają pustą listę i milczą, zamiast wyrzucić błąd na przekroczenie limitu linii pliku/funkcji. **Prośba do architekta: pisząc TASK_SCOPE w każdym brief.md, używać dokładnie formatu `backend.py` już umie parsować — literalna linia `TASK_SCOPE:` (nie nagłówek), pliki jako myślniki, nie lista numerowana** — to jedyna mechaniczna bramka pilnująca limitu wielkości plików/funkcji niezależnie od implementatora; jej ciche wyłączenie zwiększa ryzyko rozrostu kodu (spaghetti) bez sygnału. CC nie zmienia formatu briefów samodzielnie — to decyzja architekta/właściciela co do konwencji pisania briefów. |
| ROTA-T065 | CC | Codex | `task/ROTA-T065` | poprawka R3-01 `4274011` (na FAIL `2e4df35`/`eebed90`) | READY_FOR_CODEX | **R3-01 naprawione: `dn_semantics_apply(demand, regime)` zamiast `is_role_based_demand`, po decyzji ownera że wątpliwość "duży promień zmiany" była nadmiarowa dla tego typu poprawki (etykieta w testach, nie decyzja produktowa) — Paweł zlecił bezpośrednio: "zrób to sam".** Implementacja: `regime` dociągany z `state.site.planning_regime` przez `eligibility.py`/`validator.py`/`solver.py`; SiteRule rozdzielone wg rodzaju (`site_rules.py::SHIFT_KIND_SPECIFIC_RULE_KINDS`) — tylko `EMPLOYEE_ALLOWED_SHIFT_KINDS`/`EMPLOYEE_FORBIDDEN_SHIFT_KINDS_ON_WEEKDAYS` pomijane dla technicznego D/N, `EMPLOYEE_ALLOWED_WEEKDAYS` (czysto data-only) zawsze aktywne. Naprawiono też przyczynę 30 nowych failów z poprzedniej próby: `tests/support/minimal_state.py`/`state_builder.py` domyślnie konstruują `Site(..., ORDINARY)` jako neutralny placeholder w dziesiątkach testów — 6 plików (`test_site_rules_execution.py`, `test_t018.py`, `test_t032_soft_ranking.py`, `test_t058.py`, `test_audit_t007_r3.py`, `test_audit_t007_r5.py`) faktycznie testuje zachowanie OCHRONA-specyficzne (SiteRule D/N, NIGHT-STREAK-01, DAY_ONLY-N-FALLBACK-01) przez ten domyślny placeholder — każdy z nich dostał lokalny override na jawne `SitePlanningRegime.OCHRONA` (przez lokalny wrapper `base_state()` albo, gdzie dotyczyło jednego testu, wprost w miejscu wywołania); wspólny domyślny reżim w `minimal_state.py`/`state_builder.py` NIE został zmieniony (ryzyko odwrotnego efektu na testy zakładające brak WEEKLY-REST-01/podłogi 24h). Zweryfikowane: wszystkie 3 reproduktory R3 + zachowane reproduktory R2 PASS; wszystkie 6 poprawionych plików w całości PASS (25+37+13+15+11+1=102); `test_t065_ordinary_roles.py`, `test_t030_shift_catalog_api.py`, `test_t023b.py`, `test_eligibility_matrix.py`, `test_audit_r12/r13_findings.py`, `test_site_rule_execution_integration.py` nadal PASS — razem 214 passed. **Pełnej regresji całej suity (~1500 testów, ~19 min) nie zdążyłem uruchomić w tej sesji (kończymy na godzinę) — proszę Codexa o jej wykonanie jako część re-checku**, obok zwykłego zestawu (diff, reproduktory R2+R3, testy Tasku). |

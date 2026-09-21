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
| ROTA-CODEX-AUDIT-TIERS | CC | Architekt | -- (propozycja procesu, bez kodu) | `arch/PROPOSAL_2026-09-21_CODEX_AUDIT_TIERS.md` | OWNER_DECISION_NEEDED | **OWNER: Codex zuzywa limit, bo nie ma podzialu na lekki i powazny audyt.** Szkic (do decyzji architekta+ownera, CC nie zmienia AGENTS.md ani configu): (1) sekcja `AUDIT_TIER: LIGHT|STANDARD|DEEP` wpisywana przez architekta w wierszu BOARD (domyslnie STANDARD; Codex moze tylko podniesc, z konkretnym powodem); LIGHT = diff + JEDEN reproduktor, bez pionu/macierzy/WHERE_MAP, raport <=30 linii; DEEP = mechaniczne wyzwalacze sciezek (rota/planning/**, db.py/migracje, pii_crypto.py, api/auth/**, Dockerfile, zmiana kontraktu/HARD) -- pelny audyt; ROUND_CAP max 2 rundy re-checku na temat, STOP_RULE po wystarczajacym dowodzie; DEFECT_GATE/exact SHA/reproduktor per finding BEZ ZMIAN we wszystkich poziomach. (2) Odchudzenie AGENTS.md+CODEX_START_HERE.md z ok. 18 KB do <=8 KB: usunac tablice nagrobne (SIMULATORS/BENCHMARKS REMOVED -> jedno zdanie), zdeduplikowac reguly powtorzone w obu plikach. (3) Reczne po stronie OWNERA (poza repo, AGENTS.md tego nie wymusi): reasoning effort per watek wg AUDIT_TIER (LIGHT=low, STANDARD=medium, DEEP=high), wylaczenie w ~/.codex/config.toml wtyczek niezwiazanych z kodem (documents/pdf/spreadsheets/presentations/template-creator/visualize/computer-use), model_verbosity=low, tool_output_token_limit, jedna sesja=jeden audyt. Pytania otwarte w pliku (kompletnosc listy DEEP, kto przypisuje poziom bez wiersza BOARD, pomiar zuzycia dla 5 audytow przed/po). Zrodla zewnetrzne to blogi praktykow, liczby orientacyjne. |
| AGENT-HARNESS-KIT-AUDIT | CC | Codex | Agent: `task/HARNESS-STARTER-KIT` | `515920fdebd9a1267ab5dc1adaa1afc23f5d4301` | READY_FOR_CODEX | **Audyt CRITICAL zestawu startowego harnessu dla projektu Agent (zlecenie OWNERA, 2026-09-21). To jest INNE repo niz Rota** -- nie audytuj Roty ani starego `C:\Projects\Agent`. Klon: `git clone --branch task/HARNESS-STARTER-KIT https://github.com/paweltpietraszko-ship-it/Agent.git` do folderu POZA Rota (repo prywatne, uzyj konta OWNERA); sprawdz `git rev-parse HEAD` = SHA z wiersza. Start: `docs/PROCESS.md`, potem `harness/backend.py`, `guard.py`, `task_init.py`, `.githooks/pre-commit`, `.github/workflows/gate.yml`, `harness/tests/`. `python -m pytest harness/tests` (63 testy) i `ruff check --config harness/ruff.toml harness` sa zielone u CC -- nie powtarzaj bez powodu. Wiesz z Roty, jak modele obchodzily `guard.py`, `task_init.py` i `TASK_SCOPE`; szukaj tego samego tutaj. Audytuj to, co jest w kodzie kitu, nie to, jak bylo w Rocie. **Pytania (tylko te):** (1) Jak model moze obejsc bramke, hook lub workflow bez czerwonego wyniku? (2) Czy jest falszywy PASS/FAIL: zmiana nazwy, usuniecie, symlink, dziwne sciezki, CRLF, brief zmieniony po `before_sha`, `TASK_SCOPE` z `**`? (3) Roznice Windows vs Linux (Actions biegnie na Linuksie): sciezki, `sh` w hooku, `git show`, kodowanie. (4) Czy limity miekkie/twarde (kod 600/900, testy 1200/1800, funkcja 50/80) lub WYMAGA_DECYZJI nie otwieraja nowej luki (np. model dzieli plik tylko po to, by ominac prog)? (5) Czy workflow ma luke: uprawnienia, `${{ github.ref_name }}` w shellu (wstrzykniecie przez nazwe brancha), brief/`repo_before.hash` podmienione w tym samym pushu. Zakres: tylko kit; bez propozycji nowych funkcji poza ARCHITECTURE_PROPOSALS. Znane i zaakceptowane: kolejnosc ARCHITECT_REVIEW->Codex nie jest wymuszana mechanicznie (zadanie dla Maestro); ochrona `main` (ruleset) jeszcze niewlaczona -- decyzja OWNERA. **Raport** (Codex nie przeskakuje miedzy repo): zapisz jako `tasks/AGENT-HARNESS-KIT-AUDIT/audit_r1.txt` na branchu Roty `audit/agent-harness-kit` (utworz od `main`), i zmien status na CODEX_REPORTED. CC przeniesie wnioski do Agent. |

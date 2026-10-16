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
| ROTA-CLOUD-REVIEW-FIXES | CC | Codex | `task/ROTA-CLOUD-REVIEW-FIXES` | `4c45a67362288eb3babe9acacb5dc456cc1ce9db` | READY_FOR_CODEX | **Implementacja gotowa do audytu (precheck r1/r2 zamknięte, poprawki P1/P2 naniesione).** Brief: `tasks/ROTA-CLOUD-REVIEW-FIXES/brief.md` (main@8512553, base). Dostawa: `tasks/ROTA-CLOUD-REVIEW-FIXES/round_01/implementation/delivery_r1.md` (klasyfikacja bramki, dowody, NOT_CHECKED, mapa test→kontrakt→powód). Bramka dosłownie: `backend_r2.txt` -- STATUS: FAIL (NEW_FILES 8 -- wszystkie wymienione w TASK_SCOPE; SIZE_FILE/SIZE_FUNC -- pliki/funkcje >limit już przed zmianą; RATIO/TOTAL_LINES -- WYMAGA_DECYZJI). Decyzja o akceptacji należy do OWNERA, nie CC. Pełna suita raz (A9): **1516 passed, 1 skipped, 0 failed** (przed: 34 failed). Nowe: `tests/test_cloud_review_schedule_fixes.py` (15), `tests/test_cloud_review_password_change.py` (3), `frontend/e2e/cloud-review-fixes.spec.ts` (1); mutacje F1-F7 potwierdzone. NOT_CHECKED: A2/F5 w kontenerze (brak Dockera) -- po wdrożeniu `railway ssh date`. R: tylko `railway config plan` (0 add / 1 change / 0 destroy); `apply` NIE wykonany, `railway.json` celowo zostaje -- patrz `deploy/RAILWAY.md`. **Ważne dla audytu R:** plik z `railway config migrate` pomija env/volume/source; jego plan usuwa 6 sekretów (w tym ROTA_CENTRAL_KEK), odpina /data i repo -- dlatego plik = `config pull` + jawny DOCKERFILE. Zakres wg AGENTS: exact SHA, surowy diff, najmniejszy reproduktor każdej klasy, bez pełnej suity (już wykonana przez CC). Raport: `tasks/ROTA-CLOUD-REVIEW-FIXES/round_01/tests/tests_r3.txt`. **JAK PRACOWAĆ, ŻEBY NIE PRZESZKADZAĆ CC (prośba OWNERA):** (1) NIE przełączaj brancha w głównym folderze `C:\Projects\Elnath Rota` -- 2026-10-16 przełączenie go na `codex/...` w trakcie pracy CC sprawiło, że commit CC trafił na Twój branch; pracuj wyłącznie w własnym `git worktree` (np. `.worktrees/codex-<task>`), CC robi tak samo (`.worktrees/cc-cloud-fixes`). (2) Nie commituj do lokalnego `main` bez pushu -- zostaw raport na swoim branchu i zaktualizuj BOARD.md na `origin/main` (pull, edycja, push od razu). (3) Nie zmieniaj plików na `task/ROTA-CLOUD-REVIEW-FIXES`; jedynym Twoim plikiem jest raport `tests_r<n>.txt` -- zapisz go na własnym branchu `audit/rota-cloud-review-fixes`, CC go przeniesie. (4) Przed edycją BOARD.md zawsze `git pull`; edytuj tylko swój wiersz. |
| ROTA-UNMAPPED-DEVIATION-RULES | CC | Architekt | `main` | `8512553` | OWNER_DECISION_NEEDED | **Zgłoszenie poza zakresem ROTA-CLOUD-REVIEW-FIXES (CC nie naprawiał).** Ta sama klasa co F1: `rota/application/deviation_mapping.py::_BUILTIN_RULE_CATEGORY` nie ma kategorii dla kodów, które walidator emituje: `ROLE-01` (validator_checks_availability.py:124), `WORK_PERIOD-01`, `FULL_HOUR-01`, `SITE_RULE-01`, `ASSIGN`. `materialize_deviations` -> `category_for_rule` -> `UnknownDeviationSource` -> nieobsłużony 500. Realny scenariusz: ręczna korekta w sklepie wstawiająca osobę bez wymaganej roli (ROLE-01). Ustalone z kodu, NIE uruchomione. Do decyzji: kategorie dla tych kodów (propozycja CC: ROLE-01 -> PREFERENCE jak MEMBERSHIP-01; SITE_RULE-01 -> CLIENT_REQUIREMENT? -- wymaga briefu), osobny mały Task. |

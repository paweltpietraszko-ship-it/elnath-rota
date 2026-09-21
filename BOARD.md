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
| AGENT-HARNESS-CODEX-START-HERE | CC | Codex | Agent (po merge: `main`, `cb728d4`) | `cb728d4` | CODEX_REPORTED | **CODEX: plik gotowy na `audit/agent-harness-kit` @ `c5232c4`, `tasks/AGENT-HARNESS-KIT-AUDIT/CODEX_START_HERE.md`.** Audyt kitu zamkniety: PASS r4, kit zmergowany do `main` w Agent, repo publiczne (dziekuje). **Nastepne zlecenie (nie audyt): napisz swoj plik startowy dla nastepcy Codexa** -- `CODEX_START_HERE.md`, ok. 40-70 linii, po polsku, dla Codexa, ktory nie widzial tej rozmowy. Wzor: `CC_START_HERE.md` w repo Agent (przeczytaj, nie kopiuj). Wpisz to, czego nie ma w `AGENTS.md`: czego nauczyl Cie audyt kitu i Roty (klasy obejsc, ktore warto sprawdzac; jak ograniczac zuzycie limitu; jak pracowac na jednym repo bez skakania miedzy repo; jak pisac raport, zeby CC i architekt go uzyli), czego NIE robic, i sekcje `Stan` z data. Zapisz jako `tasks/AGENT-HARNESS-KIT-AUDIT/CODEX_START_HERE.md` na branchu `audit/agent-harness-kit`, status CODEX_REPORTED; CC wgra go do Agent (na `main` w Agent commituje tylko CC / przez PR). |
| AGENT-HARNESS-BOOKKEEPING-GATE | CC | Codex | Agent: `task/HARNESS-BOOKKEEPING-GATE` | `95db737bb31558214982d52e20e90f82b28042b5` | CODEX_REPORTED | **CODEX: PASS na exact SHA; raport `audit/agent-harness-kit` @ `90d6563`, `tasks/AGENT-HARNESS-BOOKKEEPING-GATE/audit_r1.txt`.** **Audyt CRITICAL zmiany bramki w repo Agent (nie Rota; zlecenie OWNERA: bramka ma przepuszczac zmiany tylko BOARD.md/ODLOZONE.md bez briefu, jesli to bezpieczne).** Klon: `git clone --branch task/HARNESS-BOOKKEEPING-GATE https://github.com/paweltpietraszko-ship-it/Agent.git` (repo jest teraz publiczne). Zmiana: (a) `gate.yml` przechodzi z `push` na `pull_request_target` do `main` -- workflow i skrypty biegna z wersji z `main`, kod PR (`refs/pull/N/head`) jest tylko danymi w `work/`; powod: branch mogl edytowac wlasny `gate.yml` i dawac sobie zielone, wiec wymog zielonego `gate` bylby pozorny; (b) nowy `harness/bookkeeping_only.py`: exit 0 tylko gdy KAZDA zmiana to edycja w miejscu zwyklego pliku BOARD.md/ODLOZONE.md; inaczej pelna bramka; (c) testy `harness/tests/test_bookkeeping.py`, PROCESS.md §3/§8. `backend.py` bez zmian. 74 testy zielone u CC; mutacja skryptu potwierdzona. **Pytania:** (1) Czy `pull_request_target` z checkoutem kodu PR daje wykonanie niezaufanego kodu (ruff, backend, imports, `harness/ruff.toml` z head, `persist-credentials`, secrets, forki)? (2) Czy da sie przepuscic zmiane spoza dwoch plikow przez `bookkeeping_only.py` (rename, zmiana trybu, submodul, nazwa z nowa linia, wiele plikow, merge commit, before rozny od tipa `main`)? (3) Czy branch moze nadal wplynac na to, ktory workflow/skrypt biegnie (sciezki `trusted/` vs `work/`, `github.head_ref` w shellu, `GITHUB_WORKSPACE`)? (4) Czy `before=merge-base origin/main HEAD` w `work/` jest wiarygodny (origin/main w checkoucie PR) i spojny z `check_base`? (5) Czy nazwa checku `gate` nadaje sie do wymogu w rulesecie? Nie da sie tego przetestowac na zywo przed merge (workflow z `pull_request_target` dziala tylko z `main`) -- analiza statyczna; CC przetestuje na zywo dwoma PR-ami po merge. Raport: `tasks/AGENT-HARNESS-BOOKKEEPING-GATE/audit_r1.txt` na branchu `audit/agent-harness-kit`. Zamkniete wczesniej: kit r1-r4 PASS. |

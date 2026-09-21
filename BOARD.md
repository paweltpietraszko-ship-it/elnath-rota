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
| AGENT-HARNESS-KIT-AUDIT | CC | Codex | Agent: `task/HARNESS-STARTER-KIT` | `ec5957633697911aa7acd4e9cdbdeb7f5559cbe9` | READY_FOR_CODEX | **RE-AUDYT r3 po FAIL r2** (raporty: `audit_r1.txt`, `audit_r2.txt` w `tasks/AGENT-HARNESS-KIT-AUDIT/`). Repo Agent, nie Rota. Poprawki: **F1** `check_base` fail-closed -- brak wszystkich refow `origin/main|origin/master|main|master` = `BASE` FAIL; **F2** `is_artifact` = dokladne nazwy `tasks/<id>/{backend_r<n>.txt, backend_ci.txt, audit_r<n>.txt, architect_review_r<n>.md, repo_before.hash}` + BOARD.md/ODLOZONE.md, reszta pod `tasks/` podlega zakresowi; **F3** `glob_regex`: `/**/` = zero lub wiecej katalogow (`app/**/*.py` obejmuje `app/x.py`). Decyzje z r2 (symlink = FAIL, `**` zero-lub-wiecej) sa TECHNICZNE i nalezą do CC -- Owner powiedzial, ze nie ma pojecia, co tu wybrac; nie przypisuj ich Ownerowi. Najnowszy commit zmienia tylko trigger `gate.yml` (`!task/HARNESS-**`, bez briefu nie ma bramki) i sformulowanie w PROCESS.md. Poprzednio: wpisane do `docs/PROCESS.md`. 71 testow zielonych u CC, kazda poprawka potwierdzona mutacja. Zakres r3 wg Twojego WARUNKU: reproduktor F1 bez refu bazowego, payload `.txt` pod `tasks/` o niedozwolonej nazwie, `app/**/*.py` dla `app/x.py` i `app/sub/x.py`, celowane testy zmienionych funkcji (`check_base`, `is_artifact`, `glob_regex`). Raport: `audit_r3.txt` na branchu `audit/agent-harness-kit`. |
